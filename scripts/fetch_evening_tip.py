import requests
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

TOPIC_MAP = {
    "ai": "AI 工具", "machine-learning": "机器学习", "llm": "大语言模型",
    "python": "Python", "javascript": "JavaScript", "rust": "Rust",
    "cli": "命令行工具", "devops": "DevOps", "database": "数据库",
    "frontend": "前端", "backend": "后端", "mobile": "移动开发",
    "security": "安全", "design": "设计", "chinese": "中文项目",
}

def get_chinese_tags(topics):
    tags = []
    for t in topics[:3]:
        if t in TOPIC_MAP:
            tags.append(TOPIC_MAP[t])
    return "、".join(tags) if tags else ""

def generate_angle(repo):
    desc = (repo["description"] or "").lower()
    name = repo["name"]
    full = repo["full_name"]
    lang = repo["language"] or ""
    topics = repo.get("topics", [])
    tags = get_chinese_tags(topics)
    stars = repo["stars"]

    hooks = [
        f"这个项目有点意思。{name} 做到了一件以前只有大公司才做得到的事——而且它是开源的。你可以从'为什么作者要把它开源而不是卖钱'这个角度切入，读者天然就会好奇。",
        f"你有没有想过，{name} 为什么能火到 {stars} 颗星？不是因为它技术多牛，而是它解决了一个很多人在痛的问题。写这篇文章的时候，开头就直接抛那个痛点，读者会点头说'对，我就是这样'。",
        f"{name} 让我想起一个道理：最好的工具往往是那些让你感觉'这不难啊，我上我也行'的。文章就从这句话开头，先勾起读者的自信，再告诉他这背后的门道其实很深。",
        f"如果只用一个问题来介绍 {name}，我会问：{'如果你能免费做到以前要花几千块才能做的事' if stars > 1000 else '如果有一个工具能帮你省掉最烦的那一步，你愿不愿意试试？'} 文章就从这个问题开始。",
        f"这篇文章最适合的读者不是技术大牛，而是那些听说过 {tags or '这个领域'}、但一直没搞懂到底怎么回事的人。你把自己当初第一次看到这个项目时的困惑写出来，就是最好的开头。",
        f"写 {name} 的时候，别忘了提一句作者背景。很多读者其实不在乎代码怎么写，他们想知道的是'谁做的、为什么做、赚到钱了吗'。把人的故事放在技术前面。",
        f"这篇文章的结尾，我建议你问读者：{'当工具越来越免费，人的什么能力反而越来越值钱？' if 'ai' in desc or 'ai' in str(topics) else '你会在什么场景下用它？你最想用它解决什么问题？'} 好的结尾问题，评论数至少多一倍。",
    ]

    return random.choice(hooks)

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
                        "description": item["description"] or "",
                        "url": item["html_url"],
                        "lang": item["language"] or "",
                        "topics": item.get("topics", []),
                    })
        except Exception:
            pass

    seen = set()
    unique = []
    for r in repos:
        if r["name"] not in seen:
            seen.add(r["name"])
            unique.append(r)
    unique.sort(key=lambda x: x["stars"], reverse=True)
    return unique[:10]

def pick_best(repos):
    if not repos:
        return None
    scored = []
    for r in repos:
        score = 0
        topics_str = " ".join(r.get("topics", [])) + " " + (r["description"] or "")
        if any(t in topics_str for t in ["ai", "llm", "gpt", "chat"]):
            score += 3
        if any(t in topics_str for t in ["chinese", "zh", "cn"]):
            score += 2
        if "tool" in topics_str or "cli" in topics_str:
            score += 1
        if r["stars"] > 5000:
            score += 2
        elif r["stars"] > 1000:
            score += 1
        scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]

def build_message(repo):
    if not repo:
        title = "老贾，今晚写点什么？"
        content = """## 老贾，今天下午没有找到特别合适的选题

不过你还可以：
- 从早上推送的 5 个选题里选一个
- 或者想想最近有没有什么想写的工具
- 或者把之前写过的文章翻出来，写一篇续集/番外

有想法了直接回复我，随时开写。"""
        return title, content

    stars_k = f"{repo['stars'] / 1000:.1f}K" if repo['stars'] >= 1000 else str(repo['stars'])
    angle = generate_angle(repo)
    tags = get_chinese_tags(repo.get("topics", []))

    title = f"老贾，今晚写这个怎么样？"
    content = f"""## 老贾，下午好！给你挑了一个今晚可以写的项目

### {repo['name']}
⭐ {stars_k} · {repo['lang'] or '多语言'}{' · ' + tags if tags else ''}
{repo['description'] or ''}

### 写作切入点
{angle}

### 项目链接
{repo['url']}

---
想写这个？回复我「写」，我马上开始动笔。
不想写这个？回复我「换一个」，我重新推荐。"""
    return title, content

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
    print("开始抓取今晚写作素材...")
    repos = fetch_trending()
    if repos:
        print(f"抓到 {len(repos)} 个项目")
    else:
        print("没抓到项目，推送通用消息")

    best = pick_best(repos) if repos else None
    title, content = build_message(best)
    send_to_wechat(title, content)
    print("推送完成")

if __name__ == "__main__":
    main()
