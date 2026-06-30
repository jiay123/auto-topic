import requests
import os
import json
from datetime import datetime, timedelta

SENDKEY = os.environ.get("SENDKEY", "")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

SOURCE = []

def fetch_hn():
    items = []
    try:
        r = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10)
        if r.status_code != 200:
            return items
        ids = r.json()[:50]
        ai_kw = ["ai", "llm", "gpt", "chatgpt", "machine learning", "deep learning",
                 "neural", "openai", "anthropic", "claude", "gemini", "mistral",
                 "llama", "artificial intelligence", "agent", "copilot"]
        for sid in ids:
            try:
                item = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=5).json()
                if not item or item.get("type") != "story":
                    continue
                title = (item.get("title") or "").lower()
                if any(kw in title for kw in ai_kw):
                    items.append({
                        "title": item["title"],
                        "url": item.get("url") or f"https://news.ycombinator.com/item?id={sid}",
                        "source": "Hacker News"
                    })
                    if len(items) >= 5:
                        break
            except:
                continue
    except Exception as e:
        print(f"HN 失败: {e}")
    return items


def fetch_devto():
    items = []
    try:
        r = requests.get("https://dev.to/api/articles?tag=ai&per_page=5", headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return items
        for article in r.json():
            items.append({
                "title": article["title"],
                "url": article["url"],
                "source": "Dev.to"
            })
    except Exception as e:
        print(f"Dev.to 失败: {e}")
    return items


def fetch_github_ai():
    items = []
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        url = f"https://api.github.com/search/repositories?q=ai+created:>={week_ago}&sort=stars&order=desc&per_page=5"
        r = requests.get(url, headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "auto-topic-bot"}, timeout=10)
        if r.status_code != 200:
            return items
        for repo in r.json().get("items", []):
            items.append({
                "title": f"[GitHub] {repo['full_name']} - {repo['description'] or '无描述'}",
                "url": repo["html_url"],
                "source": "GitHub"
            })
    except Exception as e:
        print(f"GitHub 失败: {e}")
    return items


def fetch_news():
    sources = [("Hacker News", fetch_hn), ("Dev.to", fetch_devto), ("GitHub AI", fetch_github_ai)]
    all_items = []
    for name, fetcher in sources:
        try:
            result = fetcher()
            if result:
                print(f"来源 {name} 获取到 {len(result)} 条")
                all_items.extend(result)
        except Exception as e:
            print(f"来源 {name} 异常: {e}")
    seen = set()
    unique = []
    for item in all_items:
        key = item["title"][:60]
        if key not in seen:
            seen.add(key)
            unique.append(item)
    if len(unique) > 8:
        unique = unique[:8]
    return unique


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
