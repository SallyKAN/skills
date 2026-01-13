"""演示脚本：带截图的微信读书笔记导出流程"""

import time
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = Path("/tmp/weread_demo")
SCREENSHOT_DIR.mkdir(exist_ok=True)

# Cookie 路径
COOKIE_PATH = Path.home() / ".wechat-read-export" / "cookies.json"


def take_screenshot(page, name: str, description: str):
    """截图并打印说明"""
    path = SCREENSHOT_DIR / f"{name}.png"
    page.screenshot(path=path, full_page=False)
    print(f"\n📸 截图已保存: {path}")
    print(f"   说明: {description}")
    return path


def main():
    print("\n🚀 微信读书笔记导出演示")
    print("=" * 50)
    print(f"截图保存目录: {SCREENSHOT_DIR}")

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=False)

    # 加载已保存的 Cookie
    import json
    if COOKIE_PATH.exists():
        with open(COOKIE_PATH, "r") as f:
            storage_state = json.load(f)
        context = browser.new_context(storage_state=storage_state)
        print("✅ 已加载保存的登录状态")
    else:
        context = browser.new_context()
        print("⚠️ 未找到登录状态，需要扫码登录")

    page = context.new_page()

    # 设置 API 拦截
    captured_data = {}

    def handle_response(response):
        url = response.url
        if "weread.qq.com" in url and "json" in response.headers.get("content-type", ""):
            try:
                if "bookmarklist" in url:
                    captured_data["bookmarks"] = response.json()
                elif "review/list" in url and "mine=1" in url:
                    captured_data["reviews"] = response.json()
            except:
                pass

    page.on("response", handle_response)

    # ========== 步骤 1: 书架页面 ==========
    print("\n" + "=" * 50)
    print("步骤 1: 访问书架")
    print("=" * 50)

    page.goto("https://weread.qq.com/web/shelf")
    page.wait_for_load_state("networkidle")
    time.sleep(2)

    # 检查是否需要登录
    if "login" in page.url:
        print("\n⏳ 请使用微信扫描二维码登录...")
        take_screenshot(page, "01_login_qrcode", "微信读书登录页面 - 扫码登录")

        # 等待登录成功
        page.wait_for_url(
            lambda url: "login" not in url and "weread.qq.com" in url,
            timeout=120000,
        )
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # 保存 Cookie
        storage = context.storage_state()
        COOKIE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(COOKIE_PATH, "w") as f:
            json.dump(storage, f, ensure_ascii=False, indent=2)
        print("✅ 登录成功，Cookie 已保存")

        # 重新访问书架
        page.goto("https://weread.qq.com/web/shelf")
        page.wait_for_load_state("networkidle")
        time.sleep(2)

    # 截图：书架页面
    take_screenshot(page, "02_bookshelf", "我的书架 - 显示所有书籍")

    # 获取书籍列表
    book_elements = page.query_selector_all(".shelfBook")
    print(f"\n📚 找到 {len(book_elements)} 本书")

    # ========== 步骤 2: 选择书籍并获取笔记 ==========
    print("\n" + "=" * 50)
    print("步骤 2: 获取书籍笔记")
    print("=" * 50)

    first_book = book_elements[0] if book_elements else None
    if not first_book:
        print("❌ 未找到书籍")
        return

    href = first_book.get_attribute("href") or ""
    book_id = href.replace("/web/reader/", "")
    title_elem = first_book.query_selector(".title")
    title = title_elem.get_attribute("title") if title_elem else "未知"

    print(f"📖 选择书籍: {title}")

    # 访问阅读器页面获取笔记
    print("正在获取笔记数据...")
    reader_url = f"https://weread.qq.com/web/reader/{book_id}"
    page.goto(reader_url)
    page.wait_for_load_state("networkidle")
    time.sleep(3)

    # 截图：阅读器页面
    take_screenshot(page, "03_reader", f"阅读器页面 - {title}")

    # 提取笔记数据
    bookmarks = captured_data.get("bookmarks", {})
    highlights = bookmarks.get("updated", [])
    chapters = {c.get("chapterUid"): c.get("title", "") for c in bookmarks.get("chapters", [])}
    book_info = bookmarks.get("book", {})

    print(f"✅ 获取到 {len(highlights)} 条划线")

    # ========== 步骤 3: 生成知识卡片 ==========
    print("\n" + "=" * 50)
    print("步骤 3: 生成知识卡片")
    print("=" * 50)

    output_dir = SCREENSHOT_DIR / "output"
    output_dir.mkdir(exist_ok=True)

    # 按章节组织划线
    chapter_highlights = {}
    for h in highlights:
        chapter_uid = h.get("chapterUid", 0)
        chapter_name = chapters.get(chapter_uid, "未知章节")
        if chapter_name not in chapter_highlights:
            chapter_highlights[chapter_name] = []
        chapter_highlights[chapter_name].append(h.get("markText", ""))

    # 生成 Markdown
    highlights_md = ""
    for chapter, texts in chapter_highlights.items():
        highlights_md += f"\n### {chapter}\n"
        for text in texts[:3]:  # 每章最多3条
            if text:
                highlights_md += f"\n> {text}\n"

    card_content = f"""# 《{title}》知识卡片

## 书籍信息

- **书名**: {title}
- **作者**: {book_info.get('author', '未知')}
- **划线数量**: {len(highlights)}
- **导出时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 精华摘录
{highlights_md}

---
*由 wechat-read-export 自动生成*
"""

    card_path = output_dir / f"{title}_知识卡片.md"
    with open(card_path, "w", encoding="utf-8") as f:
        f.write(card_content)

    print(f"✅ 知识卡片已生成: {card_path}")

    # 显示卡片预览
    print("\n" + "-" * 40)
    print("📄 知识卡片预览:")
    print("-" * 40)
    preview = card_content[:800] + "..." if len(card_content) > 800 else card_content
    print(preview)

    # ========== 汇总 ==========
    print("\n" + "=" * 50)
    print("📸 所有截图:")
    print("=" * 50)
    for f in sorted(SCREENSHOT_DIR.glob("*.png")):
        print(f"  - {f}")

    print(f"\n📄 知识卡片: {card_path}")

    # 关闭浏览器
    context.close()
    browser.close()
    playwright.stop()

    print("\n✨ 演示完成！")


if __name__ == "__main__":
    main()
