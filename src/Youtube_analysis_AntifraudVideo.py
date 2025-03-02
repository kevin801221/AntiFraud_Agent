import os
import sys
import subprocess
import hashlib
import cv2
import time
import base64
import json
import openai
import datetime
import argparse
import re
import urllib.parse
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from langsmith import Client
from langsmith.run_trees import RunTree
import uuid
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 全局設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SCREENSHOT_INTERVAL = 10  # 每10秒截一次圖 (可通過命令行參數修改)
BASE_OUTPUT_FOLDER = "video_analysis"  # 基礎輸出目錄
VIDEO_DATABASE_FILE = "processed_videos.json"  # 已處理視頻數據庫
MAX_WORKERS = 3  # 最大並行處理的視頻數量
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")  # Langsmith API密鑰
LANGSMITH_PROJECT = "anti-scam-video-analysis"  # Langsmith項目名稱
ENABLE_LANGSMITH = False  # 是否啟用Langsmith追蹤

def setup_argparse():
    """設置命令行參數解析"""
    parser = argparse.ArgumentParser(description='YouTube反詐騙視頻分析工具')
    parser.add_argument('--urls', nargs='*', help='要分析的YouTube視頻URL列表')
    parser.add_argument('--url-file', help='包含YouTube URL的文本文件，每行一個URL')
    parser.add_argument('--interval', type=int, default=SCREENSHOT_INTERVAL, 
                      help=f'截圖間隔秒數 (默認: {SCREENSHOT_INTERVAL})')
    parser.add_argument('--max-duration', type=int, default=0, 
                      help='每個視頻的最大處理時長，0表示處理全部 (默認: 0)')
    parser.add_argument('--api-key', help='OpenAI API密鑰')
    parser.add_argument('--output', default=BASE_OUTPUT_FOLDER, 
                      help=f'輸出基礎目錄 (默認: {BASE_OUTPUT_FOLDER})')
    parser.add_argument('--max-workers', type=int, default=MAX_WORKERS, 
                      help=f'最大並行處理視頻數 (默認: {MAX_WORKERS})')
    parser.add_argument('--force', action='store_true', 
                      help='強制重新處理已處理過的視頻')
    parser.add_argument('--skip-analysis', action='store_true', 
                      help='跳過gpt-4o分析，只提取幀')
    parser.add_argument('--langsmith-api-key', help='Langsmith API密鑰，用於追蹤成本和性能')
    parser.add_argument('--langsmith-project', default=LANGSMITH_PROJECT, 
                      help=f'Langsmith項目名稱 (默認: {LANGSMITH_PROJECT})')
    parser.add_argument('--enable-langsmith', action='store_true', 
                      help='啟用Langsmith追蹤')
    return parser

def ensure_dependencies():
    """確保所需依賴已安裝"""
    required_packages = ["yt-dlp", "openai", "opencv-python", "tqdm", "langsmith"]
    missing_packages = []

    # 檢查yt-dlp命令行工具
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True)
        print("✓ yt-dlp 已安裝")
    except FileNotFoundError:
        missing_packages.append("yt-dlp")
    
    # 檢查Python包
    for package in ["openai", "cv2", "tqdm", "langsmith"]:
        try:
            __import__(package)
            print(f"✓ {package} 已安裝")
        except ImportError:
            if package == "cv2":
                missing_packages.append("opencv-python")
            else:
                missing_packages.append(package)
    
    # 安裝缺少的包
    if missing_packages:
        print(f"正在安裝缺少的依賴: {', '.join(missing_packages)}")
        subprocess.run([sys.executable, "-m", "pip", "install"] + missing_packages, check=True)
        print("所有依賴已安裝")
    else:
        print("所有依賴已準備就緒")

def get_current_datetime_str():
    """獲取當前日期時間的格式化字符串"""
    now = datetime.datetime.now()
    return now.strftime("%Y%m%d_%H%M%S")

def sanitize_filename(filename):
    """清理文件名，移除不安全字符"""
    # 替換不安全的文件名字符
    return re.sub(r'[\\/*?:"<>|]', "_", filename)

def get_video_id(url):
    """從YouTube URL提取視頻ID"""
    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.netloc == 'youtu.be':
        return parsed_url.path[1:]
    if parsed_url.netloc in ('www.youtube.com', 'youtube.com'):
        if parsed_url.path == '/watch':
            query = urllib.parse.parse_qs(parsed_url.query)
            return query.get('v', [None])[0]
    return None

def get_video_hash(url):
    """為視頻URL創建唯一哈希值"""
    video_id = get_video_id(url)
    if not video_id:
        return hashlib.md5(url.encode()).hexdigest()
    return hashlib.md5(video_id.encode()).hexdigest()

