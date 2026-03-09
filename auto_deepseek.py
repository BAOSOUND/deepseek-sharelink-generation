"""
DeepSeek网页版自动化模块 - 修复类型错误
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
        else:
            launch_options['channel'] = "chrome"
            launch_options['user_agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
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
        """确保已登录 - 智能检测登录界面"""
        
        print("\n========== 开始登录流程 ==========")
        
        # 第一步：访问主页
        print("【1】访问主页...")
        await self.page.goto('https://chat.deepseek.com')
        await asyncio.sleep(1)
        
        # 第二步：检查是否已登录
        print("【2】检查登录状态...")
        try:
            await self.page.wait_for_selector('textarea', timeout=2000)
            print("✅ 已登录，无需再次登录")
            return True
        except:
            print("🔐 未登录，开始登录流程")
        
        # 第三步：跳转到登录页
        print("【3】跳转到登录页...")
        await self.page.goto('https://chat.deepseek.com/sign_in')
        await asyncio.sleep(2)
        
        # 第四步：智能检测当前登录界面类型
        print("【4】检测登录界面类型...")
        
        # 检测是否已经是密码登录界面（有输入框）
        has_inputs = await self.page.evaluate('''
            () => {
                const inputs = document.querySelectorAll('input[type="text"], input[type="password"]');
                return inputs.length >= 2;
            }
        ''')
        
        if has_inputs:
            print("✅ 检测到已经是密码登录界面，直接输入账号密码")
        else:
            print("🔄 检测到社交登录界面，需要切换到密码登录")
            try:
                # 用SVG特征找密码登录按钮
                await self.page.evaluate('''
                    () => {
                        const buttons = document.querySelectorAll('button.ds-sign-in-form__social-button');
                        for (let btn of buttons) {
                            const svg = btn.querySelector('svg');
                            if (svg) {
                                const path = svg.querySelector('path');
                                if (path) {
                                    const d = path.getAttribute('d') || '';
                                    if (d.includes('8.65039')) {
                                        btn.click();
                                        return;
                                    }
                                }
                            }
                        }
                        if (buttons.length >= 2) buttons[1].click();
                    }
                ''')
                print("✅ 已点击密码登录按钮")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"❌ 点击密码登录按钮失败: {e}")
                return False
        
        # 第五步：输入账号密码
        print("【5】输入账号密码...")
        username = os.getenv("DEEPSEEK_USER")
        password = os.getenv("DEEPSEEK_PWD")
        
        if not username or not password:
            print("❌ 请设置环境变量")
            return False
        
        try:
            await asyncio.sleep(0.5)
            inputs = await self.page.query_selector_all('input')
            print(f"找到 {len(inputs)} 个输入框")
            
            if len(inputs) >= 2:
                await inputs[0].fill(username)
                masked_username = username[:4] + "****" + username[-4:] if len(username) > 8 else "****"
                print(f"✅ 账号已输入: {masked_username}")
                await inputs[1].fill(password)
                print("✅ 密码已输入")
            else:
                print("❌ 输入框不足")
                return False
        except Exception as e:
            print(f"❌ 输入账号密码失败: {e}")
            return False
        
        # 第六步：点击登录按钮（多语言支持）
        print("【6】点击登录按钮...")
        try:
            login_texts = ['登录', '登陆', 'Sign in', 'Log in', 'Sign In', 'Log In']
            
            login_btn = None
            buttons = await self.page.query_selector_all('button')
            
            for btn in buttons:
                btn_text = await btn.text_content()
                if btn_text:
                    btn_text = btn_text.strip()
                    for text in login_texts:
                        if text in btn_text:
                            login_btn = btn
                            print(f"✅ 找到登录按钮: '{btn_text}'")
                            break
                    if login_btn:
                        break
            
            if not login_btn:
                login_btn = await self.page.query_selector('button[type="submit"]')
                if login_btn:
                    print("✅ 找到提交按钮")
            
            if not login_btn and len(buttons) > 0:
                login_btn = buttons[-1]
                print("✅ 使用最后一个按钮")
            
            if login_btn:
                await login_btn.click()
                print("✅ 已点击登录按钮")
            else:
                print("❌ 找不到登录按钮")
                return False
        except Exception as e:
            print(f"❌ 点击登录按钮失败: {e}")
            return False
        
        # 第七步：等待登录成功
        print("【7】等待登录成功...")
        for i in range(15):
            await asyncio.sleep(1)
            try:
                await self.page.wait_for_selector('textarea', timeout=1000)
                print("✅ 登录成功！")
                return True
            except:
                print(f"⏳ 等待登录... ({i+1}/15)")
                continue
        
        print("❌ 登录超时")
        return False
    
    async def wait_for_answer_complete(self, timeout=30):
        """等待AI回答完全生成 - 快速版"""
        print("等待AI生成完整回答...")
        
        try:
            await self.page.wait_for_selector('button:has-text("停止生成")', timeout=5000)
            print("✅ 检测到开始生成")
            await self.page.wait_for_selector('button:has-text("停止生成")', state='hidden', timeout=20000)
            print("✅ 检测到生成完成")
            await asyncio.sleep(0.5)
            return True
        except:
            pass
        
        print("监控内容变化...")
        last_length = 0
        
        for i in range(20):
            try:
                messages = await self.page.query_selector_all('.ds-markdown, .markdown-body')
                if messages:
                    last_msg = messages[-1]
                    current_text = await last_msg.text_content() or ""
                    current_length = len(current_text.strip())
                    
                    if current_length > 0:
                        print(f"⏳ 内容长度: {current_length} 字符")
                        if current_length == last_length:
                            print("✅ 内容稳定，生成完成")
                            return True
                        last_length = current_length
            except:
                pass
            await asyncio.sleep(0.5)
        
        print("✅ 继续执行")
        return True
    
    async def new_conversation(self):
        """开启新对话"""
        try:
            await self.page.evaluate('''
                () => {
                    const newChatBtn = document.querySelector('div._5a8ac7a.a084f19e');
                    if (newChatBtn) newChatBtn.click();
                }
            ''')
            await asyncio.sleep(0.3)
        except:
            pass
    
    async def click_share_button(self):
        """第一步：点击分享按钮"""
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
                                    return true;
                                }
                            }
                        }
                    }
                    return false;
                }
            ''')
            if result:
                print("✅ 点击分享按钮")
                return True
            print("❌ 找不到分享按钮")
            return False
        except Exception as e:
            print(f"❌ 点击分享按钮出错: {e}")
            return False

    async def click_create_share(self):
        """第二步：点击创建分享按钮"""
        try:
            result = await self.page.evaluate('''
                () => {
                    const buttons = document.querySelectorAll('button, [role="button"]');
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
                print("✅ 点击创建分享")
                return True
            print("❌ 找不到创建分享按钮")
            return False
        except Exception as e:
            print(f"❌ 点击创建分享出错: {e}")
            return False

    async def click_create_and_copy(self):
        """第三步：点击创建并复制按钮"""
        try:
            result = await self.page.evaluate('''
                () => {
                    const buttons = document.querySelectorAll('button, [role="button"]');
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
                print("✅ 点击创建并复制")
                return True
            print("❌ 找不到创建并复制按钮")
            return False
        except Exception as e:
            print(f"❌ 点击创建并复制出错: {e}")
            return False

    # ===== 修复类型错误 =====
    async def get_share_link(self):
        """获取分享链接 - 修复类型错误"""
        print("开始获取分享链接...")
        
        try:
            if not await self.click_share_button():
                return None
            await asyncio.sleep(1)
            
            if not await self.click_create_share():
                return None
            await asyncio.sleep(1)
            
            if not await self.click_create_and_copy():
                return None
            await asyncio.sleep(1)
            
            # 从剪贴板获取链接
            for attempt in range(3):
                try:
                    text = await self.page.evaluate('async () => await navigator.clipboard.readText()')
                    if text and isinstance(text, str) and text.startswith('https://chat.deepseek.com/share/'):
                        print(f"✅ 获取到分享链接")
                        return text
                    else:
                        print(f"⏳ 等待有效链接... ({attempt+1}/3)")
                except Exception as e:
                    print(f"⏳ 等待剪贴板... ({attempt+1}/3)")
                await asyncio.sleep(1)
            
            print("❌ 获取链接失败")
            return None
        except Exception as e:
            print(f"❌ 获取链接过程出错: {e}")
            return None
    # =========================
    
    async def search_and_get_share_link(self, query):
        """搜索并获取分享链接"""
        print(f"\n🔍 处理: {query}")
        
        try:
            await self.new_conversation()
            
            input_box = await self.page.wait_for_selector('textarea, div[contenteditable="true"]', timeout=5000)
            await input_box.fill(query)
            print("✅ 问题已输入")
            
            await input_box.press('Enter')
            print("✅ 已发送，等待回答...")
            
            await self.wait_for_answer_complete()
            
            share_link = await self.get_share_link()
            
            if share_link:
                print(f"✅ 成功获取链接")
            else:
                print("❌ 获取链接失败")
            
            return share_link
            
        except Exception as e:
            print(f"❌ 处理问题出错: {e}")
            return None
    
    async def close(self):
        """关闭浏览器"""
        try:
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
            print("✅ 浏览器已关闭")
        except:
            pass
