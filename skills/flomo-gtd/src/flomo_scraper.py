#!/usr/bin/env python3
"""
Flomo Web Scraper using Playwright

Automates login to Flomo and extracts notes with specific tags.
Saves browser state for subsequent runs without re-login.

Usage:
    # First run - will open browser for manual login
    python flomo_scraper.py --login

    # Subsequent runs - uses saved session
    python flomo_scraper.py --tag inbox --output notes.json

    # Export all notes
    python flomo_scraper.py --all --output all_notes.json

Requirements:
    pip install playwright
    playwright install chromium
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Error: playwright is required. Install with:")
    print("  pip install playwright")
    print("  playwright install chromium")
    sys.exit(1)


# Default paths
STATE_DIR = Path.home() / ".flomo-gtd"
STATE_FILE = STATE_DIR / "browser_state.json"
NOTES_CACHE = STATE_DIR / "notes_cache.json"


def ensure_state_dir():
    """Create state directory if it doesn't exist."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def login_and_save_state(headless: bool = False):
    """Open browser for manual login and save session state."""
    ensure_state_dir()

    print("Opening browser for Flomo login...")
    print("Please log in manually. The browser will close automatically after login.")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        # Go to Flomo login page
        page.goto("https://v.flomoapp.com/login")

        print("Waiting for login... (you have 5 minutes)")
        print("After logging in, you should see your notes page.")

        # Wait for successful login - check for main content
        try:
            # Wait for the main app to load (indicates successful login)
            page.wait_for_selector(".memo, .memos, [class*='memo']", timeout=300000)
            print("\nLogin successful! Saving session...")

            # Save browser state
            context.storage_state(path=str(STATE_FILE))
            print(f"Session saved to: {STATE_FILE}")

        except PlaywrightTimeout:
            print("\nLogin timeout. Please try again.")
            browser.close()
            return False

        browser.close()
        return True


def scrape_notes_by_tag(tag: str, max_scroll: int = 50) -> list[dict]:
    """Scrape notes with a specific tag."""
    if not STATE_FILE.exists():
        print("No saved session found. Please run with --login first.")
        sys.exit(1)

    notes = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(STATE_FILE))
        page = context.new_page()

        # Navigate to tag page
        tag_url = f"https://v.flomoapp.com/mine?tag={tag}"
        print(f"Navigating to: {tag_url}")
        page.goto(tag_url)

        # Wait for content to load
        try:
            page.wait_for_selector(".memo, .memos, [class*='memo']", timeout=30000)
        except PlaywrightTimeout:
            print("Failed to load notes. Session may have expired. Try --login again.")
            browser.close()
            return []

        print("Loading notes...")

        # Scroll to load all notes
        last_count = 0
        scroll_count = 0

        while scroll_count < max_scroll:
            # Get current notes
            memo_elements = page.query_selector_all(".memo, [class*='memo-item'], [class*='memo_']")
            current_count = len(memo_elements)

            if current_count == last_count:
                # No new notes loaded, we've reached the end
                break

            last_count = current_count
            scroll_count += 1

            # Scroll down
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)  # Wait for content to load

            print(f"  Loaded {current_count} notes...", end="\r")

        print(f"\nTotal notes found: {last_count}")

        # Extract note data
        memo_elements = page.query_selector_all(".memo, [class*='memo-item'], [class*='memo_']")

        for i, memo in enumerate(memo_elements):
            try:
                note = extract_note_data(memo)
                if note:
                    notes.append(note)
            except Exception as e:
                print(f"Warning: Failed to extract note {i}: {e}")

        # Update session state
        context.storage_state(path=str(STATE_FILE))
        browser.close()

    return notes


