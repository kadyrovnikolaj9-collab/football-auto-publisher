import json
import os
import re
import sys
import time

import xml.etree.ElementTree as ET
from email.utils import format_datetime
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import feedparser
import requests

FEED_URL = "https://news.google.com/rss/search?q=" + quote(
    "футбол OR РПЛ OR Лига чемпионов", safe=""
) + "&hl=ru&gl=RU&ceid=RU:ru"
STATE_PATH = Path("posted_links.json")
MAX_POSTS_PER_RUN = 3
VK_API_VERSION = "5.199"


def load_state():
    if not STATE_PATH.exists():
        return {"posted": []}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"posted": []}


def clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def make_post(entry):
    title = clean_text(entry.get("title", "Новости футбола"))
    link = clean_text(entry.get("link", ""))
    source = ""
    if entry.get("source"):
        source = clean_text(entry["source"].get("title", ""))
    if not source:
        source = "Источник: Google News"
    return f"⚽ {title}\n\n📰 {source}\n🔗 {link}"


def publish_to_vk(message):
    token = os.environ.get("VK_ACCESS_TOKEN", "").strip()
    group_id = os.environ.get("VK_GROUP_ID", "").strip()
    if not token or not group_id:
        print("VK_ACCESS_TOKEN or VK_GROUP_ID is missing; running in preview mode.")
        print(message)
        return False

    try:
        numeric_group_id = int(group_id)
    except ValueError:
        raise RuntimeError("VK_GROUP_ID must contain only the numeric community ID.")

    response = requests.post(
        "https://api.vk.com/method/wall.post",
        data={
            "access_token": token,
            "owner_id": -abs(numeric_group_id),
            "from_group": 1,
            "message": message,
            "v": VK_API_VERSION,
        },
        timeout=25,
    )
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        error = payload["error"]
        raise RuntimeError(
            f"VK API error {error.get('error_code')}: {error.get('error_msg')}"
        )
    return True


def write_public_rss(entries):
    """Write a small RSS feed file for VK's RSS importer."""
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Футбол без фильтра"
    ET.SubElement(channel, "link").text = "https://github.com/kadyrovnikolaj9-collab/football-auto-publisher"
    ET.SubElement(channel, "description").text = "Автоматическая лента футбольных новостей"
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(datetime.now(timezone.utc))
    for entry in entries[:20]:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = clean_text(entry.get("title", "Новости футбола"))
        ET.SubElement(item, "link").text = clean_text(entry.get("link", ""))
        ET.SubElement(item, "guid", isPermaLink="true").text = clean_text(entry.get("link", ""))
        ET.SubElement(item, "description").text = clean_text(entry.get("summary", entry.get("title", "")))
        published = entry.get("published_parsed")
        if published:
            try:
                from calendar import timegm
                dt = datetime.fromtimestamp(timegm(published), timezone.utc)
                ET.SubElement(item, "pubDate").text = format_datetime(dt)
            except (OverflowError, ValueError, TypeError):
                pass
    ET.ElementTree(rss).write("feed.xml", encoding="utf-8", xml_declaration=True)
    print(f"Wrote public RSS feed with {min(len(entries), 20)} items.")


def main():
    state = load_state()
    posted = set(state.get("posted", []))
    feed = feedparser.parse(FEED_URL)
    if feed.bozo and not feed.entries:
        raise RuntimeError(f"Could not read RSS feed: {feed.bozo_exception}")
    write_public_rss(feed.entries)

    new_entries = []
    for entry in feed.entries:
        link = clean_text(entry.get("link", ""))
        title = clean_text(entry.get("title", ""))
        if not link or not title or link in posted:
            continue
        new_entries.append(entry)
        if len(new_entries) >= MAX_POSTS_PER_RUN:
            break

    if not new_entries:
        print("No new football headlines.")
        return

    successful_links = []
    for entry in reversed(new_entries):
        message = make_post(entry)
        published = publish_to_vk(message)
        # In preview mode, don't mark as posted, so a real run can publish later.
        if published:
            successful_links.append(clean_text(entry.get("link", "")))
        time.sleep(1)

    if successful_links:
        state["posted"] = (state.get("posted", []) + successful_links)[-500:]
        STATE_PATH.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Published {len(successful_links)} post(s).")
    else:
        print("Preview finished. Configure VK secrets to enable publishing.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
