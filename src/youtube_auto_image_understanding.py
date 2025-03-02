import os
import sys
import subprocess
import cv2
import time
import base64
import json
import openai
from tqdm import tqdm

# 從環境變數加載設定
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("請設置 OPENAI_API_KEY 環境變數")

# 其他設定
YOUTUBE_URL = "https://www.youtube.com/watch?v=JeyDrn1dSUQ"
SCREENSHOT_INTERVAL = 5  # 每5秒截一次圖
MAX_DURATION = 300  # 最大處理時長（秒）
OUTPUT_FOLDER = "youtube_analysis"  # 輸出文件夾

def ensure_dependencies():
    """確保所需依賴已安裝"""
    try:
        # 檢查 yt-dlp (youtube-dl的改進版)
        subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True)
    except FileNotFoundError:
        print("未找到yt-dlp，正在安裝...")
        subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp"], check=True)
    
    # 確保其他必要庫已安裝
    try:
        import openai
        import cv2
        import tqdm
    except ImportError:
        print("安裝缺少的Python庫...")
        subprocess.run([sys.executable, "-m", "pip", "install", "openai", "opencv-python", "tqdm"], check=True)
    
    print("所有依賴已準備就緒")

def download_youtube_video(url, output_path):
    """下載YouTube視頻（低質量版本）"""
    print(f"正在下載視頻: {url}")
    
    # 確保輸出目錄存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 使用yt-dlp下載視頻（選擇較低質量以加快速度）
    command = [
        "yt-dlp",
        "-f", "worst[ext=mp4]",  # 選擇最低質量的mp4
        "--restrict-filenames",  # 避免特殊字符
        "-o", output_path,
        "--no-playlist",  # 不下載播放列表
        url
    ]
    
    try:
        process = subprocess.run(command, capture_output=True, text=True, check=True)
        print("視頻下載完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"下載失敗: {e.stderr}")
        return False

def extract_frames(video_path, output_folder, interval=5, max_duration=300):
    """從視頻中每隔指定時間提取一幀"""
    print(f"從視頻中提取畫面，間隔 {interval} 秒")
    
    # 確保輸出目錄存在
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # 打開視頻文件
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("無法打開視頻文件")
        return []
    
    # 獲取視頻信息
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_duration = total_frames / fps
    
    print(f"視頻信息: {total_frames} 幀, {fps:.2f} FPS, 時長: {video_duration:.2f} 秒")
    
    # 限制處理時長
    if max_duration > 0 and video_duration > max_duration:
        print(f"視頻較長，將只處理前 {max_duration} 秒")
        video_duration = max_duration
    
    # 計算需要提取的幀
    frames_to_extract = []
    for time_point in range(0, int(video_duration), interval):
        frame_number = int(time_point * fps)
        frames_to_extract.append((time_point, frame_number))
    
    # 提取幀
    extracted_frames = []
    for time_point, frame_number in tqdm(frames_to_extract, desc="提取幀"):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        
        if ret:
            # 格式化時間為 HH:MM:SS
            hours = time_point // 3600
            minutes = (time_point % 3600) // 60
            seconds = time_point % 60
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # 保存幀
            output_path = os.path.join(output_folder, f"frame_{time_point:04d}_{time_str}.jpg")
            cv2.imwrite(output_path, frame)
            extracted_frames.append({
                "path": output_path,
                "time": time_point,
                "time_str": time_str
            })
    
    cap.release()
    print(f"成功提取 {len(extracted_frames)} 幀")
    return extracted_frames

def analyze_frame_with_gpt4v(frame_info, api_key):
    """使用GPT-4V分析幀"""
    openai.api_key = api_key
    
    # 讀取並編碼圖像
    with open(frame_info["path"], "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "你是一個專業的視頻分析師。請詳細描述這個視頻幀的內容，包括人物、場景、動作、文字和重要細節。提供詳細但簡潔的分析。"
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": f"這是YouTube視頻在 {frame_info['time_str']} 時間點的幀。請描述你看到的內容:"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500
        )
        
        analysis = response.choices[0].message.content
        return analysis
    
    except Exception as e:
        print(f"分析幀時出錯: {e}")
        return f"分析失敗: {str(e)}"

def generate_video_summary(frame_analyses, api_key):
    """生成最終視頻摘要"""
    openai.api_key = api_key
    
    # 準備所有幀分析的文本
    analyses_text = ""
    for analysis in frame_analyses:
        analyses_text += f"時間點 {analysis['time_str']}:\n{analysis['description']}\n\n"
    
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "你是一個專業的視頻內容總結專家。基於提供的一系列視頻幀分析，創建一個連貫、詳細、結構清晰的視頻摘要。"
                },
                {
                    "role": "user",
                    "content": f"以下是一個YouTube視頻按時間順序的幀分析，每隔幾秒提取一幀。請創建一個全面、有條理的視頻內容摘要，包括主要內容、關鍵時間點和重要信息:\n\n{analyses_text}"
                }
            ],
            max_tokens=1500
        )
        
        summary = response.choices[0].message.content
        return summary
    
    except Exception as e:
        print(f"生成摘要時出錯: {e}")
        return f"摘要生成失敗: {str(e)}"

