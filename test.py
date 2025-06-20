import asyncio
import os.path
from playwright.async_api import async_playwright

main_page = "http://cnu.cc"
login_page = "http://www.cnu.cc/login"
fav_page = "http://www.cnu.cc/users/favorites"
wechat_login = "http://www.cnu.cc/auth/wechat-login/%7BisLogin%7D"

cookie_file = "auth_storage.json"

async def login(p):
    browser = await p.chromium.launch(headless=False)

    if os.path.exists(cookie_file):
        context = await browser.new_context(locale="zh-CN", storage_state=cookie_file)
        print("✅ 已加载保存的 Cookie 登录状态")
    else:
        context = await browser.new_context(locale="zh-CN")
        print("🚫 未找到 Cookie，请扫码登录")

    page = await context.new_page()
    await page.goto(main_page)
    if not await page.locator("#userNav").is_visible(timeout=10000):
        print("🔒 Cookie 无效或未登录，进入扫码登录流程..")
        await page.goto(wechat_login)

        try:
            await page.wait_for_selector("#userNav", timeout=120000)
            print("✅ 登录成功！保存 Cookie...")
            await context.storage_state(path=cookie_file)
            await page.click("#userNav")

        except TimeoutError:
            print("❌ 登录超时，未能完成扫码")
            await browser.close()
            return None, None

    else:
        print("✅ 已登录")

    return context, page

async def process_fav(page):
    await page.click("#userNav")
    print("正在获取收藏列表..")
    await page.locator("#favLi").click(timeout=10000)


async def main():
    async with async_playwright() as p:
        context, page = await login(p)
        if context and page:
            await process_fav(page)


            await asyncio.Event().wait()  # 保持窗口打开

asyncio.run(main())