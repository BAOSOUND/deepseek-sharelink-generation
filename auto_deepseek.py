"""
DeepSeek??? - ??
"""

import asyncio
import json
import time
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

class DeepSeekAuto:
    def __init__(self, headless=True, timeout=120):  # ????120
        # ?? headless
        is_linux = sys.platform.startswith('linux')
        if is_linux:
            print("?? Linux? headless ??")
            self.headless = True
        else:
            self.headless = headless
        
        self.timeout = timeout * 1000
        self.base_dir = Path(__file__).parent
        self.user_data_dir = self.base_dir / "browser_data"
        self.user_data_dir.mkdir(exist_ok=True)
        self.playwright = None
        self.context = None
        self.page = None
        self._last_read_link = None
        
    async def start(self):
        print("【启动】开始启动浏览器...")
        self.playwright = await async_playwright().start()
        
        is_linux = sys.platform.startswith('linux')
        print(f"【启动】系统平台: {sys.platform}, headless: {self.headless}")
        
        launch_options = {
            'user_data_dir': str(self.user_data_dir),
            'headless': self.headless,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ],
            'viewport': {'width': 1280, 'height': 800},
            'permissions': ['clipboard-read', 'clipboard-write']
        }
        
        if is_linux:
            launch_options['user_agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
        try:
            print("【启动】正在创建浏览器上下文...")
            self.context = await self.playwright.chromium.launch_persistent_context(**launch_options)
            print("【启动】浏览器上下文创建成功")
        except Exception as e:
            print(f"【启动】启动浏览器失败: {e}")
            raise
        
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        self.page.set_default_timeout(self.timeout)
        print("【启动】页面创建成功")
        
        return self
    
    async def ensure_login(self):
        """确保已登录"""
        
        print("\n========== 开始登录流程 ==========")
        
        # 步骤1: 访问主页
        print("【步骤1】访问主页...")
        try:
            await self.page.goto('https://chat.deepseek.com', wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle')
            print(" 主页加载完成")
        except Exception as e:
            print(f" 主页加载失败: {e}")
            return False
        
        # 步骤2: 检测是否已登录
        print("【步骤2】检测登录状态...")
        try:
            await self.page.wait_for_selector('textarea, div[contenteditable="true"]', timeout=5000)
            print(" 检测到输入框，已登录")
            return True
        except:
            print(" 未检测到输入框，需要登录")
            return False  # 先简化，后面再处理登录
    
    # ===== 关键修复：正确等待回答完成 =====
    async def wait_for_answer_complete(self, timeout=120):
        """等待AI回答完全生成"""
        print("等待AI生成完整回答...")
        
        # 方法1：等待"停止生成"按钮出现然后消失
        try:
            # 等待开始生成（"停止生成"按钮出现）
            await self.page.wait_for_selector('button:has-text("停止生成")', timeout=30000)
            print(" 检测到AI开始生成回答")
            
            # 等待生成完成（"停止生成"按钮消失）
            await self.page.wait_for_selector('button:has-text("停止生成")', state='hidden', timeout=timeout*1000)
            print(" 检测到AI生成完成")
            
            # 额外等待1秒确保内容完全加载
            await asyncio.sleep(1)
            return True
            
        except Exception as e:
            print(f" 等待停止生成按钮超时: {e}")
        
        # 方法2：监控内容长度变化
        print("监控内容变化...")
        last_length = 0
        stable_count = 0
        
        for i in range(timeout * 2):  # 每0.5秒检查一次
            try:
                # 获取最后一个回答的内容
                messages = await self.page.query_selector_all('.ds-markdown, .markdown-body, [class*="message"]')
                if messages:
                    last_msg = messages[-1]
                    current_text = await last_msg.text_content() or ""
                    current_length = len(current_text.strip())
                    
                    if current_length > last_length:
                        print(f" 内容正在生成... ({current_length} 字符)")
                        last_length = current_length
                        stable_count = 0
                    elif current_length > 0 and current_length == last_length:
                        stable_count += 1
                        if stable_count >= 4:  # 连续2秒内容不变
                            print(f" 内容稳定，生成完成 (共{current_length}字符)")
                            return True
            except:
                pass
            
            await asyncio.sleep(0.5)
        
        print(" 等待超时")
        return True
    # ======================================
    
    async def new_conversation(self):
        """开启新对话"""
        try:
            await self.page.evaluate('''
                () => {
                    const newChatBtn = document.querySelector('div._5a8ac7a.a084f19e');
                    if (newChatBtn) newChatBtn.click();
                }
            ''')
            await asyncio.sleep(0.5)
        except:
            pass
    
    async def click_share_button(self):
        """点击分享按钮"""
        try:
            result = await self.page.evaluate('''
                () => {
                    const buttons = document.querySelectorAll('[role="button"]');
                    for (let btn of buttons) {
                        const svg = btn.querySelector('svg');
                        if (svg) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }
            ''')
            if result:
                print(" 点击分享按钮")
            return result
        except:
            return False
    
    async def click_create_share(self):
        """点击创建分享"""
        try:
            result = await self.page.evaluate('''
                () => {
                    const buttons = document.querySelectorAll('button');
                    for (let btn of buttons) {
                        const text = btn.textContent || '';
                        if (text.includes('创建分享')) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }
            ''')
            if result:
                print(" 点击创建分享")
            return result
        except:
            return False
    
    async def click_create_and_copy(self):
        """点击创建并复制"""
        try:
            result = await self.page.evaluate('''
                () => {
                    const buttons = document.querySelectorAll('button');
                    for (let btn of buttons) {
                        const text = btn.textContent || '';
                        if (text.includes('创建并复制')) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                }
            ''')
            if result:
                print(" 点击创建并复制")
            return result
        except:
            return False
    
    async def get_share_link_from_clipboard(self):
        """从剪贴板获取分享链接"""
        for attempt in range(3):
            try:
                text = await self.page.evaluate('async () => await navigator.clipboard.readText()')
                if text and text.startswith('https://chat.deepseek.com/share/'):
                    print(f" 获取到分享链接")
                    return text
            except:
                pass
            await asyncio.sleep(0.5)
        return None
    
    async def get_share_link(self):
        """获取分享链接"""
        if not await self.click_share_button():
            return None
        await asyncio.sleep(1)
        if not await self.click_create_share():
            return None
        await asyncio.sleep(1)
        if not await self.click_create_and_copy():
            return None
        await asyncio.sleep(1)
        return await self.get_share_link_from_clipboard()
    
    async def search_and_get_share_link(self, query):
        """搜索并获取分享链接"""
        print(f"\n 处理: {query}")
        
        try:
            await self.new_conversation()
            
            # 找到输入框
            input_box = await self.page.wait_for_selector('textarea, div[contenteditable="true"]', timeout=10000)
            await input_box.fill(query)
            print(" 问题已输入")
            
            await input_box.press('Enter')
            print(" 已发送，等待回答...")
            
            # ===== 关键：等待回答完成 =====
            await self.wait_for_answer_complete()
            # ============================
            
            share_link = await self.get_share_link()
            
            if share_link:
                print(f" 成功获取链接")
            else:
                print(" 获取链接失败")
            
            return share_link
            
        except Exception as e:
            print(f" 错误: {e}")
            return None
    
    async def close(self):
        """关闭浏览器"""
        try:
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
            print(" 浏览器已关闭")
        except:
            pass
