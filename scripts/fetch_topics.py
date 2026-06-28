import requests
import json
import os
import random
from datetime import datetime

SENDKEY = os.environ.get("SENDKEY", "")

CATEGORIES = [
    {"q": "stars:>1000 pushed:>2026-01-01", "sort": "stars", "order": "desc"},
    {"q": "stars:>500 pushed:>2026-03-01 topic:ai", "sort": "stars", "order": "desc"},
    {"q": "stars:>300 pushed:>2026-04-01 topic:developer-tools", "sort": "stars", "order": "desc"},
    {"q": "stars:>200 pushed:>2026-05-01", "sort": "stars", "order": "desc"},
    {"q": "stars:>100 pushed:>2026-06-01", "sort": "stars", "order": "desc"},
]

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "auto-topic-bot"
}

def fetch_trending():
    repos = []
    for cat in CATEGORIES:
        try:
            url = f"https://api.github.com/search/repositories?q={cat['q']}&sort={cat['sort']}&order={cat['order']}&per_page=5"
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                items = r.json().get("items", [])
                for item in items:
                    repos.append({
                        "name": item["full_name"],
                        "stars": item["stargazers_count"],
                        "description": item["description"] or "无描述",
                        "url": item["html_url"],
                        "lang": item["language"] or "未知",
                        "topics": item.get("topics", []),
                        "created": item["created_at"][:10],
                    })
        except Exception as e:
            pass

    seen = set()
    unique = []
    for r in repos:
        if r["name"] not in seen:
            seen.add(r["name"])
            unique.append(r)
    unique.sort(key=lambda x: x["stars"], reverse=True)
    return unique[:15]

def pick_top5(repos):
    if len(repos) <= 5:
        return repos
    top = repos[:3]
    rest = repos[3:]
    random.shuffle(rest)
    top += rest[:2]
    return top

def build_message(topics):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"今日選題推薦 {now}"

    lines = [f"# 老賈，以下是今天的 GitHub 選題\n"]
    for i, t in enumerate(topics, 1):
        stars_k = f"{t['stars'] / 1000:.1f}K" if t['stars'] >= 1000 else str(t['stars'])
        lines.append(f"## {i}. {t['name']}")
        lines.append(f"- ⭐ {stars_k} · {t['lang']}")
        lines.append(f"- {t['description']}")
        lines.append(f"- 鏈接：{t['url']}")
        if t["topics"]:
            lines.append(f"- 標籤：{' '.join(t['topics'][:5])}")
        lines.append("")

    lines.append("\n---\n回覆我選擇的編號，我就開始寫文章！")
    return title, "\n".join(lines)

def send_to_wechat(title, content):
    if not SENDKEY:
        print("SENDKEY 未設定，無法推送")
        return
    url = f"https://sctapi.ftqq.com/{SENDKEY}.send"
    data = {"title": title, "desp": content}
    try:
        r = requests.post(url, data=data, timeout=10)
        print("推送結果:", r.text)
    except Exception as e:
        print("推送失敗:", e)

def main():
    print("開始抓取 GitHub 熱門專案...")
    repos = fetch_trending()
    print(f"抓取到 {len(repos)} 個專案")

    if not repos:
        send_to_wechat("選題抓取失敗", "今天 GitHub API 沒有返回數據，請稍後再試")
        return

    picked = pick_top5(repos)
    title, content = build_message(picked)
    send_to_wechat(title, content)
    print("推送完成")

if __name__ == "__main__":
    main()
