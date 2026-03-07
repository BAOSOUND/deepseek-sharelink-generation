"""
DeepSeek Online - 增强版Streamlit界面（精简版）
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
    /* 旋转加载动画 */
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
    st.session_state.questions = [
        "Python异步编程的优点",
        "机器学习入门方法",
        "2024年AI发展趋势"
    ]

# 标题
st.title("🚀 DeepSeek 批量搜索")
st.markdown("---")

# 侧边栏配置
with st.sidebar:
    # ===== 添加图标（blsicon.png）=====
    icon_path = "blsicon.png"
    if os.path.exists(icon_path):
        with open(icon_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode()
        html_code = f'<img src="data:image/png;base64,{img_data}" width="120" alt="宝宝爆是俺拉" title="宝宝爆是俺拉">'
        st.markdown(html_code, unsafe_allow_html=True)
    else:
        st.markdown("### 🚀")
    # ===== 结束图标 =====
    
    st.markdown("---")
    
    # Cookie状态
    cookies_file = Path("cookies/deepseek_cookies.json")
    
    # 条件配置（包含所有设置）
    with st.expander("🔧 条件配置", expanded=True):
        # Cookie设置（放在最上面）
        st.markdown("#### 🍪 Cookie设置")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if cookies_file.exists():
                st.success("✅ 已就绪")
            else:
                st.error("❌ 未就绪")
        with col2:
            if cookies_file.exists():
                if st.button("🗑️ 清除", use_container_width=True):
                    cookies_file.unlink()
                    st.rerun()
        
        st.markdown("---")
        
        # 浏览器监测
        show_browser = st.checkbox(
            "👁️ 浏览器监测",
            value=False,
            help="开启后会显示浏览器操作过程"
        )
        
        # 问题间隔
        delay = st.number_input(
            "⏱️ 问题间隔（秒）",
            min_value=1,
            max_value=30,
            value=2,
            help="每个问题之间的等待时间"
        )
        
        # 等待超时
        timeout = st.number_input(
            "⏰ 等待超时（秒）",
            min_value=10,
            max_value=120,
            value=30,
            help="每个问题的最大等待时间"
        )
    
    st.markdown("---")
    st.caption("喜欢就分享出去")

# 主界面 - 问题输入区域
st.markdown("### 📝 问题列表")

# 只保留文本框编辑
st.markdown("**每行一个问题**")

# 将问题列表转换为文本
questions_text = "\n".join(st.session_state.questions)

# 文本区域
edited_text = st.text_area(
    "问题列表",
    value=questions_text,
    height=200,
    label_visibility="collapsed"
)

# 解析为列表
questions = [q.strip() for q in edited_text.split('\n') if q.strip()]

# 更新session state
if questions != st.session_state.questions:
    st.session_state.questions = questions

# 显示当前问题数量
if questions:
    st.info(f"📊 当前共 {len(questions)} 个问题")
    
    # 预览前几个问题
    with st.expander("预览问题列表"):
        for i, q in enumerate(questions[:10], 1):
            st.write(f"{i}. {q}")
        if len(questions) > 10:
            st.write(f"... 还有 {len(questions)-10} 个问题")

# 控制按钮
col1, col2, col3 = st.columns([1, 1, 5])

with col1:
    start_button = st.button(
        "🚀 开始",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.batch_status == 'running' or not questions
    )

with col2:
    if st.button("🔄 重置", use_container_width=True):
        st.session_state.batch_results = []
        st.session_state.batch_status = 'idle'
        st.session_state.current_progress = 0
        st.rerun()

# 进度显示区域
progress_placeholder = st.empty()
time_placeholder = st.empty()
current_placeholder = st.empty()
results_placeholder = st.empty()

# 异步处理函数
async def run_batch(questions, delay, show_browser, timeout):
    """批量处理异步函数"""
    
    auto = DeepSeekAuto(headless=not show_browser, timeout=timeout)
    
    try:
        # 使用HTML动画替代普通文本
        current_placeholder.markdown(
            '<div><span class="loading-spinner"></span><span class="processing-text">🚀 正在启动浏览器...</span></div>',
            unsafe_allow_html=True
        )
        await auto.start()
        
        current_placeholder.markdown(
            '<div><span class="loading-spinner"></span><span class="processing-text">🔐 正在登录...</span></div>',
            unsafe_allow_html=True
        )
        if not await auto.ensure_login():
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
                
                time_placeholder.info(
                    f"⏱️ {i}/{len(questions)} | 平均: {avg_time:.1f}秒 | 剩余: {remaining:.0f}秒"
                )
            
            # 使用旋转动画
            current_placeholder.markdown(
                f'<div><span class="loading-spinner"></span><span class="processing-text">📌 正在处理 ({i+1}/{len(questions)}): {question[:50]}...</span></div>',
                unsafe_allow_html=True
            )
            
            try:
                share_link = await auto.search_and_get_share_link(question)
                
                # 获取当前时间并格式化为 2026/05/17 格式
                current_time = datetime.now().strftime("%Y/%m/%d")
                
                result = {
                    "序号": i + 1,
                    "问题": question[:50] + ("..." if len(question) > 50 else ""),
                    "分享链接": share_link,
                    "状态": "✅ 成功" if share_link else "❌ 失败",
                    "数据时间": current_time
                }
                st.session_state.batch_results.append(result)
                
                if st.session_state.batch_results:
                    df = pd.DataFrame(st.session_state.batch_results[-5:])
                    results_placeholder.dataframe(df, use_container_width=True, hide_index=True)
                
            except Exception as e:
                current_time = datetime.now().strftime("%Y/%m/%d")
                st.session_state.batch_results.append({
                    "序号": i + 1,
                    "问题": question[:50] + ("..." if len(question) > 50 else ""),
                    "分享链接": None,
                    "状态": f"❌ 错误: {str(e)[:30]}",
                    "数据时间": current_time
                })
            
            if i < len(questions) - 1:
                await asyncio.sleep(delay)
        
        progress_placeholder.progress(1.0)
        current_placeholder.success(f"✅ 完成！共处理 {len(questions)} 个问题")
        
    except Exception as e:
        current_placeholder.error(f"❌ 出错: {e}")
    
    finally:
        await auto.close()

# 运行批量处理
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
    
    st.session_state.batch_status = 'completed'

# 显示结果
if st.session_state.batch_results:
    st.markdown("---")
    st.markdown("### 📊 处理结果")
    
    df = pd.DataFrame(st.session_state.batch_results)
    
    # 统计信息
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
    
    # 详细结果（从序号开始）
    st.markdown("#### 详细结果")
    
    # 重新排列列，只保留需要的列
    display_df = df[['序号', '问题', '状态', '分享链接', '数据时间']].copy()
    
    # 隐藏索引列
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "分享链接": st.column_config.LinkColumn("分享链接")
        }
    )
    
    # 只保留CSV下载
    csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        "📥 下载CSV",
        csv,
        f"deepseek_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        "text/csv",
        use_container_width=False
    )

# 页脚
st.markdown("---")
st.caption("💡 提示：批量处理时请耐心等待")

# ===== 部署修复：安装playwright浏览器 =====
import subprocess
import sys

def setup_playwright():
    """确保playwright浏览器已安装"""
    try:
        print("正在检查playwright浏览器...")
        subprocess.run(["playwright", "install", "chromium"], check=True)
        print("playwright浏览器就绪")
    except Exception as e:
        print(f"playwright浏览器安装失败: {e}")

# 只在非windows系统或明确需要时执行（避免本地重复安装）
if not sys.platform.startswith('win'):
    setup_playwright()
# ======================================
