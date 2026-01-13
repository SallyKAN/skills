"""
微信读书笔记导出工具 - 主入口

用法:
    python -m src.main login          # 登录微信读书
    python -m src.main scrape         # 抓取所有书籍笔记
    python -m src.main scrape --book "书名"  # 抓取指定书籍
    python -m src.main generate       # 生成知识卡片
    python -m src.main run            # 完整流程
    python -m src.main list           # 列出已抓取的书籍
"""

import argparse
from pathlib import Path

from .scraper import AuthManager, WeReadScraper
from .parser import NoteParser
from .generator import MarkdownCardGenerator


def cmd_login(args):
    """登录微信读书"""
    auth = AuthManager()
    auth.login_interactive(headless=False)
    print("登录成功！Cookie 已保存。")


def cmd_scrape(args):
    """抓取笔记"""
    scraper = WeReadScraper()
    try:
        if args.book:
            print(f"正在抓取书籍: {args.book}")
            scraper.scrape_all_books(book_filter=args.book)
        else:
            print("正在抓取所有书籍笔记...")
            scraper.scrape_all_books()
        print("抓取完成！")
    finally:
        scraper.close()


def cmd_generate(args):
    """生成知识卡片"""
    parser = NoteParser()
    output_dir = Path(args.output) if args.output else None
    generator = MarkdownCardGenerator(output_dir=output_dir)

    if args.book:
        # 查找匹配的书籍
        all_parsed = parser.load_all_parsed()
        matched = [p for p in all_parsed if args.book in p.book.title]
        if not matched:
            print(f"未找到书籍: {args.book}")
            return
        for parsed in matched:
            generator.generate_and_save(parsed, with_ai=not args.no_ai)
    else:
        all_parsed = parser.load_all_parsed()
        if not all_parsed:
            print("没有找到已抓取的笔记，请先运行 scrape 命令")
            return
        generator.generate_all(all_parsed, with_ai=not args.no_ai)

    print("知识卡片生成完成！")


def cmd_run(args):
    """完整流程：抓取 + 生成"""
    # 先抓取
    cmd_scrape(args)
    # 再生成
    cmd_generate(args)


def cmd_list(args):
    """列出已抓取的书籍"""
    scraper = WeReadScraper()
    books = scraper.list_saved_books()

    if not books:
        print("没有已抓取的书籍")
        return

    print(f"\n已抓取 {len(books)} 本书:\n")
    print(f"{'书名':<30} {'作者':<15} {'划线':<6} {'想法':<6} {'抓取时间'}")
    print("-" * 80)

    for book in books:
        title = book["title"][:28] + ".." if len(book["title"]) > 30 else book["title"]
        author = (
            book["author"][:13] + ".." if len(book["author"]) > 15 else book["author"]
        )
        scraped_at = book["scraped_at"][:10] if book["scraped_at"] else "未知"
        print(
            f"{title:<30} {author:<15} {book['highlights']:<6} {book['thoughts']:<6} {scraped_at}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="微信读书笔记导出工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # login 命令
    subparsers.add_parser("login", help="登录微信读书（扫码）")

    # scrape 命令
    scrape_parser = subparsers.add_parser("scrape", help="抓取笔记")
    scrape_parser.add_argument("--book", "-b", help="指定书名（模糊匹配）")

    # generate 命令
    gen_parser = subparsers.add_parser("generate", help="生成知识卡片")
    gen_parser.add_argument("--book", "-b", help="指定书名（模糊匹配）")
    gen_parser.add_argument("--output", "-o", help="输出目录")
    gen_parser.add_argument("--no-ai", action="store_true", help="不使用 AI 生成总结")

    # run 命令
    run_parser = subparsers.add_parser("run", help="完整流程：抓取 + 生成")
    run_parser.add_argument("--book", "-b", help="指定书名（模糊匹配）")
    run_parser.add_argument("--output", "-o", help="输出目录")
    run_parser.add_argument("--no-ai", action="store_true", help="不使用 AI 生成总结")

    # list 命令
    subparsers.add_parser("list", help="列出已抓取的书籍")

    args = parser.parse_args()

    if args.command == "login":
        cmd_login(args)
    elif args.command == "scrape":
        cmd_scrape(args)
    elif args.command == "generate":
        cmd_generate(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "list":
        cmd_list(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
