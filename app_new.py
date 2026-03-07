import streamlit as st
import time

# 页面配置必须在最前面
st.set_page_config(
    page_title="DeepSeek 简化版",
    page_icon="✅"
)

# 最简单的标题
st.title("✅ DeepSeek 简化版")
st.write("如果能看见这行字，说明页面渲染正常")

# 简单的输入框
name = st.text_input("你的名字")
if name:
    st.success(f"你好, {name}!")

# 简单的按钮
if st.button("点我测试"):
    st.balloons()
    st.info("按钮被点击了！")

# 显示当前时间
st.write("当前时间:", time.strftime("%Y-%m-%d %H:%M:%S"))

# 检查文件
import os
from pathlib import Path

with st.expander("查看文件状态"):
    files = ['auto_deepseek.py', 'setup_login.py', 'cookies/deepseek_cookies.json']
    for file in files:
        if Path(file).exists():
            st.success(f"✅ {file} 存在")
        else:
            st.warning(f"❌ {file} 不存在")
