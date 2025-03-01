import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 初始化OpenAI客戶端
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# 設置頁面配置
st.set_page_config(
    page_title="詐騙防範助手",
    page_icon="🛡️",
    layout="centered"
)

# 添加CSS樣式
st.markdown("""
<style>
.chat-message {
    padding: 1.5rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
    display: flex;
    flex-direction: column;
}
.user-message {
    background-color: #e3f2fd;
    border-left: 5px solid #2196f3;
}
.assistant-message {
    background-color: #f5f5f5;
    border-left: 5px solid #4caf50;
}
</style>
""", unsafe_allow_html=True)

# 標題
st.title("🛡️ 詐騙防範助手")
st.markdown("""
這是一個專門協助識別和防範詐騙的AI助手。
它經過特殊訓練，能夠：
- 識別各種常見的詐騙手法
- 提供具體的防範建議
- 解答詐騙相關的疑問
""")

# 初始化聊天歷史
if "messages" not in st.session_state:
    st.session_state.messages = []

# 顯示聊天歷史
for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]
    
    if role == "user":
        st.markdown(f'<div class="chat-message user-message">👤 您：<br>{content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-message assistant-message">🛡️ 防詐助手：<br>{content}</div>', unsafe_allow_html=True)

# 輸入框
user_input = st.text_input("請描述您遇到的情況，我會協助您判斷是否為詐騙：", key="user_input")

if st.button("發送", key="send"):
    if user_input:
        # 添加用戶消息到歷史
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # 準備完整的對話歷史
        messages = [{"role": "system", "content": "你是一個專業的詐騙防範助手，可以幫助用戶識別各種詐騙手法並提供防範建議。"}]
        messages.extend(st.session_state.messages)
        
        try:
            # 調用API
            response = client.chat.completions.create(
                model="ft:gpt-3.5-turbo-0125:personal::B6GV9v9U",
                messages=messages,
                temperature=0.7,
                max_tokens=800
            )
            
            # 獲取回應
            assistant_response = response.choices[0].message.content
            
            # 添加助手回應到歷史
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
            
            # 重新加載頁面以顯示新消息
            st.rerun()
            
        except Exception as e:
            st.error(f"發生錯誤: {str(e)}")
            
# 添加清除按鈕
if st.button("清除對話歷史"):
    st.session_state.messages = []
    st.rerun()

# 頁腳
st.markdown("---")
st.markdown("💡 提示：如果您遇到可疑情況，請立即撥打165反詐騙專線尋求協助。")
