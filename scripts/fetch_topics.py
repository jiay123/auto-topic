import requests
import os
import random
import json
from datetime import datetime, timedelta

SENDKEY = os.environ.get("SENDKEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
STATE_FILE = "state_topics.json"

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "auto-topic-bot"
}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

TOPIC_MAP = {
    "ai": "AI 工具", "machine-learning": "机器学习", "deep-learning": "深度学习",
    "llm": "大语言模型", "chatgpt": "ChatGPT", "gpt": "GPT",
    "nlp": "自然语言处理", "computer-vision": "计算机视觉",
    "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
    "rust": "Rust", "go": "Go", "react": "React", "vue": "Vue",
    "database": "数据库", "cli": "命令行工具", "devops": "DevOps",
    "docker": "Docker", "kubernetes": "K8s", "testing": "测试工具",
    "security": "安全工具", "editor": "编辑器", "api": "API",
    "frontend": "前端", "backend": "后端", "mobile": "移动开发",
    "ios": "iOS", "android": "Android", "game": "游戏开发",
    "gui": "图形界面", "markdown": "Markdown", "data": "数据科学",
    "audio": "音频", "video": "视频", "image": "图像处理",
    "design": "设计工具", "css": "CSS", "linux": "Linux",
    "windows": "Windows", "chrome": "Chrome 扩展", "vscode": "VS Code 扩展",
    "neovim": "Neovim", "cn": "中文项目", "chinese": "中文项目",
    "zh": "中文项目", "blog": "博客", "docs": "文档工具",
    "cms": "内容管理", "svg": "SVG", "terminal": "终端",
    "macos": "macOS", "vim": "Vim", "ide": "IDE",
}

def get_chinese_tags(topics):
    tags = []
    for t in topics[:3]:
        if t in TOPIC_MAP:
            tags.append(TOPIC_MAP[t])
    return "、".join(tags) if tags else ""


def get_dynamic_categories():
    today = datetime.now()
    week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    return [
        {"q": f"stars:>1000 pushed:>={week_ago}", "sort": "stars", "order": "desc"},
        {"q": f"stars:>500 pushed:>={week_ago} topic:ai", "sort": "stars", "order": "desc"},
        {"q": f"stars:>300 pushed:>={week_ago} topic:developer-tools", "sort": "stars", "order": "desc"},
        {"q": f"stars:>200 pushed:>={week_ago}", "sort": "stars", "order": "desc"},
        {"q": f"stars:>100 created:>={month_ago}", "sort": "stars", "order": "desc"},
    ]


def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                return json.load(f)
    except:
        pass
    return {"featured": [], "last_date": "", "morning_picks": []}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def fetch_trending(exclude_names=None):
    if exclude_names is None:
        exclude_names = set()
    cats = get_dynamic_categories()
    repos = []
    for cat in cats:
        try:
            url = f"https://api.github.com/search/repositories?q={cat['q']}&sort={cat['sort']}&order={cat['order']}&per_page=5"
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                items = r.json().get("items", [])
                for item in items:
                    name = item["full_name"]
                    if name in exclude_names:
                        continue
                    repos.append({
                        "name": name,
                        "stars": item["stargazers_count"],
                        "description": item["description"] or "无描述",
                        "url": item["html_url"],
                        "lang": item["language"] or "未知",
                        "topics": item.get("topics", []),
                        "created": item["created_at"][:10],
                        "updated": item["updated_at"][:10],
                    })
        except Exception as e:
            print(f"搜索失败: {e}")

    seen = set()
    unique = []
    for r in repos:
        if r["name"] not in seen:
            seen.add(r["name"])
            unique.append(r)
    unique.sort(key=lambda x: x["stars"], reverse=True)
    return unique[:15]


def pick_top6(repos, seed=None):
    if seed is not None:
        random.seed(seed)
    if len(repos) <= 6:
        return repos
    top = repos[:4]
    rest = repos[4:]
    random.shuffle(rest)
    top += rest[:2]
    return top