def main():
    """主函數"""
    # 確保所有依賴已安裝
    ensure_dependencies()
    
    # 創建主輸出目錄
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
    
    # 創建子目錄
    frames_folder = os.path.join(OUTPUT_FOLDER, "frames")
    video_path = os.path.join(OUTPUT_FOLDER, "video.mp4")
    
    print(f"========== YouTube 視頻分析 ==========")
    print(f"目標視頻: {YOUTUBE_URL}")
    print(f"截圖間隔: {SCREENSHOT_INTERVAL} 秒")
    print(f"最大處理時長: {MAX_DURATION} 秒")
    print(f"========================================")
    
    # 步驟1: 下載視頻
    print("\n步驟 1: 下載視頻")
    if not download_youtube_video(YOUTUBE_URL, video_path):
        print("無法下載視頻，程序終止")
        return
    
    # 步驟2: 提取幀
    print("\n步驟 2: 提取視頻幀")
    extracted_frames = extract_frames(
        video_path, 
        frames_folder, 
        interval=SCREENSHOT_INTERVAL, 
        max_duration=MAX_DURATION
    )
    
    if not extracted_frames:
        print("未能提取任何幀，程序終止")
        return
    
    # 步驟3: 分析幀
    print("\n步驟 3: 使用GPT-4V分析幀")
    frame_analyses = []
    
    for i, frame_info in enumerate(tqdm(extracted_frames, desc="分析幀")):
        print(f"\n分析幀 {i+1}/{len(extracted_frames)}: 時間點 {frame_info['time_str']}")
        
        # 分析幀
        description = analyze_frame_with_gpt4v(frame_info, OPENAI_API_KEY)
        
        frame_analyses.append({
            "time": frame_info["time"],
            "time_str": frame_info["time_str"],
            "description": description
        })
        
        # 保存中間結果
        analysis_path = os.path.join(OUTPUT_FOLDER, "frame_analyses.json")
        with open(analysis_path, "w", encoding="utf-8") as f:
            json.dump(frame_analyses, f, ensure_ascii=False, indent=2)
        
        # 簡短延遲，避免API限制
        time.sleep(0.5)
    
    # 步驟4: 生成摘要
    print("\n步驟 4: 生成視頻摘要")
    final_summary = generate_video_summary(frame_analyses, OPENAI_API_KEY)
    
    # 保存最終摘要
    summary_path = os.path.join(OUTPUT_FOLDER, "video_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(final_summary)
    
    print("\n========== 處理完成 ==========")
    print(f"分析了 {len(extracted_frames)} 幀")
    print(f"詳細分析保存在: {os.path.abspath(analysis_path)}")
    print(f"視頻摘要保存在: {os.path.abspath(summary_path)}")
    print("\n視頻摘要:\n" + "="*50)
    print(final_summary)

if __name__ == "__main__":
    main()