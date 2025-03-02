#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import torch
import logging
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
    TaskType
)
import psutil

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 配置參數
MODEL_NAME = "meta-llama/Llama-2-7b-chat-hf"
TRAIN_DATA_PATH = "fraud_data/03_training_data/training_data_20250301_172955.json"
OUTPUT_DIR = "fraud_data/model_checkpoints"
MAX_LENGTH = 256
BATCH_SIZE = 1
EPOCHS = 3

def load_and_process_data(data_path):
    """載入並處理訓練數據"""
    logger.info(f"Loading data from {data_path}")
    
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 數據格式為 {"sft_data": [{"instruction": "...", "input": "...", "output": "..."}]}
    formatted_data = []
    for item in data.get("sft_data", []):
        # 構建提示模板
        prompt = f"""以下是一個防詐騙助手與使用者的對話。助手會提供專業、準確的防詐騙建議。

使用者: {item.get('instruction', '')}

{item.get('input', '') if item.get('input') else ''}

助手: """
        
        formatted_data.append({
            "prompt": prompt,
            "response": item.get('output', ''),
        })
    
    return Dataset.from_list(formatted_data)

def create_model_and_tokenizer():
    """創建並配置模型和分詞器"""
    logger.info("Initializing model and tokenizer")
    
    # 載入分詞器
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True
    )
    tokenizer.pad_token = tokenizer.eos_token
    
    # 載入模型
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True,
        device_map="auto",
        torch_dtype=torch.float32,
    )
    
    # 配置 LoRA
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=8,                     # LoRA 秩
        lora_alpha=32,          # LoRA alpha參數
        lora_dropout=0.05,      # Dropout 概率
        bias="none",
        target_modules=[
            "q_proj",
            "v_proj",
            "k_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ]
    )
    
    # 準備模型進行訓練
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, lora_config)
    
    return model, tokenizer

def tokenize_function(examples, tokenizer):
    """將文本轉換為token"""
    prompt_ids = tokenizer(
        examples["prompt"],
        truncation=True,
        max_length=MAX_LENGTH,
        padding="max_length",
    )
    
    response_ids = tokenizer(
        examples["response"],
        truncation=True,
        max_length=MAX_LENGTH,
        padding="max_length",
    )
    
    input_ids = []
    labels = []
    
    for p_ids, r_ids in zip(prompt_ids["input_ids"], response_ids["input_ids"]):
        input_ids.append(p_ids + r_ids)
        # 設置提示部分的標籤為-100（忽略損失計算）
        labels.append([-100] * len(p_ids) + r_ids)
    
    return {
        "input_ids": input_ids,
        "labels": labels,
        "attention_mask": [
            [1] * len(input_id) for input_id in input_ids
        ]
    }

def main():
    # 記錄初始記憶體使用量
    initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
    logger.info(f"Initial memory usage: {initial_memory:.2f} MB")
    
    # 創建輸出目錄
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    try:
        # 載入數據
        dataset = load_and_process_data(TRAIN_DATA_PATH)
        logger.info(f"Loaded {len(dataset)} training examples")
        
        # 初始化模型和分詞器
        model, tokenizer = create_model_and_tokenizer()
        
        # 處理數據集
        tokenized_dataset = dataset.map(
            lambda x: tokenize_function(x, tokenizer),
            batched=True,
            remove_columns=dataset.column_names,
        )
        
        # 配置訓練參數
        training_args = TrainingArguments(
            output_dir=OUTPUT_DIR,
            per_device_train_batch_size=BATCH_SIZE,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            num_train_epochs=EPOCHS,
            logging_steps=10,
            save_steps=100,
            save_total_limit=3,
            fp16=False,
            optim="paged_adamw_32bit",
            warmup_ratio=0.03,
            lr_scheduler_type="cosine",
            report_to="none",
        )
        
        # 創建訓練器
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_dataset,
            data_collator=DataCollatorForSeq2Seq(
                tokenizer,
                pad_to_multiple_of=8,
                return_tensors="pt",
                padding=True
            ),
        )
        
        # 開始訓練
        logger.info("Starting training")
        trainer.train()
        
        # 儲存模型
        logger.info(f"Saving model to {OUTPUT_DIR}")
        trainer.save_model()
        
    except Exception as e:
        logger.error(f"Training failed: {str(e)}")
        raise
    
    finally:
        # 記錄最終記憶體使用量
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        logger.info(f"Final memory usage: {final_memory:.2f} MB")
        logger.info(f"Memory usage difference: {final_memory - initial_memory:.2f} MB")

if __name__ == "__main__":
    main()
