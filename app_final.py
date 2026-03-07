"""
DeepSeek Online - 最终稳定版
使用同步Playwright，避免异步问题
"""

import sys
import time
import json
from pathlib import Path

# Windows平台修复
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import streamlit as st
from playwright.sync_api import sync_playwright

# 页面配置
st.set_page_config(
    page_title="DeepSeek Online",
    page_icon="🌐",
    layout="wide"
)

st.title("🌐 DeepSeek Online 联网搜索")
st.markdown("> 稳定版 - 使用同步Playwright")

# Cookie路径
cookies_file = Path("cookies/deepseek_cookies.json")

# 检查Cookie
if not cookies_file.exists():
    st.error("❌ 未找到Cookie文件")
    st.info("请先运行: python setup_login.py")
    with st.expander("查看步骤"):
        st.code("python setup_login.py")
    st.stop()

# 显示Cookie信息
with st.expander("📊 Cookie状态", expanded=False):
    try:
        with open(cookies_file, 'r') as f:
            cookies = json.load(f)
        st.success(f"✅ Cookie已加载 ({len(cookies)} 个)")
    except:
        st.error("❌ Cookie文件损坏")

# 侧边栏
with st.sidebar:
    st.header("⚙️ 设置")
    show_browser = st.checkbox("显示浏览器窗口", value=False, 
                               help="开启后会看到浏览器操作过程")
    
    if st.button("🗑️ 清除Cookie"):
        cookies_file.unlink()
        st.rerun()
    
    st.divider()
    st.markdown("### 📋 说明")
    st.markdown("输入问题后，后台会自动操作浏览器获取分享链接")

# 主界面
query = st.chat_input("输入问题...")

def search_deepseek(query, headless=True):
    """同步搜索函数"""
    try:
        with sync_playwright() as p:
            # 启动浏览器
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context()
            
            # 加载Cookie
            with open(cookies_file, 'r') as f:
                cookies = json.load(f)
                context.add_cookies(cookies)
            
            # 创建页面
            page = context.new_page()
            
            # 访问DeepSeek
            print("访问DeepSeek...")
            page.goto('https://chat.deepseek.com')
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            
            # 检查是否登录
            try:
                page.wait_for_selector('textarea, div[contenteditable="true"]', timeout=5000)
                print("已登录")
            except:
                print("未登录")
                browser.close()
                return None
            
            # 输入问题
            print(f"输入问题: {query}")
            page.fill('textarea, div[contenteditable="true"]', query)
            page.keyboard.press('Enter')
            
            # 等待回答
            print("等待回答...")
            time.sleep(10)
            
            # 点击分享
            print("点击分享按钮...")
            page.click('button:has-text("分享")')
            time.sleep(2)
            
            # 获取分享链接
            link = page.get_attribute('input[readonly]', 'value')
            
            browser.close()
            return link
            
    except Exception as e:
        print(f"错误: {e}")
        return None

# 处理查询
if query:
    with st.spinner("正在后台模拟浏览器操作..."):
        try:
            # 执行搜索
            share_link = search_deepseek(query, headless=not show_browser)
            
            if share_link:
                st.success("✅ 获取成功！")
                st.code(share_link, language="text")
                st.markdown(f"🔗 [打开分享链接]({share_link})")
                
                # 显示预览
                with st.expander("查看链接预览"):
                    st.markdown(f"问题: {query}")
                    st.markdown(f"分享链接: {share_link}")
            else:
                st.error("❌ 获取失败，请重试")
                
        except Exception as e:
            st.error(f"❌ 出错了: {str(e)}")
            with st.expander("查看详细错误"):
                st.code(str(e))
