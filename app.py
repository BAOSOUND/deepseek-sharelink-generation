"""
DeepSeek Online - Streamlit 主程序（修复Windows异步问题）
"""

# ！！！重要：必须在任何其他导入之前设置事件循环策略 ！！！
import sys
import asyncio

# Windows平台专用修复
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# 现在导入其他模块
import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置页面
st.set_page_config(
    page_title="DeepSeek Online",
    page_icon="🌐",
    layout="wide"
)

st.title("🌐 DeepSeek Online 联网搜索")
st.markdown("> 后台模拟浏览器 + 官方分享链接获取")

# 检查Cookie
cookies_file = Path("cookies/deepseek_cookies.json")
if not cookies_file.exists():
    st.warning("⚠️ 首次使用需要登录")
    st.info("请先在终端运行: `python test_login_fixed.py` 完成登录")

# 侧边栏设置
with st.sidebar:
    st.header("⚙️ 设置")
    show_browser = st.checkbox("显示浏览器窗口", value=False, help="调试时开启")
    
    if st.button("🗑️ 清除Cookie"):
        if cookies_file.exists():
            cookies_file.unlink()
            st.success("Cookie已清除")
            st.rerun()
    
    st.divider()
    st.markdown("### 📋 使用说明")
    st.markdown("""
    1. 输入问题
    2. 等待AI生成回答
    3. 自动获取官方分享链接
    4. 可打开链接查看完整内容
    """)

# 主界面
query = st.chat_input("输入问题...")

if query:
    with st.spinner("正在后台模拟浏览器操作..."):
        try:
            from auto_deepseek import DeepSeekAuto
            
            async def run():
                auto = DeepSeekAuto(headless=not show_browser)
                try:
                    await auto.start()
                    if await auto.ensure_login():
                        share_link = await auto.search_and_get_share_link(query)
                        return share_link
                    return None
                finally:
                    await auto.close()
            
            # 运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            share_link = loop.run_until_complete(run())
            loop.close()
            
            if share_link:
                st.success("✅ 获取成功！")
                st.code(share_link, language="text")
                st.markdown(f"🔗 [打开分享链接]({share_link})")
                
                # 显示预览
                with st.expander("查看详情"):
                    st.markdown(f"**问题**: {query}")
                    st.markdown(f"**分享链接**: {share_link}")
            else:
                st.error("❌ 获取失败，请重试")
                
        except Exception as e:
            st.error(f"❌ 出错了: {str(e)}")
            with st.expander("查看详细错误"):
                import traceback
                st.code(traceback.format_exc())