def scrape_all_notes(max_scroll: int = 100) -> list[dict]:
    """Scrape all notes from Flomo."""
    if not STATE_FILE.exists():
        print("No saved session found. Please run with --login first.")
        sys.exit(1)

    notes = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(STATE_FILE))
        page = context.new_page()

        # Navigate to main page
        print("Navigating to Flomo...")
        page.goto("https://v.flomoapp.com/mine")

        # Wait for content to load
        try:
            page.wait_for_selector(".memo, .memos, [class*='memo']", timeout=30000)
        except PlaywrightTimeout:
            print("Failed to load notes. Session may have expired. Try --login again.")
            browser.close()
            return []

        print("Loading all notes (this may take a while)...")

        # Scroll to load all notes
        last_count = 0
        scroll_count = 0
        no_change_count = 0

        while scroll_count < max_scroll:
            memo_elements = page.query_selector_all(".memo, [class*='memo-item'], [class*='memo_']")
            current_count = len(memo_elements)

            if current_count == last_count:
                no_change_count += 1
                if no_change_count >= 3:
                    break
            else:
                no_change_count = 0

            last_count = current_count
            scroll_count += 1

            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1.5)

            print(f"  Loaded {current_count} notes...", end="\r")

        print(f"\nTotal notes found: {last_count}")

        # Extract note data
        memo_elements = page.query_selector_all(".memo, [class*='memo-item'], [class*='memo_']")

        for i, memo in enumerate(memo_elements):
            try:
                note = extract_note_data(memo)
                if note:
                    notes.append(note)
            except Exception as e:
                print(f"Warning: Failed to extract note {i}: {e}")

        context.storage_state(path=str(STATE_FILE))
        browser.close()

    return notes


def extract_note_data(memo_element) -> dict | None:
    """Extract data from a memo element."""
    try:
        # Get full HTML for debugging
        html = memo_element.inner_html()

        # Extract text content
        content = memo_element.inner_text()

        # Extract tags from content
        tags = re.findall(r'#(\w+)', content)

        # Try to find date/time
        time_elem = memo_element.query_selector("time, .time, [class*='time'], [class*='date']")
        created_at = time_elem.inner_text() if time_elem else ""

        # Clean up content (remove extra whitespace)
        content = re.sub(r'\s+', ' ', content).strip()

        if not content:
            return None

        return {
            'content': content,
            'html_content': html,
            'tags': tags,
            'created_at': created_at,
            'scraped_at': datetime.now().isoformat(),
        }
    except Exception:
        return None


def filter_notes_by_tag(notes: list[dict], tag: str) -> list[dict]:
    """Filter notes that contain a specific tag."""
    tag_lower = tag.lower()
    return [note for note in notes if tag_lower in [t.lower() for t in note.get('tags', [])]]


def main():
    parser = argparse.ArgumentParser(description='Flomo Web Scraper')
    parser.add_argument('--login', action='store_true', help='Open browser for manual login')
    parser.add_argument('--tag', '-t', help='Filter notes by tag (e.g., inbox)')
    parser.add_argument('--all', '-a', action='store_true', help='Scrape all notes')
    parser.add_argument('--output', '-o', help='Output file path (default: stdout)')
    parser.add_argument('--format', '-f', choices=['json', 'text'], default='json', help='Output format')
    parser.add_argument('--max-scroll', type=int, default=50, help='Maximum scroll iterations')
    parser.add_argument('--headless', action='store_true', help='Run login in headless mode (not recommended)')

    args = parser.parse_args()

    if args.login:
        success = login_and_save_state(headless=args.headless)
        if success:
            print("\nYou can now run the scraper:")
            print(f"  python {sys.argv[0]} --tag inbox")
            print(f"  python {sys.argv[0]} --all")
        sys.exit(0 if success else 1)

    if not args.tag and not args.all:
        parser.print_help()
        print("\nError: Please specify --tag or --all")
        sys.exit(1)

    # Scrape notes
    if args.all:
        notes = scrape_all_notes(max_scroll=args.max_scroll)
    else:
        notes = scrape_notes_by_tag(args.tag, max_scroll=args.max_scroll)

    if not notes:
        print("No notes found.", file=sys.stderr)
        sys.exit(1)

    # Filter by tag if scraping all but want specific tag
    if args.all and args.tag:
        notes = filter_notes_by_tag(notes, args.tag)

    # Format output
    if args.format == 'json':
        output = json.dumps(notes, ensure_ascii=False, indent=2)
    else:
        lines = []
        for i, note in enumerate(notes, 1):
            lines.append(f"--- Note {i} ---")
            lines.append(f"Date: {note.get('created_at', 'Unknown')}")
            lines.append(f"Tags: {', '.join('#' + t for t in note.get('tags', []))}")
            lines.append(f"Content:\n{note.get('content', '')}")
            lines.append("")
        output = '\n'.join(lines)

    # Write output
    if args.output:
        Path(args.output).write_text(output, encoding='utf-8')
        print(f"Output written to: {args.output}", file=sys.stderr)
    else:
        print(output)

    print(f"\nTotal notes: {len(notes)}", file=sys.stderr)


if __name__ == '__main__':
    main()