def get_video_info(url):
    """獲取YouTube視頻信息（標題、時長等）"""
    try:
        cmd = ["yt-dlp", "--skip-download", "--print", "%(title)s|%(duration)s|%(upload_date)s", url]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        parts = result.stdout.strip().split('|')
        if len(parts) >= 3:
            title = parts[0]
            duration = int(parts[1]) if parts[1].isdigit() else 0
            upload_date = parts[2]  # YYYYMMDD格式
            
            # 格式化上傳日期 (YYYYMMDD -> YYYY-MM-DD)
            if len(upload_date) == 8:
                upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            else:
                upload_date = "未知日期"
                
            return {
                "title": title,
                "duration": duration,
                "upload_date": upload_date,
                "url": url,
                "video_id": get_video_id(url)
            }
    except Exception as e:
        print(f"獲取視頻信息失敗: {e}")
    
    # 返回基本信息
    return {
        "title": "未知標題",
        "duration": 0,
        "upload_date": "未知日期",
        "url": url,
        "video_id": get_video_id(url)
    }

def load_video_database():
    """加載已處理視頻的數據庫"""
    if os.path.exists(VIDEO_DATABASE_FILE):
        try:
            with open(VIDEO_DATABASE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"讀取視頻數據庫失敗: {e}")
            return {}
    return {}

def save_video_database(db):
    """保存已處理視頻的數據庫"""
    try:
        with open(VIDEO_DATABASE_FILE, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存視頻數據庫失敗: {e}")

def is_video_processed(video_hash, db):
    """檢查視頻是否已處理"""
    return video_hash in db

def download_youtube_video(video_info, output_path):
    """下載YouTube視頻（低質量版本）"""
    url = video_info["url"]
    print(f"正在下載視頻: {video_info['title']}")
    
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

def extract_frames(video_path, output_folder, interval=10, max_duration=0):
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

def analyze_frame_with_gpt4v(frame_info, api_key, context, langsmith_client=None):
    """使用gpt-4oV分析幀"""
    openai.api_key = api_key
    
    # 讀取並編碼圖像
    with open(frame_info["path"], "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    
    try:
        # 準備請求
        messages = [
            {
                "role": "system",
                "content": "你是一位專門分析反詐騙宣導視頻的專家。請詳細描述這些幀中顯示的詐騙手法、防範方法、警告標誌，以及任何相關的關鍵信息。特別注意識別詐騙類型和關鍵教育點。"
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text", 
                        "text": f"這是反詐騙宣導視頻「{context['title']}」在 {frame_info['time_str']} 時間點的畫面。請詳細描述你看到的內容，尤其是與防詐騙相關的信息:"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
        
        # 如果啟用了Langsmith追蹤
        if langsmith_client:
            # 創建Langsmith運行
            run_id = str(uuid.uuid4())
            run_tree = RunTree(
                name="frame_analysis",
                run_type="llm",
                inputs={
                    "messages": messages,
                    "model": "gpt-4o",
                    "max_tokens": 500,
                    "frame_time": frame_info['time_str'],
                    "video_title": context['title']
                },
                id=run_id,
                client=langsmith_client
            )
            
            # 執行API調用並追蹤
            with run_tree:
                start_time = time.time()
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    max_tokens=500
                )
                elapsed_time = time.time() - start_time
                
                analysis = response.choices[0].message.content
                
                # 記錄輸出和元數據
                run_tree.outputs = {
                    "analysis": analysis,
                    "response": response.model_dump(),
                }
                run_tree.end_metadata = {
                    "elapsed_time": elapsed_time,
                    "tokens": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    },
                    "cost_estimate": estimate_cost(response.usage.prompt_tokens, response.usage.completion_tokens, "gpt-4o")
                }
                
                return analysis
        else:
            # 不使用Langsmith的正常調用
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=500
            )
            
            analysis = response.choices[0].message.content
            return analysis
    
    except Exception as e:
        print(f"分析幀時出錯: {e}")
        if langsmith_client:
            try:
                # 記錄錯誤
                run_tree.end(error=str(e))
            except:
                pass
        return f"分析失敗: {str(e)}"

def estimate_cost(prompt_tokens, completion_tokens, model):
    """估算API調用成本"""
    # 價格可能會變動，這些是大約價格 (美元/1000 tokens)
    prices = {
        "gpt-4o": {"prompt": 0.01, "completion": 0.03},
        "gpt-4o": {"prompt": 0.03, "completion": 0.06}
    }
    
    if model in prices:
        prompt_cost = (prompt_tokens / 1000) * prices[model]["prompt"]
        completion_cost = (completion_tokens / 1000) * prices[model]["completion"]
        return prompt_cost + completion_cost
    return 0

def generate_video_summary(frame_analyses, api_key, video_info, langsmith_client=None):
    """生成最終視頻摘要"""
    openai.api_key = api_key
    
    # 準備所有幀分析的文本
    analyses_text = ""
    for analysis in frame_analyses:
        analyses_text += f"時間點 {analysis['time_str']}:\n{analysis['description']}\n\n"
    
    try:
        # 準備請求
        messages = [
            {
                "role": "system",
                "content": "你是一位反詐騙教育專家，專門總結分析反詐騙宣導視頻的內容。請基於提供的幀分析，創建一個全面而有條理的視頻摘要，重點強調詐騙類型、常見手法、警告跡象、預防措施和關鍵教育信息。"
            },
            {
                "role": "user",
                "content": f"以下是反詐騙宣導視頻「{video_info['title']}」按時間順序的幀分析。請創建一個結構清晰的視頻摘要，包括:\n\n1. 視頻介紹的詐騙類型\n2. 詐騙手法的運作方式\n3. 如何識別此類詐騙\n4. 建議的預防措施\n5. 關鍵教育要點\n\n幀分析內容如下:\n\n{analyses_text}"
            }
        ]
        
        # 如果啟用了Langsmith追蹤
        if langsmith_client:
            # 創建Langsmith運行
            run_id = str(uuid.uuid4())
            run_tree = RunTree(
                name="video_summary_generation",
                run_type="llm",
                inputs={
                    "messages": messages,
                    "model": "gpt-4o",
                    "max_tokens": 1500,
                    "video_title": video_info['title']
                },
                id=run_id,
                client=langsmith_client
            )
            
            # 執行API調用並追蹤
            with run_tree:
                start_time = time.time()
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    max_tokens=1500
                )
                elapsed_time = time.time() - start_time
                
                summary = response.choices[0].message.content
                
                # 記錄輸出和元數據
                run_tree.outputs = {
                    "summary": summary,
                    "response": response.model_dump(),
                }
                run_tree.end_metadata = {
                    "elapsed_time": elapsed_time,
                    "tokens": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    },
                    "cost_estimate": estimate_cost(response.usage.prompt_tokens, response.usage.completion_tokens, "gpt-4o")
                }
                
                return summary
        else:
            # 不使用Langsmith的正常調用
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=1500
            )
            
            summary = response.choices[0].message.content
            return summary
    
    except Exception as e:
        print(f"生成摘要時出錯: {e}")
        if langsmith_client:
            try:
                run_tree.end(error=str(e))
            except:
                pass
        return f"摘要生成失敗: {str(e)}"

