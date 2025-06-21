import asyncio
import os.path
from playwright.async_api import async_playwright

main_page = "http://cnu.cc"
login_page = "http://www.cnu.cc/login"
fav_page = "http://www.cnu.cc/users/favorites"
fav_subpage = "http://www.cnu.cc/users/favorites?page=1"
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

async def extract_posts(page):
    await page.wait_for_selector(".work-thumbnail", timeout=10000)
    items = page.locator(".work-thumbnail")
    count = await items.count()
    print(f"✅ 本页共有 {count} 个收藏作品")

    results = []

    for i in range(count):
        item = items.nth(i).locator("a.thumbnail")
        href = await item.get_attribute("href")
        title = await item.locator(".title").text_content()
        results.append({
            "title": title.strip() if title else "(无标题)",
            "url": href.strip() if href else "#"
        })

    return results


async def get_total_pages(page):
    await page.wait_for_selector("ul.pagination", timeout=10000)
    li_count = await page.locator(".pagination > li").count()
    page_count = li_count - 2

    return page_count


async def process_fav(page):
    await page.click("#userNav")
    print("🔄 正在获取收藏列表..")
    await page.locator("#favLi").click(timeout=10000)

    page_count = await get_total_pages(page)
    print(f"✅ 收藏夹共有 {page_count} 页")

    for page_num in range(1, page_count+1):
        url = f"http://www.cnu.cc/users/favorites?page={page_num}"
        print(f"🔄 正在访问第 {page_num} 页: {url}")
        await page.goto(url)
        results = await extract_posts(page)
        for res in results:
            print(res)


async def main():
    async with async_playwright() as p:
        context, page = await login(p)
        if context and page:
            await process_fav(page)

            print("🍀 测试结束")

            await asyncio.Event().wait()  # 保持窗口打开

asyncio.run(main())