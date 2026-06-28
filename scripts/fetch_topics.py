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
    "ai": "AI 工具",
    "machine-learning": "機器學習",
    "deep-learning": "深度學習",
    "llm": "大語言模型",
    "chatgpt": "ChatGPT",
    "gpt": "GPT",
    "nlp": "自然語言處理",
    "computer-vision": "電腦視覺",
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "rust": "Rust",
    "go": "Go",
    "react": "React",
    "vue": "Vue",
    "database": "資料庫",
    "cli": "命令列工具",
    "devops": "DevOps",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "testing": "測試工具",
    "security": "安全工具",
    "editor": "編輯器",
    "ide": "IDE",
    "vim": "Vim",
    "terminal": "終端機",
    "api": "API",
    "graphql": "GraphQL",
    "mobile": "行動開發",
    "ios": "iOS",
    "android": "Android",
    "frontend": "前端",
    "backend": "後端",
    "fullstack": "全端",
    "docs": "文件工具",
    "blog": "部落格",
    "cms": "內容管理",
    "game": "遊戲",
    "gui": "圖形介面",
    "svg": "SVG",
    "markdown": "Markdown",
    "data": "資料科學",
    "audio": "音訊",
    "video": "影片",
    "image": "圖片處理",
    "design": "設計",
    "css": "CSS",
    "linux": "Linux",
    "windows": "Windows",
    "macos": "macOS",
    "chrome": "Chrome 擴展",
    "vscode": "VS Code 擴展",
    "neovim": "Neovim",
    "arxiv": "學術論文",
    "cn": "中文專案",
    "chinese": "中文專案",
    "zh": "中文專案",
}

def get_chinese_tags(topics):
    tags = []
    for t in topics[:3]:
        if t in TOPIC_MAP:
            tags.append(TOPIC_MAP[t])
    return "、".join(tags) if tags else ""

def judge_project(repo):
    score = 0
    reasons = []
    stars = repo["stars"]
    topics = repo.get("topics", [])
    desc = (repo["description"] or "").lower()
    name = repo["name"].lower()

    if stars >= 10000:
        score += 3
        reasons.append(f"⭐{stars/1000:.0f}K 超高人氣")
    elif stars >= 5000:
        score += 2
        reasons.append(f"⭐{stars/1000:.0f}K 人氣高")
    elif stars >= 1000:
        score += 1
        reasons.append(f"⭐{stars/1000:.1f}K 值得關注")
    else:
        reasons.append(f"⭐{stars} 新專案")

    has_tools = any(t in topics or t in desc for t in ["cli", "tool", "devops", "docker", "api"])
    has_ai = any(t in topics or t in desc for t in ["ai", "llm", "gpt", "machine-learning", "deep-learning"])
    has_frontend = any(t in topics or t in desc for t in ["react", "vue", "frontend", "css", "ui"])
    has_chinese = any(t in topics for t in ["cn", "chinese", "zh"])
    has_chinese_name = any(c in name for c in ["zh", "cn", "chinese"])

    if has_ai:
        score += 2
        reasons.append("AI 熱門賽道")
    if has_tools:
        score += 1
        reasons.append("開發者實用工具")
    if has_chinese or has_chinese_name:
        score += 2
        reasons.append("有中文支援")

    if score >= 5:
        level = "🔥 非常適合寫文章"
    elif score >= 3:
        level = "👍 可以考慮"
    else:
        level = "👀 普通，看你有沒有興趣"

    return level, "、".join(reasons)

def summarize_repo(repo):
    desc = repo["description"] or ""
    topics = repo.get("topics", [])
    tags = get_chinese_tags(topics)

    if not desc and not tags:
        return "暫無詳細資訊"

    parts = []
    if tags:
        parts.append(f"分類：{tags}")
    if desc:
        parts.append(f"簡介：{desc}")
    return "。".join(parts)

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
                        "updated": item["updated_at"][:10],
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
    title = f"老賈，今天的 GitHub 選題來了"

    lines = [f"## 老賈早安！以下是你今天的 GitHub 選題\n"]
    for i, t in enumerate(topics, 1):
        stars_k = f"{t['stars'] / 1000:.1f}K" if t['stars'] >= 1000 else str(t['stars'])
        level, reason = judge_project(t)
        summary = summarize_repo(t)

        lines.append(f"### {i}. {t['name']}")
        lines.append(f"⭐ {stars_k}　{t['lang']}　更新於 {t['updated']}")
        lines.append(f"📝 {summary}")
        lines.append(f"🏷 {level}")
        lines.append(f"💡 {reason}")
        lines.append(f"🔗 {t['url']}")
        lines.append("")

    lines.append("---")
    lines.append("直接回覆我編號，我就開始寫文章！")
    lines.append("例如：回覆「3」代表選第三個專案。")
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