def clean_old_files(directory):
    """清理舊的臨時文件"""
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"刪除文件時出錯 {file_path}: {e}")

def generate_html_report(video_folder, video_info, frame_analyses, summary):
    """生成HTML報告"""
    try:
        html_path = os.path.join(video_folder, "report.html")
        
        # 準備HTML內容
        html_parts = []
        
        # 頭部
        html_parts.extend([
            '<!DOCTYPE html>',
            '<html lang="zh-TW">',
            '<head>',
            '    <meta charset="UTF-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'    <title>反詐騙視頻分析: {video_info["title"]}</title>',
            '    <style>',
            '        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; color: #333; }',
            '        h1, h2, h3 { color: #2c3e50; }',
            '        .container { max-width: 1200px; margin: 0 auto; }',
            '        .video-info { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }',
            '        .summary { background-color: #e9f7ef; padding: 15px; border-radius: 5px; margin-bottom: 30px; }',
            '        .frame-analysis { display: flex; margin-bottom: 30px; border: 1px solid #ddd; border-radius: 5px; overflow: hidden; }',
            '        .frame-img { flex: 0 0 320px; padding: 10px; }',
            '        .frame-img img { max-width: 100%; border-radius: 3px; }',
            '        .frame-content { flex: 1; padding: 15px; }',
            '        .timestamp { font-weight: bold; color: #3498db; }',
            '        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #777; font-size: 0.9em; }',
            '    </style>',
            '</head>',
            '<body>',
            '    <div class="container">',
            '        <h1>反詐騙視頻分析報告</h1>',
        ])
        
        # 視頻信息
        html_parts.extend([
            '        <div class="video-info">',
            '            <h2>視頻信息</h2>',
            f'            <p><strong>標題:</strong> {video_info["title"]}</p>',
            f'            <p><strong>上傳日期:</strong> {video_info["upload_date"]}</p>',
            f'            <p><strong>時長:</strong> {video_info["duration"]} 秒</p>',
            f'            <p><strong>URL:</strong> <a href="{video_info["url"]}" target="_blank">{video_info["url"]}</a></p>',
            '        </div>',
        ])
        
        # 摘要
        html_parts.extend([
            '        <div class="summary">',
            '            <h2>視頻摘要</h2>',
            f'            {summary}'.replace('\n', '<br>'),
            '        </div>',
            '        <h2>幀分析</h2>',
        ])
        
        # 添加每個幀的分析
        for analysis in frame_analyses:
            frame_path_rel = analysis['frame_path'].replace(os.sep, '/')
            html_parts.extend([
                '        <div class="frame-analysis">',
                '            <div class="frame-img">',
                f'                <p class="timestamp">時間點: {analysis["time_str"]}</p>',
                f'                <img src="{frame_path_rel}" alt="Frame at {analysis["time_str"]}">',
                '            </div>',
                '            <div class="frame-content">',
                '                <h3>內容分析</h3>',
                f'                {analysis["description"]}'.replace('\n', '<br>'),
                '            </div>',
                '        </div>',
            ])
        
        # 添加頁腳
        html_parts.extend([
            '        <div class="footer">',
            f'            <p>分析生成時間: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>',
            '            <p>這份報告使用AI技術自動生成，僅供參考。</p>',
            '        </div>',
            '    </div>',
            '</body>',
            '</html>',
        ])
        
        # 寫入HTML文件
        with open(html_path, "w", encoding="utf-8") as f:
            f.write('\n'.join(html_parts))
        
        print(f"HTML報告已生成: {html_path}")
        return True
    
    except Exception as e:
        print(f"生成HTML報告時出錯: {e}")
        return False

