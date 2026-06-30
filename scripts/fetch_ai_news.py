import requests
import os
import xml.etree.ElementTree as ET
from datetime import datetime

SENDKEY = os.environ.get("SENDKEY", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

SOURCES = [
    {"name": "机器之心", "url": "https://www.jiqizhixin.com/rss", "type": "rss"},
    {"name": "量子位", "url": "https://www.qbitai.com/feed", "type": "rss"},
    {"name": "36氪快讯", "url": "https://36kr.com/api/newsflash?per_page=30", "type": "json"},
    {"name": "雷锋网AI", "url": "https://www.leiphone.com/feed/categoryRss/name/ai", "type": "rss"},
]


def parse_rss(xml_text):
    items = []
    try:
        root = ET.fromstring(xml_text)
        for item in root.findall(".//item"):
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            pubdate = item.findtext("pubDate", "")
            if title:
                items.append({"title": title, "url": link, "date": pubdate})
    except Exception as e:
        print(f"RSS 解析失败: {e}")
    return items


def parse_36kr_json(data):
    items = []
    try:
        if isinstance(data, dict) and "data" in data:
            news_list = data["data"].get("data", [])
            for n in news_list[:10]:
                title = n.get("title", "").strip()
                url = n.get("url", "")
                if not url:
                    url = f"https://36kr.com/p/{n.get('id', '')}"
                if title:
                    items.append({"title": title, "url": url, "date": n.get("published_at", "")})
    except Exception as e:
        print(f"36氪解析失败: {e}")
    return items


def fetch_news():
    all_items = []
    for source in SOURCES:
        try:
            r = requests.get(source["url"], headers=HEADERS, timeout=10)
            if r.status_code != 200:
                print(f"来源 {source['name']} HTTP {r.status_code}")
                continue

            if source["type"] == "rss":
                items = parse_rss(r.text)
            elif source["type"] == "json":
                items = parse_36kr_json(r.json())
            else:
                items = []

            if items:
                print(f"来源 {source['name']} 获取到 {len(items)} 条")
                all_items.extend(items)
        except Exception as e:
            print(f"来源 {source['name']} 失败: {e}")

    seen = set()
    unique = []
    for item in all_items:
        key = item["title"][:60]
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique[:8]


def build_message(news):
    now = datetime.now().strftime("%Y-%m-%d")
    title = f"老贾，今日 AI 新闻来了 ({now})"

    lines = [f"## 老贾早安！以下是今天的 AI 新闻\n"]
    for i, n in enumerate(news, 1):
        lines.append(f"{i}. {n['title']}")
        lines.append(f"   {n['url']}")
        lines.append("")

    lines.append("---")
    lines.append("想详细了解哪条？回复我编号。")
    return title, "\n".join(lines)


def send_to_wechat(title, content):
    if not SENDKEY:
        print("SENDKEY 未设定")
        return
    url = f"https://sctapi.ftqq.com/{SENDKEY}.send"
    data = {"title": title, "desp": content}
    try:
        r = requests.post(url, data=data, timeout=10)
        print("推送结果:", r.text[:100])
    except Exception as e:
        print("推送失败:", e)


def main():
    print("开始抓取中文 AI 新闻...")
    news = fetch_news()

    if not news:
        send_to_wechat("AI新闻抓取失败", "今天所有新闻源都无法访问，请稍后再试")
        return

    title, content = build_message(news)
    send_to_wechat(title, content)
    print(f"推送完成，共 {len(news)} 条")


if __name__ == "__main__":
    main()
