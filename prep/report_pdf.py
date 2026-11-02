"""Build the Milestone 2 report PDF from its Markdown: uv run python -m prep.report_pdf.

reports/milestone2Report.md is the source; edit it, then run this to rebuild reports/milestone2Report.pdf.
The Markdown becomes HTML styled roughly like GitHub, and headless Chrome prints it to PDF.
If Chrome is not found, set CHROME to its path.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown
from markdown.extensions.toc import TocExtension

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports" / "milestone2Report.md"
TARGET = ROOT / "reports" / "milestone2Report.pdf"
CHROME_PATHS = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)
CHROME_COMMANDS = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome")
CSS = """
@page { size: Letter; margin: 13mm 13mm; }
body { font: 10pt/1.38 -apple-system, "Helvetica Neue", Arial, sans-serif; color: #1f2328; max-width: 100%; }
h1 { font-size: 18pt; line-height: 1.2; border-bottom: 1px solid #d0d7de; padding-bottom: 6px; }
h2 { font-size: 15pt; border-bottom: 1px solid #d0d7de; padding-bottom: 4px; margin-top: 16px; break-after: avoid; }
h3 { font-size: 12pt; break-after: avoid; }
table { border-collapse: collapse; font-size: 8.5pt; line-height: 1.35; margin: 8px 0; width: 100%; break-inside: auto; }
th, td { border: 1px solid #d0d7de; padding: 3px 5px; vertical-align: top; }
th { background: #f6f8fa; }
tr { break-inside: avoid; }
table:not(:has(tbody tr:nth-child(6))) { break-inside: avoid; }
p:has(+ table), p:has(+ img) { break-after: avoid; }
code, pre { font-family: Menlo, monospace; font-size: 8.5pt; }
pre { background: #f6f8fa; padding: 8px; border-radius: 4px; }
img { max-width: 100%; max-height: 170mm; display: block; margin: 0 auto; break-inside: avoid; }
blockquote { margin: 8px 0; padding: 4px 12px; border-left: 4px solid #d0d7de; color: #424a53; }
.footnote { font-size: 9pt; }
a { color: #0969da; text-decoration: none; }
"""


def github_slug(value, separator="-"):
    """Heading anchors as GitHub makes them, so #links work in both places."""
    value = re.sub(r"<[^>]+>", "", value).strip().lower()
    value = re.sub(r"[^\w\- ]", "", value)
    return value.replace(" ", separator)


def blank_line_before_lists(text):
    """GitHub starts a list right after a paragraph line; Python-Markdown needs a blank line first."""
    item = re.compile(r"^(?:[-*]|\d+\.) ")
    out = []
    for line in text.splitlines():
        previous = out[-1] if out else ""
        if item.match(line) and previous.strip() and not item.match(previous) and not previous.startswith(" "):
            out.append("")
        out.append(line)
    return "\n".join(out) + "\n"


def absolute_images(body, folder):
    """Point relative image paths at the files, since the page is written to a temporary folder.

    A <base> tag would do this too, but it also sends #section links to the folder instead of the page.
    """
    def resolve(match):
        src = match.group(1)
        if re.match(r"[a-z][a-z0-9+.-]*:", src):
            return match.group(0)
        return f'src="{(folder / src).resolve().as_uri()}"'

    return re.sub(r'src="([^"]+)"', resolve, body)


def to_html(text, folder):
    """A standalone page; folder is where the Markdown's relative image paths start from."""
    body = markdown.markdown(
        blank_line_before_lists(text),
        extensions=["tables", "footnotes", "fenced_code", "sane_lists", TocExtension(slugify=github_slug)],
    )
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        f"<title>Aurum Milestone 2 Report</title><style>{CSS}</style></head>"
        f"<body>{absolute_images(body, folder)}</body></html>"
    )


def find_chrome():
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    for path in CHROME_PATHS:
        if Path(path).exists():
            return path
    for command in CHROME_COMMANDS:
        if shutil.which(command):
            return shutil.which(command)
    sys.exit("Chrome was not found. Set CHROME to its path.")


def main():
    html = to_html(SOURCE.read_text(encoding="utf-8"), SOURCE.parent)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        page = Path(tmp) / "report.html"
        page.write_text(html, encoding="utf-8")
        # A throwaway profile keeps this run separate from a Chrome window that is already open.
        result = subprocess.run(
            [
                find_chrome(), "--headless=new", "--no-pdf-header-footer",
                f"--user-data-dir={Path(tmp) / 'chrome-profile'}", "--allow-file-access-from-files",
                f"--print-to-pdf={TARGET}", page.as_uri(),
            ],
            capture_output=True, encoding="utf-8", errors="replace",
        )
    # Chrome logs harmless warnings on success, so its output is shown only when it fails.
    if result.returncode != 0:
        sys.exit(f"Chrome could not print the PDF (exit {result.returncode}):\n{result.stderr}")
    print(TARGET)


if __name__ == "__main__":
    main()
