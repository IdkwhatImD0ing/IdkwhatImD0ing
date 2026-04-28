import argparse
import html
import re
import textwrap
import urllib.request
import xml.etree.ElementTree as ET

from readme_blocks import replace_block


DEFAULT_RSS_URL = "https://www.thehackathonplaybook.dev/blog/rss.xml"
START = "<!-- PLAYBOOK_POSTS:START -->"
END = "<!-- PLAYBOOK_POSTS:END -->"


def fetch_rss(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "github-profile-readme-updater"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def clean_text(value: str, max_length: int = 190) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_length:
        return text
    return textwrap.shorten(text, width=max_length, placeholder="...")


def parse_posts(feed_xml: bytes, limit: int) -> tuple[str, str, list[dict[str, str]]]:
    root = ET.fromstring(feed_xml)
    channel = root.find("channel")
    if channel is None:
        raise ValueError("RSS feed is missing a channel element")

    feed_title = clean_text(channel.findtext("title", "Hackathon Playbook Blog"))
    feed_description = clean_text(
        channel.findtext("description", "Hackathon guides, strategies, and tips.")
    )

    posts = []
    for item in channel.findall("item")[:limit]:
        posts.append(
            {
                "title": clean_text(item.findtext("title", "Untitled"), max_length=120),
                "link": clean_text(item.findtext("link", ""), max_length=300),
                "description": clean_text(item.findtext("description", "")),
            }
        )

    if not posts:
        raise ValueError("RSS feed did not contain any posts")

    return feed_title, feed_description, posts


def render(feed_title: str, feed_description: str, posts: list[dict[str, str]]) -> str:
    lines = [f"**{feed_title}** - {feed_description}", ""]
    for post in posts:
        lines.append(f"- **[{post['title']}]({post['link']})** - {post['description']}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--rss-url", default=DEFAULT_RSS_URL)
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()

    feed_xml = fetch_rss(args.rss_url)
    feed_title, feed_description, posts = parse_posts(feed_xml, args.limit)
    changed = replace_block(args.readme, START, END, render(feed_title, feed_description, posts))
    print("Updated playbook posts block" if changed else "Playbook posts block already current")


if __name__ == "__main__":
    main()
