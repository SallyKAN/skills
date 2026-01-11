#!/usr/bin/env python3
"""
Flomo HTML Export Parser

Parses Flomo's HTML export files and extracts notes with optional tag filtering.

Usage:
    python parse_flomo.py /path/to/flomo/export --tag inbox
    python parse_flomo.py /path/to/flomo/export --all
    python parse_flomo.py /path/to/flomo.html --tag inbox --output notes.json
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: beautifulsoup4 is required. Install with: pip install beautifulsoup4")
    sys.exit(1)


def parse_flomo_html(html_content: str) -> list[dict]:
    """Parse Flomo HTML export and extract all notes."""
    soup = BeautifulSoup(html_content, 'html.parser')
    notes = []

    # Flomo exports notes in .memo divs
    memo_divs = soup.find_all('div', class_='memo')

    for memo in memo_divs:
        note = extract_note_from_memo(memo)
        if note:
            notes.append(note)

    # Alternative structure: some exports use different class names
    if not notes:
        # Try finding notes by content structure
        for item in soup.find_all(['div', 'article'], class_=re.compile(r'(memo|note|item|card)')):
            note = extract_note_from_memo(item)
            if note:
                notes.append(note)

    return notes


def extract_note_from_memo(memo_element) -> dict | None:
    """Extract note data from a memo element."""
    try:
        # Extract content
        content_elem = memo_element.find('div', class_='content') or memo_element.find('p') or memo_element
        content = content_elem.get_text(strip=True) if content_elem else ""

        # Extract HTML content for rich text
        html_content = str(content_elem) if content_elem else ""

        # Extract tags (Flomo uses #tag format in content)
        tags = re.findall(r'#(\w+)', content)

        # Extract date/time
        time_elem = memo_element.find('div', class_='time') or memo_element.find('time') or memo_element.find('span', class_=re.compile(r'(time|date)'))
        created_at = time_elem.get_text(strip=True) if time_elem else ""

        # Try to parse the date
        parsed_date = None
        if created_at:
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M', '%Y-%m-%d']:
                try:
                    parsed_date = datetime.strptime(created_at, fmt).isoformat()
                    break
                except ValueError:
                    continue

        if not content:
            return None

        return {
            'content': content,
            'html_content': html_content,
            'tags': tags,
            'created_at': created_at,
            'parsed_date': parsed_date,
        }
    except Exception as e:
        print(f"Warning: Failed to parse memo element: {e}", file=sys.stderr)
        return None


def filter_notes_by_tag(notes: list[dict], tag: str) -> list[dict]:
    """Filter notes that contain a specific tag."""
    tag_lower = tag.lower()
    return [note for note in notes if tag_lower in [t.lower() for t in note.get('tags', [])]]


def load_flomo_export(path: str) -> str:
    """Load Flomo export from file or directory."""
    path = Path(path).expanduser()

    if path.is_file():
        if path.suffix == '.html':
            return path.read_text(encoding='utf-8')
        elif path.suffix == '.zip':
            import zipfile
            with zipfile.ZipFile(path, 'r') as zf:
                # Find HTML files in the zip
                html_files = [f for f in zf.namelist() if f.endswith('.html')]
                if html_files:
                    # Combine all HTML content
                    contents = []
                    for hf in html_files:
                        contents.append(zf.read(hf).decode('utf-8'))
                    return '\n'.join(contents)
            raise ValueError(f"No HTML files found in ZIP: {path}")
    elif path.is_dir():
        # Find all HTML files in directory
        html_files = list(path.glob('**/*.html'))
        if not html_files:
            raise ValueError(f"No HTML files found in directory: {path}")
        contents = []
        for hf in html_files:
            contents.append(hf.read_text(encoding='utf-8'))
        return '\n'.join(contents)
    else:
        raise FileNotFoundError(f"Path not found: {path}")


def main():
    parser = argparse.ArgumentParser(description='Parse Flomo HTML export')
    parser.add_argument('path', help='Path to Flomo export (HTML file, ZIP file, or directory)')
    parser.add_argument('--tag', '-t', help='Filter notes by tag (e.g., inbox)')
    parser.add_argument('--all', '-a', action='store_true', help='Show all notes without filtering')
    parser.add_argument('--output', '-o', help='Output file path (default: stdout)')
    parser.add_argument('--format', '-f', choices=['json', 'text'], default='json', help='Output format')
    parser.add_argument('--stats', '-s', action='store_true', help='Show statistics only')

    args = parser.parse_args()

    try:
        # Load and parse
        html_content = load_flomo_export(args.path)
        notes = parse_flomo_html(html_content)

        if not notes:
            print("No notes found in the export.", file=sys.stderr)
            sys.exit(1)

        # Filter by tag if specified
        if args.tag and not args.all:
            notes = filter_notes_by_tag(notes, args.tag)
            if not notes:
                print(f"No notes found with tag #{args.tag}", file=sys.stderr)
                sys.exit(1)

        # Show stats
        if args.stats:
            all_tags = {}
            for note in notes:
                for tag in note.get('tags', []):
                    all_tags[tag] = all_tags.get(tag, 0) + 1

            print(f"Total notes: {len(notes)}")
            print(f"\nTags found:")
            for tag, count in sorted(all_tags.items(), key=lambda x: -x[1]):
                print(f"  #{tag}: {count}")
            return

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

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
