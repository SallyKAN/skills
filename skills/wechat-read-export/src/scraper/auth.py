"""
微信读书认证管理模块

处理 Cookie 的保存、加载和验证
"""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright, Browser, BrowserContext


class AuthManager:
    """微信读书认证管理器"""

    WEREAD_URL = "https://weread.qq.com"
    LOGIN_URL = "https://weread.qq.com/#login"
    DEFAULT_STATE_DIR = Path.home() / ".wechat-read-export"
    COOKIE_FILE = "cookies.json"

    def __init__(self, state_dir: Path | None = None):
        self.state_dir = state_dir or self.DEFAULT_STATE_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.cookie_path = self.state_dir / self.COOKIE_FILE

    def has_saved_cookies(self) -> bool:
        """检查是否有已保存的 Cookie"""
        return self.cookie_path.exists()

    def save_cookies(self, context: BrowserContext) -> None:
        """保存浏览器 Cookie"""
        storage_state = context.storage_state()
        with open(self.cookie_path, "w", encoding="utf-8") as f:
            json.dump(storage_state, f, ensure_ascii=False, indent=2)
        print(f"Cookie 已保存到: {self.cookie_path}")

    def load_cookies(self) -> dict | None:
        """加载已保存的 Cookie"""
        if not self.has_saved_cookies():
            return None
        with open(self.cookie_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def clear_cookies(self) -> None:
        """清除已保存的 Cookie"""
        if self.cookie_path.exists():
            self.cookie_path.unlink()
            print("Cookie 已清除")

    def login_interactive(self, headless: bool = False) -> BrowserContext:
        """
        交互式登录（扫码）

        Args:
            headless: 是否无头模式（登录时必须为 False）

        Returns:
            已登录的浏览器上下文
        """
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        print("正在打开微信读书登录页面...")
        page.goto(self.LOGIN_URL)

        print("请使用微信扫描二维码登录...")
        print("登录成功后，程序会自动继续")

        # 等待登录成功（检测 URL 变化或特定元素出现）
        page.wait_for_url(
            lambda url: "login" not in url and "weread.qq.com" in url,
            timeout=120000,  # 2 分钟超时
        )

        # 等待页面完全加载，确保所有 Cookie 都已设置
        page.wait_for_load_state("networkidle")
        import time
        time.sleep(2)  # 额外等待确保 Cookie 完全设置

        print("登录成功！")
        self.save_cookies(context)

        # 打印保存的 Cookie 信息用于调试
        storage = context.storage_state()
        print(f"保存了 {len(storage.get('cookies', []))} 个 Cookie")
        for cookie in storage.get('cookies', []):
            print(f"  - {cookie['name']}: {cookie['value'][:20]}...")

        return context

    def get_authenticated_context(
        self, headless: bool = True
    ) -> tuple[BrowserContext, bool]:
        """
        获取已认证的浏览器上下文

        自动降级策略：先尝试已保存的 Cookie，失败则引导扫码登录

        Args:
            headless: 是否无头模式

        Returns:
            (浏览器上下文, 是否为新登录)
        """
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=headless)

        # 尝试使用已保存的 Cookie
        if self.has_saved_cookies():
            print("尝试使用已保存的 Cookie...")
            storage_state = self.load_cookies()
            context = browser.new_context(storage_state=storage_state)
            page = context.new_page()

            # 验证 Cookie 是否有效
            page.goto(self.WEREAD_URL)
            page.wait_for_load_state("networkidle")

            # 检查是否需要登录
            if "login" not in page.url:
                print("Cookie 有效，已自动登录")
                return context, False
            else:
                print("Cookie 已过期，需要重新登录")
                context.close()
                browser.close()
                playwright.stop()

        # Cookie 无效或不存在，进行交互式登录
        if headless:
            print("需要登录，但当前为无头模式。请使用 'login' 命令先登录。")
            raise RuntimeError("需要先登录微信读书")

        return self.login_interactive(headless=False), True

    def verify_login(self, context: BrowserContext) -> bool:
        """验证当前上下文是否已登录"""
        page = context.new_page()
        page.goto(self.WEREAD_URL)
        page.wait_for_load_state("networkidle")
        is_logged_in = "login" not in page.url
        page.close()
        return is_logged_in
