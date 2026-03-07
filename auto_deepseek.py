"""
DeepSeek网页版自动化模块 - 云端适配版（用SVG特征定位密码登录）
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
    def __init__(self, headless=True, timeout=60):
        # 云端强制 headless
        is_linux = sys.platform.startswith('linux')
        if is_linux:
            print("🐧 Linux环境：强制使用 headless 模式")
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
        """确保已登录 - 用SVG特征定位密码登录"""
        
        print("\n========== 开始登录流程 ==========")
        
        # 步骤1: 访问主页
        print("【步骤1】访问主页...")
        try:
            await self.page.goto('https://chat.deepseek.com', wait_until='domcontentloaded')
            await self.page.wait_for_load_state('networkidle')
            print("✅ 主页加载完成")
        except Exception as e:
            print(f"❌ 主页加载失败: {e}")
            return False
        
        # 步骤2: 检测是否已登录
        print("【步骤2】检测登录状态...")
        try:
            await self.page.wait_for_selector('textarea, div[contenteditable="true"]', timeout=5000)
            print("✅ 检测到输入框，已登录")
            return True
        except:
            print("⏱️ 未检测到输入框，需要登录")
        
        # 步骤3: 访问登录页
        print("【步骤3】访问登录页...")
        try:
            await self.page.goto('https://chat.deepseek.com/sign_in', wait_until='domcontentloaded')
            await asyncio.sleep(2)
            print("✅ 登录页加载完成")
        except Exception as e:
            print(f"❌ 登录页加载失败: {e}")
            return False
        
        # ===== 关键修复：用SVG特征定位密码登录按钮 =====
        print("【步骤4】用SVG特征定位密码登录按钮...")
        try:
            click_result = await self.page.evaluate('''
                () => {
                    const buttons = document.querySelectorAll('button.ds-sign-in-form__social-button');
                    
                    // 用SVG特征找密码登录按钮
                    for (let i = 0; i < buttons.length; i++) {
                        const btn = buttons[i];
                        const svg = btn.querySelector('svg');
                        if (svg) {
                            const path = svg.querySelector('path');
                            if (path) {
                                const d = path.getAttribute('d') || '';
                                // 密码登录按钮的SVG特征
                                if (d.includes('8.65039') || d.includes('M8.65039')) {
                                    btn.click();
                                    return {success: true, method: 'svg_match'};
                                }
                            }
                        }
                    }
                    
                    // 如果没找到，点第二个按钮（备用方案）
                    if (buttons.length >= 2) {
                        buttons[1].click();
                        return {success: true, method: 'fallback'};
                    }
                    return {success: false};
                }
            ''')
            
            print(f"点击结果: {click_result}")
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"❌ 点击按钮失败: {e}")
            return False
        # ============================================
        
        # 步骤5: 输入账号密码
        print("【步骤5】输入账号密码...")
        username = os.getenv("DEEPSEEK_USER")
        password = os.getenv("DEEPSEEK_PWD")
        
        if not username or not password:
            print("❌ 请设置账号密码")
            return False
        
        try:
            # 等待输入框出现
            await asyncio.sleep(1)
            inputs = await self.page.query_selector_all('input[type="text"], input[type="password"]')
            print(f"找到 {len(inputs)} 个输入框")
            
            if len(inputs) >= 2:
                await inputs[0].fill(username)
                print("✅ 账号已输入")
                await inputs[1].fill(password)
                print("✅ 密码已输入")
            else:
                print("❌ 输入框不足")
                return False
        except Exception as e:
            print(f"❌ 输入账号密码失败: {e}")
            return False
        
        # 步骤6: 点击登录按钮
        print("【步骤6】点击登录按钮...")
        try:
            login_btn = None
            buttons = await self.page.query_selector_all('button')
            for btn in buttons:
                btn_text = await btn.text_content()
                if btn_text and ('登录' in btn_text or '登陆' in btn_text):
                    login_btn = btn
                    print(f"找到登录按钮: {btn_text}")
                    break
            
            if login_btn:
                await login_btn.click()
                print("✅ 已点击登录按钮")
            else:
                print("❌ 找不到登录按钮")
                return False
        except Exception as e:
            print(f"❌ 点击登录按钮失败: {e}")
            return False
        
        # 步骤7: 等待登录成功
        print("【步骤7】等待登录成功...")
        for i in range(15):
            await asyncio.sleep(1)
            try:
                await self.page.wait_for_selector('textarea, div[contenteditable="true"]', timeout=1000)
                print("✅ 登录成功！")
                return True
            except:
                print(f"⏳ 等待登录... ({i+1}/15)")
                continue
        
        print("❌ 登录超时")
        return False
    
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
    
    async def wait_for_answer_complete(self, timeout=120):
        """等待回答完成"""
        try:
            await self.page.wait_for_selector('button:has-text("停止生成")', timeout=10)
            await self.page.wait_for_selector('button:has-text("停止生成")', state='hidden', timeout=timeout*1000)
            return True
        except:
            pass
        
        for i in range(20):
            try:
                messages = await self.page.query_selector_all('.ds-markdown, .markdown-body')
                if messages:
                    return True
            except:
                pass
            await asyncio.sleep(2)
        return True
    
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
            return result
        except:
            return False
    
    async def get_share_link_from_clipboard(self):
        """从剪贴板获取分享链接"""
        for attempt in range(3):
            try:
                text = await self.page.evaluate('async () => await navigator.clipboard.readText()')
                if text and text.startswith('https://chat.deepseek.com/share/'):
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
        print(f"\n🔍 处理: {query}")
        
        try:
            await self.new_conversation()
            
            input_box = await self.page.wait_for_selector('textarea, div[contenteditable="true"]', timeout=10000)
            await input_box.fill(query)
            await input_box.press('Enter')
            
            await self.wait_for_answer_complete()
            
            share_link = await self.get_share_link()
            
            if share_link:
                print(f"✅ 成功")
            else:
                print("❌ 失败")
            
            return share_link
            
        except Exception as e:
            print(f"❌ 错误: {e}")
            return None
    
    async def close(self):
        """关闭浏览器"""
        try:
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass
