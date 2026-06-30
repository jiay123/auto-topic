import requests
import os
import base64
import json
from datetime import datetime

SENDKEY = os.environ.get("SENDKEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
MORNING_STATE_FILE = "state_topics.json"

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "auto-topic-bot"
}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

FUNC_MAP = [
    (["ai", "llm", "gpt", "chatgpt", "machine-learning", "deep-learning", "neural"], "人工智能/大模型相关工具"),
    (["cli", "command", "terminal", "shell"], "命令行工具"),
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


def load_morning_state():
    try:
        if os.path.exists(MORNING_STATE_FILE):
            with open(MORNING_STATE_FILE) as f:
                state = json.load(f)
                return state.get("morning_picks", [])
    except:
        pass
    return []


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
    except Exception:
        pass
    return ""


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
    return "开发者/技术爱好者"


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


def why_good_for_wechat(repo):
    reasons = []
    desc = (repo["description"] or "").lower()
    topics = repo.get("topics", [])
    stars = repo["stars"]

    if any(t in ["ai", "llm", "gpt", "chat"] for t in topics) or "ai" in desc:
        reasons.append("AI 话题自带流量，你的读者对这个最感兴趣")
    if any(t in ["chinese", "cn", "zh"] for t in topics):
        reasons.append("有中文支持，国内读者上手门槛低，文章实用性强")
    if stars > 5000:
        reasons.append("万星项目已有口碑，写它读者会觉得'这个东西很靠谱'")
    if any(t in ["cli", "tool", "app"] for t in topics):
        reasons.append("工具类文章好写、好读、好转发，是最适合公众号的品类")
    if any(t in ["python", "javascript", "typescript"] for t in topics):
        reasons.append("主流语言工具，覆盖面广，读者基数大")

    if not reasons:
        reasons.append("开源项目，有新鲜感，适合做'发现新工具'系列")

    return "、".join(reasons[:3])


def build_message(project1, project2):
    title = "老贾，今天精选2个适合写公众号的开源项目"

    lines = [f"## 老贾下午好！从今天6个选题里挑了2个最适合写公众号的\n"]

    for idx, repo in enumerate([project1, project2], 1):
        stars_k = f"{repo['stars'] / 1000:.1f}K" if repo['stars'] >= 1000 else str(repo['stars'])
        readme_snippet = fetch_readme(repo["name"])
        desc = repo["description"] or "暂无简介"
        func = infer_function(desc, repo.get("topics", []), repo["name"])
        audience = infer_audience(desc, repo.get("topics", []), repo["name"])
        angle = generate_writing_angle(repo)
        reason = why_good_for_wechat(repo)

        lines.append(f"---")
        lines.append(f"### 项目{idx}. {repo['name']}")
        lines.append(f"星 {stars_k} · {repo['lang'] or '多语言'}")
        lines.append(f"")
        lines.append(f"**功能：** {func}")
        if readme_snippet:
            lines.append(f"{readme_snippet}")
        lines.append(f"")
        lines.append(f"**适合人群：** {audience}")
        lines.append(f"")
        lines.append(f"**推荐理由：** {reason}")
        lines.append(f"")
        lines.append(f"**写作角度：** {angle}")
        lines.append(f"")
        lines.append(f"🔗 {repo['url']}")
        lines.append("")

    lines.append("---")
    lines.append("回复「写1」或「写2」我马上动笔。")
    lines.append("如果这两个都不想写，回复「换」我从剩下4个里再挑。")

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
    print(f"读取早上推送结果 (日期: {today_str})...")

    morning_picks = load_morning_state()

    if not morning_picks or len(morning_picks) < 2:
        print(f"未找到早上推送数据（{len(morning_picks) if morning_picks else 0} 条），跳过推送")
        send_to_wechat("下午选题推送失败", "今天早上没有选题数据，无法精选。请手动选一个项目告诉我。")
        return

    scored = [(score_project(r), r) for r in morning_picks]
    scored.sort(key=lambda x: x[0], reverse=True)

    project1 = scored[0][1]
    project2 = scored[1][1]

    print(f"精选 2 个项目：{project1['name']}、{project2['name']}")
    title, content = build_message(project1, project2)
    send_to_wechat(title, content)
    print("推送完成")


if __name__ == "__main__":
    main()
