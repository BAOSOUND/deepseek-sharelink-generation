"""
DeepSeek网页版自动化模块 - 修复cookie持久化问题
"""

import asyncio
import json
import time
import re
import os
from pathlib import Path
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class DeepSeekAuto:
    """DeepSeek自动化操作类"""
    
    def __init__(self, headless=True, timeout=30):
        self.headless = headless
        self.timeout = timeout * 1000
        self.base_dir = Path(__file__).parent
        self.cookies_dir = self.base_dir / "cookies"
        self.cookies_dir.mkdir(exist_ok=True)
        self.playwright = None
        self.context = None
        self.page = None
        self._last_share_link = None
        self._last_read_link = None
        
    async def start(self):
        """启动浏览器 - 使用持久化上下文"""
        self.playwright = await async_playwright().start()
        
        # 使用持久化上下文，自动保存登录状态
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.cookies_dir / "browser_data"),  # 浏览器数据保存目录
            headless=self.headless,
            channel="msedge",
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ],
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            permissions=['clipboard-read', 'clipboard-write']
        )
        
        # 获取页面
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        self.page.set_default_timeout(self.timeout)
        
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        return self
    
    async def ensure_login(self):
        """确保已登录 - 持久化上下文会自动保持登录状态"""
        print("🌐 访问DeepSeek...")
        await self.page.goto('https://chat.deepseek.com')
        await self.page.wait_for_load_state('networkidle')
        
        # 检查是否已登录
        try:
            await self.page.wait_for_selector('textarea, div[contenteditable="true"]', timeout=5000)
            print("✅ 已登录（使用保存的登录状态）")
            return True
        except:
            print("🔐 需要手动登录一次")
        
        # 如果没登录，跳转到登录页
        await self.page.goto('https://chat.deepseek.com/sign_in')
        await self.page.wait_for_load_state('networkidle')
        
        try:
            print("切换到密码登录...")
            
            # 点击密码登录按钮
            click_result = await self.page.evaluate('''
                () => {
                    const buttons = document.querySelectorAll('button.ds-sign-in-form__social-button');
                    for (let i = 0; i < buttons.length; i++) {
                        const btn = buttons[i];
                        const svg = btn.querySelector('svg');
                        if (svg) {
                            const path = svg.querySelector('path');
                            if (path) {
                                const d = path.getAttribute('d') || '';
                                if (d.includes('8.65039') || d.includes('M8.65039')) {
                                    btn.click();
                                    return {success: true, index: i};
                                }
                            }
                        }
                    }
                    return {success: false};
                }
            ''')
            
            print(f"点击结果: {click_result}")
            await asyncio.sleep(1)
            
            print("输入账号密码...")
            await self.page.wait_for_selector('input', timeout=5000)
            
            inputs = await self.page.query_selector_all('input')
            if len(inputs) >= 2:
                username = os.getenv("DEEPSEEK_USER", "")
                password = os.getenv("DEEPSEEK_PWD", "")
                
                await inputs[0].fill(username)
                await inputs[1].fill(password)
                print("✅ 账号密码已输入")
                
                # 找登录按钮
                login_btn = None
                buttons = await self.page.query_selector_all('button')
                for btn in buttons:
                    btn_text = await btn.text_content()
                    if btn_text and '登录' in btn_text:
                        login_btn = btn
                        break
                
                if login_btn:
                    await login_btn.click()
                    print("✅ 点击登录按钮")
                else:
                    await inputs[1].press("Enter")
                    print("✅ 按回车登录")
                
                # 等待登录成功
                for i in range(10):
                    await asyncio.sleep(1)
                    current_url = self.page.url
                    if 'sign_in' not in current_url:
                        print("✅ 登录成功！状态将自动保存")
                        return True
                
                return False
            else:
                return False
                
        except Exception as e:
            print(f"登录出错: {e}")
            return False
    
    async def new_conversation(self):
        """开启新对话"""
        print("开启新对话...")
        
        try:
            # 使用类名查找新对话按钮
            result = await self.page.evaluate('''
                () => {
                    const newChatBtn = document.querySelector('div._5a8ac7a.a084f19e');
                    if (newChatBtn) {
                        newChatBtn.scrollIntoView();
                        newChatBtn.click();
                        return {success: true, method: 'exact_class'};
                    }
                    
                    // 备用方法：找包含"开启新对话"文本的元素
                    const allElements = document.querySelectorAll('*');
                    for (let el of allElements) {
                        if (el.textContent && el.textContent.includes('开启新对话')) {
                            el.click();
                            return {success: true, method: 'text_match'};
                        }
                    }
                    
                    return {success: false};
                }
            ''')
            
            print(f"开启新对话结果: {result}")
            await asyncio.sleep(2)
            return result.get('success', False)
            
        except Exception as e:
            print(f"开启新对话出错: {e}")
            return True
    
    async def wait_for_answer_complete(self, timeout=120):
        """等待回答完全生成"""
        print("等待AI生成完整回答...")
        
        try:
            await self.page.wait_for_selector('button:has-text("停止生成")', timeout=10)
            print("✅ 检测到开始生成")
            await self.page.wait_for_selector('button:has-text("停止生成")', state='hidden', timeout=timeout*1000)
            print("✅ 检测到生成完成")
            return True
        except:
            pass
        
        print("使用备用方法等待...")
        last_content = ""
        stable_count = 0
        
        for i in range(timeout // 2):
            try:
                messages = await self.page.query_selector_all('.ds-markdown, .markdown-body')
                if messages:
                    last_msg = messages[-1]
                    current_text = await last_msg.text_content()
                    
                    if current_text and current_text != last_content:
                        print(f"⏳ 内容在变化... ({len(current_text)}字符)")
                        last_content = current_text
                        stable_count = 0
                    elif current_text:
                        stable_count += 1
                        if stable_count >= 3:
                            print("✅ 内容稳定，生成完成")
                            return True
            except:
                pass
            await asyncio.sleep(2)
        
        print("⚠️ 等待超时")
        return True
    
    async def click_share_button(self):
        """点击分享按钮"""
        print("点击分享按钮...")
        
        try:
            result = await self.page.evaluate('''
                () => {
                    const buttons = document.querySelectorAll('[role="button"]');
                    
                    for (let btn of buttons) {
                        const svg = btn.querySelector('svg');
                        if (svg) {
                            const path = svg.querySelector('path');
                            if (path) {
                                const d = path.getAttribute('d') || '';
                                if (d.includes('M7.95889 1.52285')) {
                                    btn.click();
                                    return {success: true};
                                }
                            }
                        }
                    }
                    return {success: false};
                }
            ''')
            
            if result.get('success'):
                print("✅ 点击分享按钮成功")
                await asyncio.sleep(2)
                return True
            return False
        except Exception as e:
            print(f"点击分享按钮出错: {e}")
            return False
    
    async def click_create_share(self):
        """点击创建分享"""
        print("点击创建分享...")
        
        try:
            result = await self.page.evaluate('''
                () => {
                    const buttons = document.querySelectorAll('button, [role="button"]');
                    for (let btn of buttons) {
                        const text = btn.textContent || '';
                        if (text.includes('创建分享')) {
                            btn.click();
                            return {success: true};
                        }
                    }
                    return {success: false};
                }
            ''')
            
            if result.get('success'):
                print("✅ 点击创建分享成功")
                await asyncio.sleep(2)
                return True
            return False
        except Exception as e:
            print(f"点击创建分享出错: {e}")
            return False
    
    async def click_create_and_copy(self):
        """点击创建并复制"""
        print("点击创建并复制...")
        
        try:
            result = await self.page.evaluate('''
                () => {
                    const buttons = document.querySelectorAll('button, [role="button"]');
                    for (let btn of buttons) {
                        const text = btn.textContent || '';
                        if (text.includes('创建并复制')) {
                            btn.click();
                            return {success: true};
                        }
                    }
                    return {success: false};
                }
            ''')
            
            if result.get('success'):
                print("✅ 点击创建并复制成功")
                await asyncio.sleep(2)
                return True
            return False
        except Exception as e:
            print(f"点击创建并复制出错: {e}")
            return False
    
    async def get_share_link_from_clipboard(self):
        """从剪贴板获取分享链接"""
        print("尝试从剪贴板获取分享链接...")
        
        try:
            await asyncio.sleep(2)
            
            for attempt in range(3):
                clipboard_text = await self.page.evaluate('''
                    async () => {
                        try {
                            const text = await navigator.clipboard.readText();
                            return text;
                        } catch (e) {
                            return null;
                        }
                    }
                ''')
                
                if clipboard_text and clipboard_text.startswith('https://chat.deepseek.com/share/'):
                    if clipboard_text != getattr(self, '_last_read_link', None):
                        self._last_read_link = clipboard_text
                        print(f"✅ 获取到新分享链接")
                        return clipboard_text
                
                await asyncio.sleep(1)
            
            print("❌ 未能获取到新链接")
            return None
                
        except Exception as e:
            print(f"读取剪贴板出错: {e}")
            return None
    
    async def search_and_get_share_link(self, query):
        """搜索并获取分享链接"""
        print(f"\n🔍 搜索: {query}")
        
        try:
            # 1. 开启新对话
            await self.new_conversation()
            
            # 2. 找到输入框
            input_box = await self.page.wait_for_selector('textarea, div[contenteditable="true"]', timeout=self.timeout)
            
            # 3. 输入问题
            await input_box.fill('')
            await input_box.fill(query)
            print("✅ 问题已输入")
            
            # 4. 发送
            await input_box.press('Enter')
            print("✅ 已发送")
            
            # 5. 等待回答
            await self.wait_for_answer_complete()
            
            # 6. 点击分享
            if not await self.click_share_button():
                return None
            
            # 7. 点击创建分享
            if not await self.click_create_share():
                return None
            
            # 8. 点击创建并复制
            if not await self.click_create_and_copy():
                return None
            
            # 9. 获取链接
            share_link = await self.get_share_link_from_clipboard()
            
            if share_link:
                print(f"\n🎉 获取到分享链接: {share_link}")
            else:
                print("\n❌ 获取失败")
            
            return share_link
            
        except Exception as e:
            print(f"搜索出错: {e}")
            return None
    
    async def close(self):
        """关闭浏览器"""
        print("关闭浏览器...")
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        print("✅ 浏览器已关闭")
