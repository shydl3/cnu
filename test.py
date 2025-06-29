import asyncio
import json
import os.path
from os.path import splitext

from playwright.async_api import async_playwright
import aiohttp

main_page = "http://cnu.cc"
login_page = "http://www.cnu.cc/login"
fav_page = "http://www.cnu.cc/users/favorites"
fav_subpage = "http://www.cnu.cc/users/favorites?page=1"
wechat_login = "http://www.cnu.cc/auth/wechat-login/%7BisLogin%7D"

cookie_file = "auth_storage.json"

desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'CNU')

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

async def save_images_from_posts(page, post_url, title):
    print(f"📥 开始处理：{title} - {post_url}")
    await page.goto(post_url)

    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(2)

    img_json = await page.evaluate("document.getElementById('imgs_json')?.innerText")
    if not img_json:
        print("⚠️ 无法找到图片 JSON 数据，跳过..")
        return

    try:
        img_list = json.loads(img_json)
    except Exception as e:
        print(f"❌ JSON 解码失败: {e}")
        return

    save_path = os.path.join(desktop_path, title)
    # print(save_path)
    os.makedirs(save_path, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        for idx, img in enumerate(img_list):
            img_path = img.get("img")
            if not img_path:
                print(f"skipping {idx}")
                continue
            img_url = f"http://imgoss.cnu.cc/{img_path}?x-oss-process=style/content"
            ext = os.path.splitext(img_path)[-1].split("?")[0] or ".jpg"
            file_name = os.path.join(save_path, f"{idx + 1}{ext}")

            try:
                async with session.get(img_url) as resp:
                    if resp.status == 200:
                        with open(file_name, 'wb') as f:
                            f.write(await resp.read())
                        print(f"✅ 已保存：{file_name}")
                    else:
                        print(f"❌ 图片请求失败: {img_url}")
            except Exception as e:
                print(f"❌ 下载异常: {e}")

        print(f"🎉 完成：{title}")


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
        posts_list = await extract_posts(page)
        for post in posts_list:
            # print(post)
            post_title = post["title".replace("/", "_").replace("\\", "_")]
            post_url = post["url"]

            if not post_url.startswith("http"):
                post_url = "http://www.cnu.cc" + post_url
            await save_images_from_posts(page, post_url, post_title)

            # exit(0)


async def main():
    async with async_playwright() as p:
        context, page = await login(p)
        if context and page:
            await process_fav(page)

            print("🍀 测试结束")

            await asyncio.Event().wait()  # 保持窗口打开


asyncio.run(main())