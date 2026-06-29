import requests
import os
import xml.etree.ElementTree as ET
from datetime import datetime

SENDKEY = os.environ.get("SENDKEY", "")

SOURCES = [
    {
        "name": "36氪AI资讯",
        "url": "https://36kr.com/api/search/entity-search?page=1&per_page=8&keyword=AI&type=information",
        "parser": "36kr",
    },
    {
        "name": "百度新闻AI",
        "url": "https://news.baidu.com/ns?word=AI&tn=newsrss&cl=2&ct=1&rn=8",
        "parser": "rss",
    },
    {
        "name": "知乎AI热榜",
        "url": "https://www.zhihu.com/api/v4/search?q=AI&type=article&limit=8",
        "parser": "zhihu",
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def parse_36kr(data):
    items = []
    try:
        results = data.get("data", {}).get("items", [])
        for r in results[:8]:
            title = r.get("title", "").strip()
            url = "https://36kr.com/p/" + str(r.get("id", ""))
            if title:
                items.append({"title": title, "url": url})
    except:
        pass
    return items

def parse_rss(xml_text):
    items = []
    try:
        root = ET.fromstring(xml_text)
        for item in root.findall(".//item")[:8]:
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            if title:
                items.append({"title": title, "url": link})
    except:
        pass
    return items

def parse_zhihu(data):
    items = []
    try:
        results = data
        if isinstance(results, dict):
            results = data.get("data", [])
        for r in results[:8]:
            title = r.get("title", "").strip()
            url = r.get("url", "")
            if not url and "id" in r:
                url = f"https://zhuanlan.zhihu.com/p/{r['id']}"
            if title:
                items.append({"title": title, "url": url})
    except:
        pass
    return items

def fetch_news():
    for source in SOURCES:
        try:
            r = requests.get(source["url"], headers=HEADERS, timeout=10)
            if r.status_code != 200:
                continue

            parser = source["parser"]
            if parser == "36kr":
                items = parse_36kr(r.json())
            elif parser == "rss":
                items = parse_rss(r.text)
            elif parser == "zhihu":
                items = parse_zhihu(r.json())
            else:
                items = []

            if items:
                print(f"来源 {source['name']} 获取到 {len(items)} 条")
                return items

        except Exception as e:
            print(f"来源 {source['name']} 失败: {e}")
            continue

    return []

def build_message(news):
    now = datetime.now().strftime("%Y-%m-%d")
    title = f"老贾，今日AI新闻来了 ({now})"

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
    print("开始抓取 AI 新闻...")
    news = fetch_news()

    if not news:
        send_to_wechat("AI新闻抓取失败", "今天所有新闻源都无法访问，请稍后再试")
        return

    title, content = build_message(news)
    send_to_wechat(title, content)
    print(f"推送完成，共 {len(news)} 条")

if __name__ == "__main__":
    main()