def generate_master_report(output_folder, all_results):
    """生成主報告，列出所有處理過的視頻"""
    try:
        # 報告路徑
        report_path = os.path.join(output_folder, "master_report.html")
        
        # 統計數據
        processed_count = len([r for r in all_results if r["status"] in ["success", "success_frames_only"]])
        skipped_count = len([r for r in all_results if r["status"] == "skipped"])
        failed_count = len([r for r in all_results if r["status"] == "failed"])
        
        # HTML內容
        html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>反詐騙視頻分析總報告</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; color: #333; }}
        h1, h2, h3 {{ color: #2c3e50; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .stats {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; display: flex; }}
        .stat-item {{ flex: 1; text-align: center; padding: 10px; }}
        .stat-number {{ font-size: 2em; font-weight: bold; color: #3498db; }}
        .stat-label {{ font-size: 0.9em; color: #777; }}
        .video-list {{ margin: 20px 0; }}
        .video-item {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 5px; }}
        .success {{ border-left: 5px solid #2ecc71; }}
        .skipped {{ border-left: 5px solid #f39c12; }}
        .failed {{ border-left: 5px solid #e74c3c; }}
        .video-title {{ font-size: 1.2em; font-weight: bold; margin-bottom: 10px; }}
        .video-meta {{ color: #777; font-size: 0.9em; margin-bottom: 10px; }}
        .video-status {{ display: inline-block; padding: 3px 8px; border-radius: 3px; font-size: 0.8em; margin-left: 10px; }}
        .status-success {{ background-color: #d5f5e3; color: #2ecc71; }}
        .status-skipped {{ background-color: #fef9e7; color: #f39c12; }}
        .status-failed {{ background-color: #fadbd8; color: #e74c3c; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #777; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>反詐騙視頻分析總報告</h1>
        
        <div class="stats">
            <div class="stat-item">
                <div class="stat-number">{len(all_results)}</div>
                <div class="stat-label">總視頻數</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{processed_count}</div>
                <div class="stat-label">成功處理</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{skipped_count}</div>
                <div class="stat-label">已跳過</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{failed_count}</div>
                <div class="stat-label">處理失敗</div>
            </div>
        </div>
        
        <h2>處理結果</h2>
        <div class="video-list">
"""
        
        # 添加每個視頻的結果
        for result in sorted(all_results, key=lambda x: x["status"], reverse=True):
            video_info = result["video_info"]
            status = result["status"]
            
            status_class = ""
            status_text = ""
            item_class = ""
            
            if status in ["success", "success_frames_only"]:
                status_class = "status-success"
                status_text = "成功處理" if status == "success" else "僅提取幀"
                item_class = "success"
                report_link = f'<a href="{os.path.relpath(os.path.join(result.get("output_folder", ""), "report.html"), output_folder)}">查看報告</a>'
            elif status == "skipped":
                status_class = "status-skipped"
                status_text = "已跳過"
                item_class = "skipped"
                report_link = ""
            else:
                status_class = "status-failed"
                status_text = f"處理失敗: {result.get('error', 'unknown error')}"
                item_class = "failed"
                report_link = ""
            
            html_content += f"""
            <div class="video-item {item_class}">
                <div class="video-title">
                    {video_info['title']}
                    <span class="video-status {status_class}">{status_text}</span>
                </div>
                <div class="video-meta">
                    <div>上傳日期: {video_info.get('upload_date', '未知')}</div>
                    <div>URL: <a href="{video_info['url']}" target="_blank">{video_info['url']}</a></div>
                    {report_link}
                </div>
            </div>
"""
        
        # 添加頁腳
        html_content += f"""
        </div>
        
        <div class="footer">
            <p>報告生成時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>這份報告使用AI技術自動生成，僅供參考。</p>
        </div>
    </div>
</body>
</html>
"""
        
        # 寫入HTML文件
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"主報告已生成: {report_path}")
        return True
    
    except Exception as e:
        print(f"生成主報告時出錯: {e}")
        return False

def generate_cost_report(langsmith_client, project_name):
    """生成處理成本報告"""
    try:
        # 獲取所有運行
        runs = langsmith_client.list_runs(project_name=project_name)
        
        # 收集成本數據
        total_cost = 0
        model_costs = {}
        run_types = {}
        
        for run in runs:
            # 提取成本信息
            cost = run.end_metadata.get("cost_estimate", 0) if run.end_metadata else 0
            model = run.inputs.get("model", "unknown") if run.inputs else "unknown"
            run_type = run.run_type or "unknown"
            
            # 累計成本
            total_cost += cost
            
            # 按模型分類成本
            if model not in model_costs:
                model_costs[model] = 0
            model_costs[model] += cost
            
            # 按運行類型分類
            if run_type not in run_types:
                run_types[run_type] = {"count": 0, "cost": 0}
            run_types[run_type]["count"] += 1
            run_types[run_type]["cost"] += cost
        
        # 生成報告
        report = {
            "total_cost": total_cost,
            "model_costs": model_costs,
            "run_types": run_types,
            "run_count": len(list(runs))
        }
        
        return report
    except Exception as e:
        print(f"生成成本報告失敗: {e}")
        return {"error": str(e)}

def display_cost_report(cost_report):
    """顯示成本報告"""
    if "error" in cost_report:
        print(f"無法生成成本報告: {cost_report['error']}")
        return
    
    print("\n========== API 使用成本報告 ==========")
    print(f"總運行數量: {cost_report['run_count']}")
    print(f"總成本: ${cost_report['total_cost']:.4f}")
    
    print("\n按模型劃分的成本:")
    for model, cost in sorted(cost_report['model_costs'].items(), key=lambda x: x[1], reverse=True):
        if cost > 0:
            print(f"  - {model}: ${cost:.4f} ({cost/cost_report['total_cost']*100:.1f}%)")
    
    print("\n按運行類型劃分:")
    for run_type, data in sorted(cost_report['run_types'].items(), key=lambda x: x[1]['cost'], reverse=True):
        if data['cost'] > 0:
            print(f"  - {run_type}: {data['count']} 次運行, ${data['cost']:.4f} ({data['cost']/cost_report['total_cost']*100:.1f}%)")
    
    print("=======================================")

def main():
    """主函數"""
    # 解析命令行參數
    parser = setup_argparse()
    args = parser.parse_args()
    
    # 設置API密鑰
    if args.api_key:
        api_key = args.api_key
    else:
        api_key = OPENAI_API_KEY
    
    if api_key == "your_openai_api_key_here":
        print("錯誤: 未設置OpenAI API密鑰")
        print("請通過 --api-key 參數提供，或編輯腳本設置 OPENAI_API_KEY 變量")
        return
    
    args.api_key = api_key
    
    # 設置Langsmith
    langsmith_client = None
    enable_langsmith = args.enable_langsmith or ENABLE_LANGSMITH
    
    if enable_langsmith:
        langsmith_api_key = args.langsmith_api_key or os.environ.get("LANGSMITH_API_KEY") or LANGSMITH_API_KEY
        
        if langsmith_api_key == "your_langsmith_api_key_here":
            print("警告: 未設置Langsmith API密鑰，禁用成本追蹤功能")
            enable_langsmith = False
        else:
            try:
                langsmith_client = Client(
                    api_key=langsmith_api_key,
                    api_url=os.environ.get("LANGSMITH_API_URL", "https://api.smith.langchain.com")
                )
                langsmith_project = args.langsmith_project or LANGSMITH_PROJECT
                
                print(f"已啟用Langsmith成本追蹤 (項目: {langsmith_project})")
                
                # 設置環境變量（用於其他可能使用的工具）
                os.environ["LANGCHAIN_TRACING_V2"] = "true"
                os.environ["LANGCHAIN_PROJECT"] = langsmith_project
                os.environ["LANGSMITH_API_KEY"] = langsmith_api_key
                
            except Exception as e:
                print(f"初始化Langsmith失敗: {e}")
                enable_langsmith = False
                langsmith_client = None
    
    # 確保所有依賴已安裝
    ensure_dependencies()
    
    # 獲取要處理的URL列表
    urls_to_process = []
    
    if args.urls:
        urls_to_process.extend(args.urls)
    
    if args.url_file:
        try:
            with open(args.url_file, 'r', encoding='utf-8') as f:
                for line in f:
                    url = line.strip()
                    if url and not url.startswith('#'):
                        urls_to_process.append(url)
        except Exception as e:
            print(f"讀取URL文件時出錯: {e}")
    
    # 如果沒有URL，提示用戶
    if not urls_to_process:
        print("請提供要處理的YouTube URL:")
        print("1. 通過命令行參數: --urls URL1 URL2 URL3 ...")
        print("2. 通過文件: --url-file filename.txt")
        return
    
    # 確保輸出目錄存在
    if not os.path.exists(args.output):
        os.makedirs(args.output)
    
    # 加載已處理視頻數據庫
    video_db = load_video_database()
    
    # 顯示處理信息
    print(f"========== 反詐騙視頻分析 ==========")
    print(f"將處理 {len(urls_to_process)} 個視頻")
    print(f"截圖間隔: {args.interval} 秒")
    print(f"最大並行處理: {args.max_workers} 個視頻")
    print(f"跳過分析: {'是' if args.skip_analysis else '否'}")
    print(f"強制重新處理: {'是' if args.force else '否'}")
    print(f"輸出目錄: {os.path.abspath(args.output)}")
    print(f"成本追蹤: {'啟用' if enable_langsmith else '禁用'}")
    print(f"====================================")
    
    # 處理所有視頻
    results = []
    
    # 使用線程池並行處理多個視頻
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        # 提交所有任務
        future_to_url = {
            executor.submit(process_video, url, args, video_db, langsmith_client if enable_langsmith else None): url 
            for url in urls_to_process
        }
        
        # 處理結果
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
                results.append(result)
                
                # 每完成一個視頻就更新數據庫
                save_video_database(video_db)
                
                if result["status"] == "success":
                    print(f"\n✅ 成功處理視頻: {result['video_info']['title']}")
                elif result["status"] == "success_frames_only":
                    print(f"\n✅ 成功提取幀: {result['video_info']['title']}")
                elif result["status"] == "skipped":
                    print(f"\n⏭️ 跳過視頻: {result['video_info']['title']}")
                else:
                    print(f"\n❌ 處理失敗: {result['video_info']['title']} - {result.get('error', 'unknown error')}")
                
            except Exception as e:
                print(f"\n❌ 處理視頻時出錯 {url}: {e}")
                results.append({
                    "status": "failed",
                    "error": str(e),
                    "video_info": {"url": url, "title": "未知視頻"},
                    "hash": get_video_hash(url)
                })
    
    # 生成主報告
    generate_master_report(args.output, results)
    
    # 統計結果
    success_count = len([r for r in results if r["status"] in ["success", "success_frames_only"]])
    skipped_count = len([r for r in results if r["status"] == "skipped"])
    failed_count = len([r for r in results if r["status"] == "failed"])
    
    print("\n========== 處理完成 ==========")
    print(f"總視頻數: {len(results)}")
    print(f"成功處理: {success_count}")
    print(f"已跳過: {skipped_count}")
    print(f"處理失敗: {failed_count}")
    print(f"主報告: {os.path.abspath(os.path.join(args.output, 'master_report.html'))}")
    
    # 如果啟用了Langsmith，顯示成本報告
    if enable_langsmith and langsmith_client:
        # 延遲一下，確保所有運行都已完成記錄
        time.sleep(2)
        try:
            cost_report = generate_cost_report(langsmith_client, langsmith_project)
            display_cost_report(cost_report)
            
            # 將成本報告保存到文件
            cost_report_path = os.path.join(args.output, "cost_report.json")
            with open(cost_report_path, "w", encoding="utf-8") as f:
                json.dump(cost_report, f, ensure_ascii=False, indent=2)
            print(f"成本報告已保存至: {os.path.abspath(cost_report_path)}")
        except Exception as e:
            print(f"生成成本報告失敗: {e}")
    
    print(f"===============================")

def process_video(video_url, args, video_db, langsmith_client=None):
    # 設置 API 密鑰
    api_key = args.api_key
    """處理單個視頻，返回結果信息"""
    # 獲取視頻哈希和基本信息
    video_hash = get_video_hash(video_url)
    video_info = get_video_info(video_url)
    
    # 為整個視頻處理創建一個Langsmith追蹤（如果啟用）
    if langsmith_client:
        video_run_id = str(uuid.uuid4())
        video_run = RunTree(
            name="process_video",
            run_type="chain",
            inputs={
                "video_url": video_url,
                "video_info": video_info,
                "interval": args.interval,
                "max_duration": args.max_duration
            },
            id=video_run_id,
            client=langsmith_client
        )
        video_run.begin()
    else:
        video_run = None
    
    try:
        # 檢查視頻是否已處理
        if is_video_processed(video_hash, video_db) and not args.force:
            print(f"視頻 '{video_info['title']}' 已處理過，跳過。使用 --force 參數可強制重新處理。")
            
            # 記錄跳過操作
            if video_run:
                video_run.end(
                    outputs={"status": "skipped"},
                    end_metadata={"reason": "already_processed"}
                )
                
            return {
                "status": "skipped",
                "video_info": video_info,
                "hash": video_hash
            }
        
        # 創建輸出目錄結構
        date_str = get_current_datetime_str()
        video_title_safe = sanitize_filename(video_info['title'])
        
        # 格式: output/YYYYMMDD_HHMMSS_VideoTitle_hash/
        video_folder = os.path.join(
            args.output, 
            f"{date_str}_{video_title_safe[:30]}_{video_hash[:8]}"
        )
        
        frames_folder = os.path.join(video_folder, "frames")
        temp_folder = os.path.join(video_folder, "temp")
        os.makedirs(video_folder, exist_ok=True)
        os.makedirs(frames_folder, exist_ok=True)
        os.makedirs(temp_folder, exist_ok=True)
        
        # 臨時視頻文件路徑
        video_path = os.path.join(temp_folder, "video.mp4")
        
        # 記錄視頻信息
        with open(os.path.join(video_folder, "video_info.json"), "w", encoding="utf-8") as f:
            json.dump(video_info, f, ensure_ascii=False, indent=2)
        
        # 步驟1: 下載視頻
        print(f"\n處理視頻: {video_info['title']}")
        
        # 記錄下載操作 (如果啟用Langsmith)
        if video_run:
            download_run = RunTree(
                name="download_video",
                run_type="tool",
                inputs={"video_url": video_url},
                parent_run=video_run
            )
            
            with download_run:
                download_success = download_youtube_video(video_info, video_path)
                download_run.outputs = {"success": download_success}
        else:
            download_success = download_youtube_video(video_info, video_path)
        
        if not download_success:
            print("下載視頻失敗，跳過處理")
            
            # 結束視頻處理追蹤
            if video_run:
                video_run.end(
                    outputs={"status": "failed"},
                    end_metadata={"error": "download_failed"}
                )
                
            return {
                "status": "failed",
                "error": "download_failed",
                "video_info": video_info,
                "hash": video_hash
            }
        
        # 步驟2: 提取幀
        if video_run:
            extract_run = RunTree(
                name="extract_frames",
                run_type="tool",
                inputs={
                    "video_path": video_path,
                    "interval": args.interval,
                    "max_duration": args.max_duration
                },
                parent_run=video_run
            )
            
            with extract_run:
                extracted_frames = extract_frames(
                    video_path, 
                    frames_folder, 
                    interval=args.interval, 
                    max_duration=args.max_duration
                )
                extract_run.outputs = {"frames_count": len(extracted_frames) if extracted_frames else 0}
        else:
            extracted_frames = extract_frames(
                video_path, 
                frames_folder, 
                interval=args.interval, 
                max_duration=args.max_duration
            )
        
        if not extracted_frames:
            print("提取幀失敗，跳過處理")
            
            # 結束視頻處理追蹤
            if video_run:
                video_run.end(
                    outputs={"status": "failed"},
                    end_metadata={"error": "frame_extraction_failed"}
                )
                
            return {
                "status": "failed",
                "error": "frame_extraction_failed",
                "video_info": video_info,
                "hash": video_hash
            }
        
        # 只提取幀，不分析
        if args.skip_analysis:
            # 記錄視頻為已處理
            video_db[video_hash] = {
                "title": video_info["title"],
                "url": video_url,
                "date_processed": date_str,
                "output_folder": video_folder,
                "frames_count": len(extracted_frames)
            }
            
            # 清理臨時文件
            clean_old_files(temp_folder)
            
            # 結束視頻處理追蹤
            if video_run:
                video_run.end(
                    outputs={
                        "status": "success_frames_only",
                        "frames_count": len(extracted_frames)
                    }
                )
                
            return {
                "status": "success_frames_only",
                "video_info": video_info,
                "hash": video_hash,
                "output_folder": video_folder,
                "frames_count": len(extracted_frames)
            }
        
        # 步驟3: 分析幀
        frame_analyses = []
        total_tokens = {"prompt": 0, "completion": 0}
        total_cost = 0
        
        # 創建一個幀分析的父運行
        if video_run:
            frames_run = RunTree(
                name="analyze_frames",
                run_type="chain",
                inputs={"frames_count": len(extracted_frames)},
                parent_run=video_run
            )
            frames_run.begin()
        else:
            frames_run = None
        
        for i, frame_info in enumerate(tqdm(extracted_frames, desc="分析幀")):
            print(f"\n分析幀 {i+1}/{len(extracted_frames)}: 時間點 {frame_info['time_str']}")
            
            # 分析幀
            description = analyze_frame_with_gpt4v(frame_info, api_key, video_info, langsmith_client)
            
            frame_analyses.append({
                "time": frame_info["time"],
                "time_str": frame_info["time_str"],
                "description": description,
                "frame_path": os.path.relpath(frame_info["path"], video_folder)
            })
            
            # 保存中間結果
            try:
                analysis_path = os.path.join(video_folder, "frame_analyses.json")
                os.makedirs(os.path.dirname(analysis_path), exist_ok=True)
                with open(analysis_path, "w", encoding="utf-8") as f:
                    json.dump(frame_analyses, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"保存分析結果時出錯: {e}")
            
            # 短暫延遲，避免API限制
            time.sleep(0.5)
        
        # 結束幀分析追蹤
        if frames_run:
            frames_run.end(
                outputs={"frames_analyzed": len(frame_analyses)}
            )
        
        # 步驟4: 生成摘要
        final_summary = generate_video_summary(frame_analyses, api_key, video_info, langsmith_client)
        
        # 保存最終摘要
        summary_path = os.path.join(video_folder, "video_summary.txt")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(final_summary)
        
        # 生成HTML報告
        if video_run:
            report_run = RunTree(
                name="generate_html_report",
                run_type="tool",
                inputs={"frames_count": len(frame_analyses)},
                parent_run=video_run
            )
            
            with report_run:
                report_success = generate_html_report(video_folder, video_info, frame_analyses, final_summary)
                report_run.outputs = {"success": report_success}
        else:
            generate_html_report(video_folder, video_info, frame_analyses, final_summary)
        
        # 記錄視頻為已處理
        video_db[video_hash] = {
            "title": video_info["title"],
            "url": video_url,
            "date_processed": date_str,
            "output_folder": video_folder,
            "frames_count": len(extracted_frames)
        }
        
        # 清理臨時文件
        clean_old_files(temp_folder)
        
        # 結束視頻處理追蹤
        if video_run:
            video_run.end(
                outputs={
                    "status": "success",
                    "frames_count": len(extracted_frames)
                }
            )
            
        return {
            "status": "success",
            "video_info": video_info,
            "hash": video_hash,
            "output_folder": video_folder,
            "frames_count": len(extracted_frames),
            "summary": final_summary
        }
        
    except Exception as e:
        print(f"處理視頻時出錯: {e}")
        
        # 結束視頻處理追蹤
        if video_run:
            video_run.end(
                outputs={"status": "failed"},
                end_metadata={"error": str(e)}
            )
            
        return {
            "status": "failed",
            "error": str(e),
            "video_info": video_info,
            "hash": video_hash
        }
def main():
    """主函數"""
    try:
        # 檢查環境變量
        print("\n=== 環境變量檢查 ===")
        print(f"OPENAI_API_KEY: {'*' * 8}{os.getenv('OPENAI_API_KEY')[-4:] if os.getenv('OPENAI_API_KEY') else '未設置'}")
        print(f"LANGSMITH_API_KEY: {'*' * 8}{os.getenv('LANGSMITH_API_KEY')[-4:] if os.getenv('LANGSMITH_API_KEY') else '未設置'}")
        print(f"LANGSMITH_PROJECT: {os.getenv('LANGSMITH_PROJECT') or '未設置'}")
        print("========================\n")

        # 解析命令行參數
        parser = setup_argparse()
        args = parser.parse_args()
        
        # 設置輸出目錄
        output_folder = args.output
        os.makedirs(output_folder, exist_ok=True)
        
        # 設置 API 密鑰
        api_key = args.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("錯誤: 未提供 OpenAI API 密鑰")
            return
        args.api_key = api_key
        
        # 設置 Langsmith
        enable_langsmith = args.enable_langsmith
        langsmith_client = None
        if enable_langsmith:
            langsmith_api_key = args.langsmith_api_key or os.getenv("LANGSMITH_API_KEY")
            if langsmith_api_key:
                os.environ["LANGSMITH_API_KEY"] = langsmith_api_key
                os.environ["LANGCHAIN_PROJECT"] = args.langsmith_project
                langsmith_client = Client()
                print(f"已啟用Langsmith成本追蹤 (項目: {args.langsmith_project})")
            else:
                print("警告: 未提供 Langsmith API 密鑰，將無法追蹤成本")
                enable_langsmith = False
        
        # 確保依賴已安裝
        ensure_dependencies()
        
        # 讀取視頻 URL
        urls = []
        if args.urls:
            urls.extend(args.urls)
        if args.url_file:
            try:
                with open(args.url_file, 'r') as f:
                    urls.extend(line.strip() for line in f if line.strip())
            except Exception as e:
                print(f"讀取URL文件出錯: {e}")
                return
        
        if not urls:
            print("錯誤: 未提供視頻 URL")
            return
        
        # 加載視頻資料庫
        video_db = load_video_database()
        
        print("========== 反詐騙視頻分析 ==========")
        print(f"將處理 {len(urls)} 個視頻")
        print(f"截圖間隔: {args.interval} 秒")
        print(f"最大並行處理: {args.max_workers} 個視頻")
        print(f"跳過分析: {'是' if args.skip_analysis else '否'}")
        print(f"強制重新處理: {'是' if args.force else '否'}")
        print(f"輸出目錄: {output_folder}")
        print(f"成本追蹤: {'啟用' if enable_langsmith else '停用'}")
        print("====================================")
        
        # 使用線程池並行處理視頻
        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            future_to_url = {
                executor.submit(process_video, url, args, video_db, langsmith_client if enable_langsmith else None): url 
                for url in urls
            }
            
            all_results = []
            for future in tqdm(as_completed(future_to_url), total=len(urls), desc="處理視頻"):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        all_results.append(result)
                except Exception as e:
                    print(f"處理視頻時出錯 {url}: {e}")
        
        # 生成主報告
        if all_results:
            generate_master_report(output_folder, all_results)
            
            # 如果啟用了 Langsmith，生成成本報告
            if enable_langsmith:
                cost_report = generate_cost_report(langsmith_client, args.langsmith_project)
                if cost_report:
                    display_cost_report(cost_report)
        
        print("處理完成!")
        
    except KeyboardInterrupt:
        print("用戶中斷處理")
        sys.exit(1)
    except Exception as e:
        print(f"處理過程中出錯: {e}")
        sys.exit(1)

if __name__ == "__main__":
    ensure_dependencies()
    main()