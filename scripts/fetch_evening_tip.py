import requests
import os
import base64
import random
import json
from datetime import datetime, timedelta

SENDKEY = os.environ.get("SENDKEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
STATE_FILE = "state_evening.json"

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "auto-topic-bot"
}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

TOPIC_CN = {
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

FUNC_MAP = [
    (["ai", "llm", "gpt", "chatgpt", "machine-learning", "deep-learning", "neural"], "人工智能/大模型相关工具"),
    (["cli", "command", "terminal", "shell"], "命令行工具，面向终端操作"),
    (["database", "sql", "nosql", "redis", "postgres", "mysql"], "数据库/存储相关工具"),
    (["python", "javascript", "typescript", "rust", "go", "java"], "编程语言/开发框架"),
    (["devops", "docker", "kubernetes", "ci", "cd", "deploy"], "DevOps/部署运维工具"),
    (["frontend", "react", "vue", "angular", "css", "html", "ui"], "前端/UI 开发工具"),
    (["backend", "api", "graphql", "rest", "server"], "后端/API 开发工具"),
    (["security", "encrypt", "auth", "privacy", "vpn"], "安全/隐私工具"),
    (["data", "analytics", "visualization", "chart", "dashboard"], "数据分析/可视化工具"),
    (["image", "photo", "video", "audio", "media"], "多媒体处理工具"),
    (["test", "testing", "qa", "quality"], "测试/质量保障工具"),
    (["editor", "ide", "vscode", "vim", "plugin"], "编辑器/IDE 扩展"),
    (["design", "figma", "ui", "ux", "prototype"], "设计工具"),
    (["doc", "documentation", "wiki", "knowledge"], "文档/知识管理工具"),
    (["mobile", "ios", "android", "flutter", "react-native", "swift"], "移动端开发工具"),
    (["game", "engine", "3d", "animation"], "游戏/3D 引擎"),
    (["blog", "cms", "static-site", "writing"], "博客/内容管理"),
    (["chat", "messaging", "bot", "slack", "discord"], "聊天/消息/机器人"),
    (["search", "index", "elastic", "algolia"], "搜索/索引工具"),
    (["monitor", "logging", "observability", "metrics"], "监控/可观测性"),
]

AUDIENCE_RULES = [
    (["python", "javascript", "typescript", "rust", "go", "java"], "程序员/开发者"),
    (["ai", "llm", "gpt", "machine-learning", "data", "deep-learning"], "AI 从业者/数据科学家"),
    (["frontend", "react", "vue", "css", "design", "ui"], "前端开发者/设计师"),
    (["devops", "docker", "kubernetes", "monitor", "deploy"], "运维/DevOps 工程师"),
    (["cli", "terminal", "shell", "editor", "vim"], "开发者/效率工具爱好者"),
    (["mobile", "ios", "android", "flutter"], "移动端开发者"),
    (["security", "vpn", "encrypt", "privacy"], "安全工程师/隐私关注者"),
    (["game", "3d", "animation", "engine"], "游戏开发者"),
    (["database", "sql", "data"], "数据工程师/分析师"),
    (["blog", "writing", "cms", "doc", "knowledge"], "写作者/内容创作者"),
    (["video", "audio", "image", "media"], "媒体创作者/设计师"),
    (["chinese", "cn", "zh"], "中文用户/国内开发者"),
]


def get_chinese_tags(topics):
    tags = []
    for t in topics[:3]:
        if t in TOPIC_CN:
            tags.append(TOPIC_CN[t])
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
    return {"featured": [], "last_date": ""}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def infer_function(description, topics, name):
    desc_lower = (description or "").lower()
    name_lower = name.lower()
    matched = []
    for keywords, func_desc in FUNC_MAP:
        for kw in keywords:
            if kw in desc_lower or kw in name_lower or any(kw in t for t in topics):
                matched.append(func_desc)
                break
    if matched:
        return "、".join(matched[:3])
    return "通用工具/框架"


def infer_audience(description, topics, name):
    desc_lower = (description or "").lower()
    name_lower = name.lower()
    matched = []
    for keywords, audience in AUDIENCE_RULES:
        for kw in keywords:
            if kw in desc_lower or kw in name_lower or any(kw in t for t in topics):
                matched.append(audience)
                break
    if matched:
        return "、".join(list(dict.fromkeys(matched))[:4])
    if any(t in ["chinese", "cn", "zh"] for t in topics):
        return "中文用户/普通用户"
    return "开发者/技术爱好者"


def fetch_readme(repo_full_name):
    try:
        url = f"https://api.github.com/repos/{repo_full_name}/readme"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            content = r.json().get("content", "")
            if content:
                decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
                lines = decoded.split("\n")
                meaningful = [l for l in lines if l.strip() and not l.startswith("#") and not l.startswith("!")]
                for line in meaningful:
                    clean = line.strip()
                    if clean and len(clean) > 30 and not clean.startswith("[!"):
                        return clean[:300]
                return ""
    except Exception:
        return ""
    return ""


def build_detailed_intro(repo, readme_snippet):
    stars_k = f"{repo['stars'] / 1000:.1f}K" if repo['stars'] >= 1000 else str(repo['stars'])
    lang = repo["lang"] or "多语言"
    desc = repo["description"] or ""
    topics = repo.get("topics", [])
    tags = get_chinese_tags(topics)
    func = infer_function(desc, topics, repo["name"])
    audience = infer_audience(desc, topics, repo["name"])

    lines = [f"星 {stars_k} · {lang}{(' · ' + tags) if tags else ''}"]
    if desc:
        lines.append(f"📄 {desc}")
    lines.append(f"🔧 功能分类：{func}")
    lines.append(f"👥 适合人群：{audience}")

    if readme_snippet:
        lines.append(f"📖 项目简介：{readme_snippet}")

    score_notes = []
    if repo["stars"] >= 5000:
        score_notes.append("超大爆款项目")
    elif repo["stars"] >= 1000:
        score_notes.append("热门项目")
    if any(t in ["chinese", "cn", "zh"] for t in topics):
        score_notes.append("有中文支持，对国内用户友好")
    if any(t in ["cli", "tool", "app"] for t in topics):
        score_notes.append("即装即用，门槛低")
    if any(t in ["ai", "llm", "gpt"] for t in topics):
        score_notes.append("AI 赛道，读者感兴趣")
    if score_notes:
        lines.append(f"💡 {'，'.join(score_notes)}")

    return "\n".join(lines)


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
    return unique[:15]


def pick_top5(repos, seed=None):
    if seed is not None:
        random.seed(seed)
    if len(repos) <= 5:
        return repos
    top = repos[:3]
    rest = repos[3:]
    random.shuffle(rest)
    top += rest[:2]
    return top


def score_project(repo):
    score = 0
    topics_str = " ".join(repo.get("topics", [])) + " " + (repo["description"] or "")
    if any(t in topics_str for t in ["ai", "llm", "gpt", "chat"]):
        score += 3
    if any(t in topics_str for t in ["chinese", "zh", "cn"]):
        score += 2
    if "tool" in topics_str or "cli" in topics_str:
        score += 1
    if repo["stars"] > 5000:
        score += 3
    elif repo["stars"] > 1000:
        score += 2
    else:
        score += 1
    if repo["description"] and len(repo["description"]) > 30:
        score += 1
    return score


def pick_best(repos):
    scored = [(score_project(r), r) for r in repos]
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def generate_writing_angle(repo):
    desc = (repo["description"] or "").lower()
    stars = repo["stars"]
    topics = repo.get("topics", [])

    if "ai" in desc or "llm" in desc or any(t in ["ai", "llm", "gpt"] for t in topics):
        return "AI 工具是流量密码。从'普通人怎么用 AI 省钱/赚钱'切入，先抛痛点再给方案。"
    if stars > 5000:
        return "万星项目有天然说服力。开头直接说'这个项目火了，但大多数人还不知道它能干啥'，制造信息差。"
    if any(t in ["chinese", "cn", "zh"] for t in topics):
        return "国产/中文项目读者有亲切感。从'国内开发者做了一个让全世界都在用的工具'切入。"
    if any(t in ["cli", "tool"] for t in topics):
        return "实用工具类文章最适合公众号。开头说'我找到一个神器，用了就回不去了'，重点写使用体验。"
    return "从'为什么这个项目能火'切入，先讲一个场景让读者觉得'对，我也有这个问题'，再介绍项目怎么解决。"


def build_message(repos):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"老贾，今天的详细选题来了（15:00）"

    lines = [f"## 老贾下午好！以下是今天 GitHub 热门项目的详细中文介绍\n"]
    lines.append(f"推送时间：{now}\n")

    for i, repo in enumerate(repos, 1):
        readme_snippet = fetch_readme(repo["name"])
        intro = build_detailed_intro(repo, readme_snippet)

        lines.append(f"---")
        lines.append(f"### {i}. {repo['name']}")
        lines.append(f"{intro}")
        lines.append(f"🔗 {repo['url']}")
        lines.append("")

    best = pick_best(repos)
    stars_best = f"{best['stars'] / 1000:.1f}K" if best['stars'] >= 1000 else str(best['stars'])
    angle = generate_writing_angle(best)
    tags_best = get_chinese_tags(best.get("topics", []))

    lines.append(f"---")
    lines.append(f"### 推荐你写这个：{best['name']}")
    lines.append(f"星 {stars_best} · {best['lang'] or '多语言'}{(' · ' + tags_best) if tags_best else ''}")
    lines.append(f"{best['description'] or ''}")
    lines.append("")
    lines.append(f"**写作角度：** {angle}")
    lines.append("")
    lines.append(f"🔗 {best['url']}")
    lines.append("")
    lines.append("---")
    lines.append("回复「写」我马上动笔，回复「换一个」重新推荐。")

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
    print(f"开始抓取 GitHub 热门项目，准备详细中文介绍 (日期: {today_str})...")

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

    seed = today_str.replace("-", "") + "1"
    picked = pick_top5(repos, seed=int(seed))

    state["featured"].extend([r["name"] for r in picked])
    state["featured"] = state["featured"][-30:]
    save_state(state)

    print(f"精选 5 个项目，开始获取 README...")
    title, content = build_message(picked)
    send_to_wechat(title, content)
    print("推送完成")


if __name__ == "__main__":
    main()