def judge_project(repo):
    score = 0
    reasons = []
    stars = repo["stars"]
    topics = repo.get("topics", [])
    desc = (repo["description"] or "").lower()
    name = repo["name"].lower()

    if stars >= 10000:
        score += 3
        reasons.append(f"星 {stars/1000:.0f}K 超高人气")
    elif stars >= 5000:
        score += 2
        reasons.append(f"星 {stars/1000:.0f}K 人气高")
    elif stars >= 1000:
        score += 1
        reasons.append(f"星 {stars/1000:.1f}K 值得关注")
    else:
        reasons.append(f"星 {stars} 新项目")

    has_ai = any(t in topics or t in desc for t in ["ai", "llm", "gpt", "machine-learning", "deep-learning"])
    has_tools = any(t in topics or t in desc for t in ["cli", "tool", "devops", "docker", "api"])
    has_chinese = any(t in topics for t in ["cn", "chinese", "zh"])
    has_chinese_name = any(c in name for c in ["zh", "cn", "chinese"])

    if has_ai:
        score += 2
        reasons.append("AI 热门赛道")
    if has_tools:
        score += 1
        reasons.append("开发者实用工具")
    if has_chinese or has_chinese_name:
        score += 2
        reasons.append("有中文支持")

    if score >= 5:
        level = "非常适合写文章"
    elif score >= 3:
        level = "可以考虑"
    else:
        level = "普通，看你有没兴趣"

    return level, "、".join(reasons)


def summarize_repo(repo):
    desc = repo["description"] or ""
    topics = repo.get("topics", [])
    tags = get_chinese_tags(topics)

    if not desc and not tags:
        return "暂无详细信息"

    parts = []
    if tags:
        parts.append(f"分类：{tags}")
    if desc:
        parts.append(f"简介：{desc}")
    return "。".join(parts)


def build_message(topics):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"老贾，今天的 GitHub 选题来了"

    lines = [f"## 老贾早安！以下是你今天的 GitHub 选题\n"]
    for i, t in enumerate(topics, 1):
        stars_k = f"{t['stars'] / 1000:.1f}K" if t['stars'] >= 1000 else str(t['stars'])
        level, reason = judge_project(t)
        summary = summarize_repo(t)

        lines.append(f"### {i}. {t['name']}")
        lines.append(f"星 {stars_k}　{t['lang']}　更新于 {t['updated']}")
        lines.append(f"📝 {summary}")
        lines.append(f"🏷 {level}")
        lines.append(f"💡 {reason}")
        lines.append(f"🔗 {t['url']}")
        lines.append("")

    lines.append("---")
    lines.append("直接回复我编号，我就开始写文章！")
    lines.append("例如：回复「3」代表选第三个项目。")
    return title, "\n".join(lines)


def send_to_wechat(title, content):
    if not SENDKEY:
        print("SENDKEY 未设定，无法推送")
        return
    url = f"https://sctapi.ftqq.com/{SENDKEY}.send"
    data = {"title": title, "desp": content}
    try:
        r = requests.post(url, data=data, timeout=10)
        print("推送结果:", r.text[:200])
    except Exception as e:
        print("推送失败:", e)


def main():
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"开始抓取 GitHub 热门项目 (日期: {today_str})...")

    state = load_state()
    if state.get("last_date") != today_str:
        state["featured"] = []
        state["last_date"] = today_str

    exclude_names = set(state.get("featured", []))
    repos = fetch_trending(exclude_names)
    print(f"抓取到 {len(repos)} 个项目")

    if not repos:
        send_to_wechat("选题抓取失败", "今天 GitHub API 没有返回数据，请稍后再试")
        return

    seed = today_str.replace("-", "")
    picked = pick_top6(repos, seed=int(seed))

    state["featured"].extend([r["name"] for r in picked])
    state["featured"] = state["featured"][-30:]
    state["morning_picks"] = picked
    save_state(state)

    title, content = build_message(picked)
    send_to_wechat(title, content)
    print("推送完成")


if __name__ == "__main__":
    main()
