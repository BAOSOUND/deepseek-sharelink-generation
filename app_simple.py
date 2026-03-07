import streamlit as st
import sys
import os
from pathlib import Path

st.set_page_config(
    page_title="DeepSeek Online 简化版",
    page_icon="🌐"
)

st.title("🌐 DeepSeek Online 简化版")

# 显示系统信息
with st.expander("系统信息", expanded=True):
    st.write("Python 版本:", sys.version)
    st.write("当前目录:", os.getcwd())
    st.write("文件存在性检查:")
    
    # 检查关键文件
    files = ['auto_deepseek.py', 'setup_login.py', 'cookies/deepseek_cookies.json']
    for file in files:
        path = Path(file)
        if path.exists():
            st.success(f"✅ {file} 存在")
        else:
            st.warning(f"❌ {file} 不存在")

# 简单的输入框
query = st.text_input("输入问题:")
if query:
    st.info(f"您输入了: {query}")
    st.write("接下来会集成自动化功能...")
