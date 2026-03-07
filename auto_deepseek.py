"""
DeepSeek网页版自动化模块 - 优化版（支持跨平台：Windows用Chrome，Linux用Chromium）
"""

import asyncio
import json
import time
import re
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class DeepSeekAuto:
    """DeepSeek自动化操作类"""
    
    def __init__(self, headless=True, timeout=60):
        self.headless = headless
        self.timeout = timeout * 1000
        self.base_dir = Path(__file__).parent
        self.user_data_dir = self.base_dir / "browser_data"
        self.user_data_dir.mkdir(exist_ok=True)
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self._last_share_link = None
        self._last_read_link = None
        
    async def start(self):
        """启动浏览器 - 根据平台自动选择"""
        self.playwright = await async_playwright().start()
        
        # ===== 根据运行环境选择浏览器 =====
        is_windows = sys.platform.startswith('win')
        is_linux = sys.platform.startswith('linux')
        
        # 基础启动参数
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
        
        if is_windows:
            # Windows 下用 Chrome
            launch_options['channel'] = "chrome"
            launch_options['user_agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            print("🖥️ Windows环境: 使用 Chrome 浏览器")
        elif is_linux:
            # Linux 下用 Chromium（不带channel）
            launch_options['user_agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            print("🐧 Linux环境: 使用 Chromium 浏览器")
        else:
            # 其他系统默认
            print("⚠️ 未知环境: 使用默认浏览器")
        
        self.context = await self.playwright.chromium.launch_persistent_context(**launch_options)
        
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        self.page.set_default_timeout(self.timeout)
        
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        return self
    
    async def ensure_login(self):
        """确保已登录 - 加速版"""
        
        # ============= 快速检测登录状态 =============
        print("🔍 检测登录状态...")
        
        # 直接访问主页（只等1秒）
        await self.page.goto('https://chat.deepseek.com', wait_until='domcontentloaded')
        await self.page.wait_for_load_state('networkidle')
        
        try:
            # 快速检测输入框（只等500ms）
            await self.page.wait_for_selector('textarea, div[contenteditable="true"]', timeout=500)
            print("✅ 已登录")
            return True
        except:
            print("⏱️ 未登录")
        
        # ============= 直接访问登录页 =============
        print("⚡ 访问登录页...")
        await self.page.goto('https://chat.deepseek.com/sign_in', wait_until='domcontentloaded')
        
        try:
            # ============= 切换到密码登录 =============
            print("切换到密码登录...")
            
            # 直接找密码登录按钮（基于SVG特征）
            click_result = await self.page.evaluate('''
                () => {
                    const buttons = document.querySelectorAll('button.ds-sign-in-form__social-button');
                    
                    // 直接找密码登录按钮
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
                    
                    // 如果没找到，点第二个
                    if (buttons.length >= 2) {
                        buttons[1].click();
                        return {success: true, method: 'fallback'};
                    }
                    return {success: false};
                }
            ''')
            
            print(f"点击结果: {click_result}")
            await asyncio.sleep(0.5)
            
            # ============= 输入账号密码 =============
            username = os.getenv("DEEPSEEK_USER")
            password = os.getenv("DEEPSEEK_PWD")
            
            if not username or not password:
                print("❌ 请设置账号密码")
                return False
            
            # 快速输入
            await self.page.wait_for_selector('input', timeout=3000)
            inputs = await self.page.query_selector_all('input')
            
            if len(inputs) >= 2:
                await inputs[0].fill(username)
                await inputs[1].fill(password)
                print("✅ 账号密码已输入")
                
                # ============= 点击登录 =============
                # 直接找登录按钮
                login_btn = None
                buttons = await self.page.query_selector_all('button')
                for btn in buttons:
                    btn_text = await btn.text_content()
                    if btn_text and ('登录' in btn_text or '登陆' in btn_text):
                        login_btn = btn
                        break
                
                if login_btn:
                    await login_btn.click()
                    print("✅ 点击登录")
                    
                    # 快速等待登录成功
                    try:
                        await self.page.wait_for_selector('textarea, div[contenteditable="true"]', timeout=5000)
                        print("✅ 登录成功！")
                        return True
                    except:
                        print("❌ 登录失败")
                        return False
                else:
                    print("❌ 找不到登录按钮")
                    return False
            else:
                print(f"❌ 输入框不足: {len(inputs)}")
                return False
                
        except Exception as e:
            print(f"登录出错: {e}")
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
            await asyncio.sleep(0.3)
        except:
            pass
    
    async def wait_for_answer_complete(self, timeout=120):
        """
        等待回答完全生成 - 稳定计数改为1次
        """
        print("等待AI生成完整回答...")
        
        # 方法1：等待"停止生成"按钮
        try:
            await self.page.wait_for_selector('button:has-text("停止生成")', timeout=10)
            print("✅ 检测到开始生成")
            await self.page.wait_for_selector('button:has-text("停止生成")', state='hidden', timeout=timeout*1000)
            print("✅ 检测到生成完成")
            return True
        except:
            pass
        
        # 方法2：监控内容变化（稳定1次即可）
        print("监控内容变化...")
        last_content = ""
        
        for i in range(20):
            try:
                messages = await self.page.query_selector_all('.ds-markdown, .markdown-body, [class*="message"]')
                if messages:
                    last_msg = messages[-1]
                    current_text = await last_msg.text_content()
                    current_text = current_text.strip() if current_text else ""
                    
                    if current_text and len(current_text) > 0:
                        if current_text != last_content:
                            print(f"⏳ 内容变化: {len(current_text)}字符")
                            last_content = current_text
                        else:
                            print("✅ 内容稳定，生成完成")
                            return True
            except:
                pass
            
            await asyncio.sleep(2)
        
        print("⚠️ 等待超时")
        return True
    
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
            return False
        except:
            return False
    
    async def click_create_share(self):
        """第二步：点击创建分享"""
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
            return False
        except:
            return False
    
    async def click_create_and_copy(self):
        """第三步：点击创建并复制"""
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
            return False
        except:
            return False
    
    async def get_share_link_from_clipboard(self):
        """从剪贴板获取分享链接"""
        for attempt in range(3):
            try:
                text = await self.page.evaluate('''
                    async () => {
                        try {
                            const text = await navigator.clipboard.readText();
                            return text;
                        } catch (e) {
                            return null;
                        }
                    }
                ''')
                if text and text.startswith('https://chat.deepseek.com/share/'):
                    if text != self._last_read_link:
                        self._last_read_link = text
                        print(f"✅ 获取到分享链接")
                        return text
            except:
                pass
            await asyncio.sleep(0.5)
        return None
    
    async def get_share_link(self):
        """获取分享链接"""
        
        if not await self.click_share_button():
            return None
        
        if not await self.click_create_share():
            return None
        
        if not await self.click_create_and_copy():
            return None
        
        return await self.get_share_link_from_clipboard()
    
    async def search_and_get_share_link(self, query):
        """搜索并获取分享链接 - 调试版"""
        print(f"\n🔍 搜索: {query}")
        
        try:
            print("📸 步骤1: 开启新对话")
            await self.new_conversation()
            
            print("📸 步骤2: 找输入框")
            input_box = await self.page.wait_for_selector('textarea, div[contenteditable="true"]', timeout=10000)
            print(f"✅ 找到输入框: {input_box}")
            
            print("📸 步骤3: 输入问题")
            await input_box.fill(query)
            print("✅ 问题已输入")
            
            print("📸 步骤4: 按回车")
            await input_box.press('Enter')
            print("✅ 已发送")
            
            print("📸 步骤5: 等待回答")
            await self.wait_for_answer_complete()
            
            print("📸 步骤6: 尝试点击分享按钮")
            share_result = await self.click_share_button()
            print(f"点击分享按钮结果: {share_result}")
            
            if not share_result:
                # 截图看看页面状态
                await self.page.screenshot(path="debug_share_button.png")
                print("📸 已保存截图: debug_share_button.png")
                return None
            
            print("📸 步骤7: 点击创建分享")
            create_result = await self.click_create_share()
            print(f"点击创建分享结果: {create_result}")
            
            print("📸 步骤8: 点击创建并复制")
            copy_result = await self.click_create_and_copy()
            print(f"点击创建并复制结果: {copy_result}")
            
            print("📸 步骤9: 获取链接")
            share_link = await self.get_share_link_from_clipboard()
            
            if share_link:
                print(f"\n🎉 获取到分享链接: {share_link}")
            else:
                print("\n❌ 获取失败")
                # 截图看看弹窗状态
                await self.page.screenshot(path="debug_clipboard.png")
                print("📸 已保存截图: debug_clipboard.png")
            
        return share_link
            
        except Exception as e:
            print(f"❌ 搜索出错: {e}")
            # 出错时截图
            try:
                await self.page.screenshot(path=f"error_{int(time.time())}.png")
                print(f"📸 已保存错误截图")
            except:
                pass
            return None
    
    async def close(self):
        """关闭浏览器"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("✅ 浏览器已关闭")