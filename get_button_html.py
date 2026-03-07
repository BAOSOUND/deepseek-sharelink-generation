"""
获取按钮HTML的调试脚本
"""

import asyncio
from playwright.async_api import async_playwright

async def get_html():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            channel="msedge"
        )
        page = await browser.new_page()
        
        await page.goto('https://chat.deepseek.com')
        input("\n请手动登录并让答案生成，然后按回车...")
        
        # 获取包含5个按钮的div的HTML
        button_container_html = await page.evaluate('''
            () => {
                // 查找包含5个按钮的容器
                const containers = document.querySelectorAll('div.ds-flex');
                for (let container of containers) {
                    const buttons = container.querySelectorAll('button');
                    if (buttons.length >= 5) {
                        return {
                            found: true,
                            html: container.outerHTML,
                            buttonCount: buttons.length
                        };
                    }
                }
                return {found: false};
            }
        ''')
        
        if button_container_html.get('found'):
            print(f"\n找到包含 {button_container_html['buttonCount']} 个按钮的容器")
            print("\n容器HTML:")
            print(button_container_html['html'])
        else:
            print("未找到包含5个按钮的容器")
        
        input("\n按回车退出...")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_html())
