"""
DeepSeek 自动化模块 - 处理登录和分享链接生成
"""

import asyncio
import json
import os
from pathlib import Path
import time
from typing import Optional, List

from playwright.async_api import async_playwright, Page, Browser

class DeepSeekAuto:
    """DeepSeek 自动化操作类"""
    
    def __init__(self, headless: bool = True, timeout: int = 30):
        self.headless = headless
        self.timeout = timeout * 1000  # 转换为毫秒
        self.playwright = None
        self.browser = None
        self.page = None
        self.cookies_file = Path("cookies/deepseek_cookies.json")
        
    async def start(self):
        """启动浏览器"""
        self.playwright = await async_playwright().start()
        
        # 明确指定使用 chromium，而不是 msedge
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        self.page = await self.browser.new_page()
        await self.page.set_viewport_size({"width": 1280, "height": 800})
        
        # 设置超时
        self.page.set_default_timeout(self.timeout)
        
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def save_cookies(self):
        """保存cookies到文件"""
        if self.page:
            cookies = await self.page.context.cookies()
            self.cookies_file.parent.mkdir(exist_ok=True)
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            return True
        return False
    
    async def load_cookies(self) -> bool:
        """从文件加载cookies"""
        if not self.cookies_file.exists():
            return False
        
        try:
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            if self.page:
                await self.page.context.add_cookies(cookies)
                return True
        except Exception:
            pass
        return False
    
    async def ensure_login(self) -> bool:
        """确保已登录，如果没有有效cookies则手动登录"""
        # 先访问首页
        await self.page.goto("https://chat.deepseek.com/")
        await asyncio.sleep(2)
        
        # 尝试加载cookies
        if await self.load_cookies():
            await self.page.reload()
            await asyncio.sleep(3)
            
            # 检查是否登录成功（通过URL或页面元素）
            if "chat" in self.page.url or await self.page.query_selector("nav"):
                print("✅ 使用已有cookies登录成功")
                return True
        
        print("🔐 需要手动登录，请在30秒内完成登录...")
        
        # 等待用户手动登录
        for i in range(30, 0, -1):
            print(f"\r⏳ 等待登录: {i}秒", end="")
            await asyncio.sleep(1)
            
            # 检查是否登录成功
            if "chat" in self.page.url or await self.page.query_selector("nav"):
                print("\n✅ 登录成功！")
                await self.save_cookies()
                return True
        
        print("\n❌ 登录超时")
        return False
    
    async def search_and_get_share_link(self, question: str) -> Optional[str]:
        """搜索问题并获取分享链接"""
        try:
            # 找到搜索框并输入
            search_input = await self.page.wait_for_selector(
                "input[placeholder*='搜索'], input[type='text']",
                state="visible"
            )
            await search_input.fill(question)
            await search_input.press("Enter")
            await asyncio.sleep(2)
            
            # 等待搜索结果中的对话出现
            conversation = await self.page.wait_for_selector(
                "div[class*='conversation'], div[class*='chat-item']",
                timeout=self.timeout
            )
            await conversation.click()
            await asyncio.sleep(1)
            
            # 查找分享按钮
            share_button = await self.page.wait_for_selector(
                "button:has-text('分享'), button[class*='share']",
                timeout=self.timeout
            )
            await share_button.click()
            await asyncio.sleep(1)
            
            # 获取分享链接
            link_input = await self.page.wait_for_selector(
                "input[type='url'], input[readonly], input[class*='link']",
                timeout=self.timeout
            )
            share_link = await link_input.get_attribute("value")
            
            # 关闭分享弹窗
            close_button = await self.page.query_selector(
                "button[aria-label='关闭'], button:has-text('关闭'), button[class*='close']"
            )
            if close_button:
                await close_button.click()
            
            return share_link
            
        except Exception as e:
            print(f"处理问题 '{question[:30]}...' 时出错: {e}")
            return None
    
    async def batch_process(self, questions: List[str], delay: int = 2) -> List[dict]:
        """批量处理问题列表"""
        results = []
        
        for i, question in enumerate(questions):
            print(f"处理 [{i+1}/{len(questions)}]: {question[:50]}...")
            
            share_link = await self.search_and_get_share_link(question)
            
            results.append({
                "序号": i + 1,
                "问题": question,
                "分享链接": share_link,
                "状态": "成功" if share_link else "失败"
            })
            
            if i < len(questions) - 1:
                await asyncio.sleep(delay)
        
        return results
