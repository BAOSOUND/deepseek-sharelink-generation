"""
DeepSeek Online - 增强版Streamlit界面（修复类型错误）
"""

import sys
import asyncio
import time
import json
import base64
import os
from datetime import datetime
from pathlib import Path
import pandas as pd

# Windows平台修复
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import streamlit as st
from auto_deepseek import DeepSeekAuto

# 页面配置
st.set_page_config(
    page_title="DeepSeek 批量搜索",
    page_icon="🚀",
    layout="wide"
)

# 自定义CSS
st.markdown("""
<style>
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    .loading-spinner {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid #f3f3f3;
        border-top: 3px solid #3498db;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-right: 8px;
        vertical-align: middle;
    }
    .processing-text {
        display: inline-block;
        vertical-align: middle;
    }
    div[data-testid="column"] .stButton > button {
        width: 120px !important;
        min-width: 120px !important;
        max-width: 120px !important;
    }
</style>
""", unsafe_allow_html=True)

# 初始化session state
if 'batch_results' not in st.session_state:
    st.session_state.batch_results = []
if 'batch_status' not in st.session_state:
    st.session_state.batch_status = 'idle'
if 'current_progress' not in st.session_state:
    st.session_state.current_progress = 0
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'input_key' not in st.session_state:
    st.session_state.input_key = 0

# 标题
st.title("🚀 DeepSeek 批量搜索")
st.markdown("---")

