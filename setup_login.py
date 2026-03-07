"""
首次登录设置脚本 - 修复版
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
    print("=" * 50)
    print("🔐 DeepSeek 首次登录设置")
    print("=" * 50)
    
    # 创建cookies目录
    Path("cookies").mkdir(exist_ok=True)
    
    print("\n正在启动浏览器...")
    
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )
        
        context = await browser.new_context()
        page = await context.new_page()
        
        # 打开DeepSeek
        await page.goto('https://chat.deepseek.com')
        print("\n🌐 浏览器已打开，请完成以下步骤：")
        print("1. 在浏览器中登录你的 DeepSeek 账号")
        print("2. 登录成功后，确认能看到对话输入框")
        print("3. 回到此终端，按回车键继续...")
        
        input("\n按回车键保存Cookie并退出...")
        
        # 保存Cookie
        cookies = await context.cookies()
        cookies_file = Path("cookies") / "deepseek_cookies.json"
        with open(cookies_file, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Cookie已保存到: {cookies_file}")
        print(f"📊 共保存了 {len(cookies)} 个Cookie")
        
        await browser.close()
    
    print("\n🎉 设置完成！现在可以正常运行 app.py 了")

if __name__ == "__main__":
    asyncio.run(main())
