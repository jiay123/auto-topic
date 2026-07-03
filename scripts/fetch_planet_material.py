import requests
import os
import json
from datetime import datetime

SENDKEY = os.environ.get("SENDKEY", "")
if not SENDKEY:
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")) as f:
            for line in f:
                if line.startswith("SENDKEY="):
                    SENDKEY = line.strip().split("=", 1)[1]
                    break
    except:
        pass

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "state_topics.json")


def load_morning_picks():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                state = json.load(f)
                return state.get("morning_picks", [])
    except:
        pass
    return []


FUNC_MAP = [
    (["ai", "llm", "gpt", "chatgpt", "machine-learning", "deep-learning"], "人工智能"),
    (["cli", "command", "terminal", "shell"], "命令行工具"),
    (["database", "sql", "nosql"], "数据库"),
    (["python", "javascript", "typescript", "rust", "go"], "编程语言"),
    (["devops", "docker", "kubernetes", "deploy"], "DevOps"),
    (["frontend", "react", "vue", "css", "ui"], "前端开发"),
    (["backend", "api", "graphql", "server"], "后端开发"),
    (["security", "encrypt", "auth", "privacy"], "安全工具"),
    (["data", "analytics", "visualization", "chart"], "数据分析"),
    (["image", "video", "audio", "media"], "多媒体"),
    (["test", "testing", "qa"], "测试工具"),
    (["editor", "ide", "vscode", "vim"], "编辑器"),
    (["design", "ui", "ux", "figma"], "设计工具"),
    (["doc", "documentation", "wiki"], "文档工具"),
    (["mobile", "ios", "android", "flutter"], "移动开发"),
    (["game", "3d", "animation"], "游戏开发"),
    (["blog", "cms", "writing"], "内容管理"),
    (["chat", "bot", "slack", "discord"], "聊天工具"),
    (["search", "index"], "搜索工具"),
    (["monitor", "logging", "observability"], "监控工具"),
]


CLASSICS = [
    "做技术的都知道，工具选对了，效率翻倍。但问题是：信息太多，谁有精力一个个试？",
    "开源社区每天冒出几百个项目，99% 活不过三个月。能留下来的，才是真东西。",
    "很多人问：不会编程能用这些工具吗？答案是：大部分可以。",
    "工具的价值不在功能多，而在解决一个具体问题。少即是多。",
    "今天推荐这个，不是因为星星多，而是因为它让我眼前一亮。",
    "AI 时代最稀缺的不是技术，是用技术解决问题的思路。",
    "一个工具好不好，看三点：解决什么问题、上手多快、社区活不活跃。",
    "我挑项目的标准很简单：要么省时间，要么省钱，要么省脑子。",
    "有些工具你一看就知道：这玩意儿会火。",
    "别被技术名词吓到，大部分开源工具装个包就能用。",
]


def infer_func(description, topics, name):
    desc_lower = (description or "").lower()
    name_lower = name.lower()
    matched = []
    for keywords, func_desc in FUNC_MAP:
        for kw in keywords:
            if kw in desc_lower or kw in name_lower or any(kw in t for t in topics):
                matched.append(func_desc)
                break
    if matched:
        return matched[0]
    return "效率工具"


def build_planet_content(repo):
    name = repo["name"]
    stars = repo["stars"]
    desc = repo.get("description") or "暂无简介"
    topics = repo.get("topics", [])
    lang = repo.get("lang") or "通用"
    url = repo["url"]
    func = infer_func(desc, topics, name)

    stars_str = f"{stars/1000:.1f}K" if stars >= 1000 else str(stars)
    opener = CLASSICS[hash(name) % len(CLASSICS)]

    content = f"""**{name}** ⭐{stars_str} · {lang}

{opener}

{name} 是一款 {func} 类开源项目。{desc}

🔗 {url}

#开源工具 #效率 #{func}"""

    return content.strip()


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
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"生成星球素材 ({today})...")

    picks = load_morning_picks()
    if not picks:
        print("无选题数据，跳过")
        send_to_wechat("星球素材生成失败", "今天没有选题数据，无法生成星球素材。")
        return

    repo = picks[0]
    print(f"选用项目: {repo['name']}")
    content = build_planet_content(repo)
    title = f"星球素材 · {repo['name']} · {today}"
    send_to_wechat(title, content)
    print("推送完成")


if __name__ == "__main__":
    main()