# 侧边栏
with st.sidebar:
    icon_path = "blsicon.png"
    if os.path.exists(icon_path):
        with open(icon_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode()
        html_code = f'<img src="data:image/png;base64,{img_data}" width="120" alt="宝宝爆是俺拉" title="宝宝爆是俺拉">'
        st.markdown(html_code, unsafe_allow_html=True)
    else:
        st.markdown("### 🚀")
    
    st.markdown("---")
    
    browser_data_dir = Path("browser_data")
    is_logged_in = browser_data_dir.exists() and any(browser_data_dir.iterdir())
    
    with st.expander("🔧 条件配置", expanded=True):
        st.markdown("#### 🍪 登录状态")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if is_logged_in:
                st.success("✅ 已就绪")
            else:
                st.warning("⚠️ 首次运行需要登录")
        with col2:
            if is_logged_in and st.button("🗑️ 清除", use_container_width=True):
                import shutil
                shutil.rmtree(browser_data_dir)
                st.rerun()
        
        st.markdown("---")
        
        show_browser = st.checkbox("👁️ 浏览器监测", value=False)
        delay = st.number_input("⏱️ 问题间隔（秒）", min_value=1, max_value=30, value=2)
        timeout = st.number_input("⏰ 等待超时（秒）", min_value=30, max_value=180, value=60)
    
    st.markdown("---")
    st.caption("喜欢就分享出去")

# 主界面
st.markdown("### 📝 问题列表")
st.markdown("**每行一个问题**")

input_key = f"question_input_{st.session_state.input_key}"
edited_text = st.text_area(
    "问题列表",
    value="",
    height=200,
    label_visibility="collapsed",
    placeholder="例如：\nPython异步编程的优点\n机器学习入门方法\n2024年AI发展趋势",
    key=input_key
)

questions = [q.strip() for q in edited_text.split('\n') if q.strip()]
st.session_state.questions = questions

if questions:
    st.info(f"📊 当前共 {len(questions)} 个问题")
    with st.expander("预览问题列表"):
        for i, q in enumerate(questions[:10], 1):
            st.write(f"{i}. {q}")

# 按钮布局
col1, col2, col3 = st.columns([1, 1, 6])

with col1:
    has_input = len(questions) > 0
    is_running = st.session_state.batch_status == 'running'
    start_button = st.button(
        "🚀 开始生成",
        type="primary",
        use_container_width=True,
        disabled=is_running
    )

with col2:
    if st.button("🔄 重置", use_container_width=True):
        st.session_state.batch_results = []
        st.session_state.batch_status = 'idle'
        st.session_state.current_progress = 0
        st.session_state.input_key += 1
        st.rerun()

# 进度显示
progress_placeholder = st.empty()
time_placeholder = st.empty()
current_placeholder = st.empty()
results_placeholder = st.empty()

async def run_batch(questions, delay, show_browser, timeout):
    print("\n========== 开始批量处理 ==========")
    print(f"📋 问题数量: {len(questions)}")
    print(f"👁️ 显示浏览器: {show_browser}")
    print(f"⏱️ 超时设置: {timeout}秒")
    
    auto = DeepSeekAuto(headless=not show_browser, timeout=timeout)
    
    try:
        current_placeholder.markdown(
            '<div><span class="loading-spinner"></span><span class="processing-text">🚀 正在启动浏览器...</span></div>',
            unsafe_allow_html=True
        )
        await auto.start()
        
        current_placeholder.markdown(
            '<div><span class="loading-spinner"></span><span class="processing-text">🔐 正在登录...</span></div>',
            unsafe_allow_html=True
        )
        login_success = await auto.ensure_login()
        
        if not login_success:
            current_placeholder.error("❌ 登录失败")
            return
        
        for i, question in enumerate(questions):
            progress = i / len(questions)
            st.session_state.current_progress = progress
            progress_placeholder.progress(progress)
            
            if i > 0 and st.session_state.start_time:
                elapsed = time.time() - st.session_state.start_time
                avg_time = elapsed / i
                remaining = avg_time * (len(questions) - i)
                time_placeholder.info(f"⏱️ {i}/{len(questions)} | 平均: {avg_time:.1f}秒 | 剩余: {remaining:.0f}秒")
            
            current_placeholder.markdown(
                f'<div><span class="loading-spinner"></span><span class="processing-text">📌 正在处理 ({i+1}/{len(questions)}): {question[:50]}...</span></div>',
                unsafe_allow_html=True
            )
            
            try:
                share_link = await auto.search_and_get_share_link(question)
                current_time = datetime.now().strftime("%Y/%m/%d")
                
                # ===== 修复：确保所有值都是字符串 =====
                result = {
                    "序号": str(i + 1),  # 转换为字符串避免整数错误
                    "问题": question[:50] + ("..." if len(question) > 50 else ""),
                    "分享链接": str(share_link) if share_link else "",
                    "状态": "✅ 成功" if share_link else "❌ 失败",
                    "数据时间": current_time
                }
                # ====================================
                
                st.session_state.batch_results.append(result)
                
                if st.session_state.batch_results:
                    df = pd.DataFrame(st.session_state.batch_results[-5:])
                    results_placeholder.dataframe(df, use_container_width=True, hide_index=True)
                
            except Exception as e:
                print(f"❌ 处理问题出错: {e}")
                current_time = datetime.now().strftime("%Y/%m/%d")
                st.session_state.batch_results.append({
                    "序号": str(i + 1),
                    "问题": question[:50] + ("..." if len(question) > 50 else ""),
                    "分享链接": "",
                    "状态": f"❌ 错误",
                    "数据时间": current_time
                })
            
            if i < len(questions) - 1:
                await asyncio.sleep(delay)
        
        progress_placeholder.progress(1.0)
        current_placeholder.success(f"✅ 完成！共处理 {len(questions)} 个问题")
        
    except Exception as e:
        print(f"❌ 批量处理出错: {e}")
        current_placeholder.error(f"❌ 出错: {e}")
    finally:
        await auto.close()
        st.session_state.batch_status = 'idle'

if start_button and questions:
    st.session_state.batch_status = 'running'
    st.session_state.batch_results = []
    st.session_state.start_time = time.time()
    st.session_state.current_progress = 0
    
    progress_placeholder.empty()
    time_placeholder.empty()
    current_placeholder.empty()
    results_placeholder.empty()
    
    asyncio.run(run_batch(questions, delay, show_browser, timeout))
    st.rerun()

# 显示结果
if st.session_state.batch_results:
    st.markdown("---")
    st.markdown("### 📊 处理结果")
    
    df = pd.DataFrame(st.session_state.batch_results)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总数", len(df))
    with col2:
        success = len(df[df['状态'].str.contains('成功', na=False)])
        st.metric("成功", success)
    with col3:
        failed = len(df[df['状态'].str.contains('失败|错误', na=False)])
        st.metric("失败", failed)
    with col4:
        rate = f"{(success/len(df)*100):.1f}%" if len(df) > 0 else "0%"
        st.metric("成功率", rate)
    
    st.markdown("#### 详细结果")
    display_df = df[['序号', '问题', '状态', '分享链接', '数据时间']].copy()
    st.dataframe(display_df, use_container_width=True, hide_index=True,
                 column_config={"分享链接": st.column_config.LinkColumn("分享链接")})
    
    csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button("📥 下载CSV", csv,
                      f"deepseek_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                      "text/csv")

st.markdown("---")
st.caption("💡 提示：批量处理时请耐心等待")

# ===== 云端部署：安装playwright浏览器 =====
import subprocess
import sys

if sys.platform.startswith('linux'):
    try:
        print("📦 正在安装playwright浏览器...")
        subprocess.run(["playwright", "install", "chromium"], check=True)
        print("✅ playwright浏览器安装完成")
    except Exception as e:
        print(f"⚠️ playwright安装警告: {e}")
# ======================================
