"""
08:00 GitHub 项目推荐 + 智能选文

每天推送 5 个项目：
  · 2 个：本周 GitHub 最热门（前10名里每天轮2个，不重复，5天轮完）
  · 3 个：根据老贾历史数据，最适合写的开源项目
末尾单独推荐 1 个最适合写文章的项目，用中文说清为什么。

所有文案全中文，项目简介用大白话讲清“是什么、能干啥、适合谁”，不出现英文原句。
"""
import requests
import os
import json
import random
import time
import sys
from datetime import datetime, timedelta

today = datetime.now()
# 本周一（用于热门榜按周轮转）
WEEK_MONDAY = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
DATE_7D = (today - timedelta(days=7)).strftime("%Y-%m-%d")
DATE_3D = (today - timedelta(days=3)).strftime("%Y-%m-%d")

SENDKEY = os.environ.get("SENDKEY", "")
GH_TOKEN = os.environ.get("GH_TOKEN", "")
BASE = os.path.join(os.path.dirname(__file__), "..")
STATE_FILE = os.path.join(BASE, "state_github.json")
HISTORY_FILE = os.path.join(BASE, "recommended_history.json")
HOT_FILE = os.path.join(BASE, "hot_rotation.json")
ARTICLE_DATA = os.path.join(BASE, "article_data.json")

HEADERS = {"Accept": "application/vnd.github.v3+json", "User-Agent": "auto-topic-bot"}
if GH_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GH_TOKEN}"

# 老贾爆款规律（来自历史文章 + 涨粉数据分析），用于给“数据相关”项目打分
# 权重依据「单篇涨粉」硬指标（2026-07-12 更新）：求职上岸103、大厂干货83、搞钱80/61、省钱34
PATTERNS = {
    "求职上岸": {"keywords": ["job", "jobs", "career", "resume", "cv", "interview", "hire", "hiring", "求职", "找工作", "简历", "面试", "上岸"], "score": 7, "reason": "求职/上岸类涨粉最猛（单篇+103），读者最愿意关注"},
    "省钱免费": {"keywords": ["free", "替代", "alternative", "省钱", "免费", "省", "open-source"], "score": 6, "reason": "省钱/免费类转发率11-21%、涨粉稳（+34），非常稳"},
    "搞钱变现": {"keywords": ["money", "印钞", "赚钱", "搞钱", "副业", "monetize", "revenue", "earn", "profit", "变现", "side-project"], "score": 6, "reason": "搞钱/变现类涨粉高（+80/+61），最高播放15611"},
    "大厂干货": {"keywords": ["google", "microsoft", "apple", "openai", "meta", "nvidia", "deepseek", "gemini", "claude", "anthropic"], "score": 5, "reason": "大厂/内行干货涨粉高（CLAUDE.md +83），最高播放8830"},
    "情绪爆点": {"keywords": ["慌", "被开除", "裁员", "太狠", "疯传"], "score": 3, "reason": "情绪词标题，转发率14-17%"},
    "AI相关": {"keywords": ["ai", "llm", "gpt", "chatgpt", "machine-learning", "ollama", "openai", "claude", "gemini", "langchain", "rag", "agent"], "score": 3, "reason": "AI类流量有保障，稳定1000+"},
    "直接能用": {"keywords": ["web", "online", "saas", "app", "gui", "browser", "extension"], "score": 2, "reason": "在线可用不用安装，读者门槛低"},
    "中文友好": {"keywords": ["chinese", "cn", "zh", "中文"], "score": 2, "reason": "支持中文，读者上手快"},
    "纯技术资讯": {"keywords": ["driver", "kernel", "compiler", "benchmark", "3d-engine", "physics"], "score": -6, "reason": "纯技术/硬件资讯涨粉≈0，别写"},
    "安装复杂": {"keywords": ["kubernetes", "helm", "terraform"], "score": -5, "reason": "安装复杂劝退读者"},
}

# 中文卡片规则库：按顺序匹配，命中第一条就用。每条给出“大白话标题 + 3条中文要点”
CN_CARDS = [
    {"keys": ["selfhosted", "self-host", "self hosted"], "title": "可以自己搭建的免费软件大合集",
     "points": ["是什么：收集几百个能装在你自己服务器上的开源软件", "能省啥：网盘、笔记、密码管理器都有，不用买会员", "适合谁：想摆脱付费订阅、数据自己掌控的人"]},
    {"keys": ["note", "notes", "notion", "obsidian", "markdown"], "title": "开源笔记 / 写作工具",
     "points": ["是什么：帮你记笔记、写文档、整理知识的工具", "能干啥：本地保存、双向链接、还能导出分享", "适合谁：学生、写作者、不想数据被大厂拿走的人"]},
    {"keys": ["pdf"], "title": "开源 PDF 处理工具箱",
     "points": ["是什么：合并、拆分、压缩、转换 PDF 的免费工具", "能干啥：不用开会员就能处理各种 PDF", "适合谁：经常和 PDF 打交道、想省会员费的人"]},
    {"keys": ["ocr", "recogni", "文字识别"], "title": "开源文字识别（OCR）工具",
     "points": ["是什么：把图片里的文字提取出来的免费工具", "能干啥：截图、扫描件一键变可编辑文字", "适合谁：经常要从图片搬文字、不想手抄的人"]},
    {"keys": ["translat", "翻译"], "title": "开源翻译工具",
     "points": ["是什么：自己部署的翻译工具，不依赖付费接口", "能干啥：文档、网页、对话都能翻", "适合谁：想免费搞定多语言、保护隐私的人"]},
    {"keys": ["agent", "automat", "workflow", "自动化"], "title": "会自己干活的 AI 智能体 / 自动化工具",
     "points": ["是什么：按你的指令自动跑流程、调工具的助手", "能干啥：自动填表、爬数据、发消息，省下重复劳动", "适合谁：想用 AI 提效、从重复活里解脱的人"]},
    {"keys": ["chatbot", "chat", "llm", "gpt", "chatgpt", "大模型", "大语言模型"], "title": "能聊天的 AI 助手",
     "points": ["是什么：自己部署的 AI 对话工具，数据在你手里", "能干啥：问答、写稿、总结，不用给大厂交钱", "适合谁：想用 AI 又怕隐私泄露、想省钱的人"]},
    {"keys": ["image", "photo", "图片", "绘画", "diffusion", "stable diffusion", "midjourney"], "title": "开源图片 / AI 绘画工具",
     "points": ["是什么：生成或处理图片的免费工具", "能干啥：文生图、改图、抠图，省掉付费软件", "适合谁：做图、做封面、玩 AI 绘画的人"]},
    {"keys": ["video", "视频"], "title": "开源视频处理工具",
     "points": ["是什么：剪辑、压制、下载、处理视频的免费工具", "能干啥：不用开剪映会员也能剪视频", "适合谁：做短视频、想省软件费的人"]},
    {"keys": ["audio", "music", "音乐", "播客", "podcast", "tts", "语音"], "title": "开源音频 / 音乐工具",
     "points": ["是什么：播放、剪辑、生成音频的免费工具", "能干啥：配音、转字幕、做播客都行", "适合谁：做音频内容、想省工具费的人"]},
    {"keys": ["download", "下载", "youtube", "bilibili"], "title": "开源下载工具",
     "points": ["是什么：从各平台下载视频、音频、文件的工具", "能干啥：一键保存想留的内容", "适合谁：经常要存网上的视频资料的人"]},
    {"keys": ["rss", "订阅"], "title": "开源 RSS 订阅聚合器",
     "points": ["是什么：把各个网站更新汇总到一个地方的阅读器", "能干啥：告别算法推荐，自己掌控信息源", "适合谁：想安静刷资讯、不被平台牵着走的人"]},
    {"keys": ["password", "密码", "vault", "secret"], "title": "开源密码管理器",
     "points": ["是什么：把账号密码加密存好的免费工具", "能干啥：一个主密码管所有，跨设备同步", "适合谁：密码一大堆、怕泄漏的人"]},
    {"keys": ["vpn", "proxy", "代理", "tunnel"], "title": "开源上网 / 代理工具",
     "points": ["是什么：帮你科学联网、保护流量的免费工具", "能干啥：自建节点，不用买商业套餐", "适合谁：想自己掌控网络、省订阅费的人"]},
    {"keys": ["dashboard", "看板", "monitor", "监控", "grafana"], "title": "开源数据看板 / 监控工具",
     "points": ["是什么：把各种数据画成图表的免费工具", "能干啥：服务器、业务指标一眼看清", "适合谁：想随时盯数据、不想付费监控的人"]},
    {"keys": ["docker", "container", "容器", "kubernetes", "k8s"], "title": "开源容器 / 部署工具",
     "points": ["是什么：把应用打包好、一键跑起来的工具", "能干啥：部署服务不再环境折腾", "适合谁：爱折腾服务器、会点技术的人（安装略复杂）"]},
    {"keys": ["cli", "terminal", "终端", "命令行"], "title": "命令行效率小工具",
     "points": ["是什么：在终端里帮你提速的免费小工具", "能干啥：批量改名、查文件、跑脚本更顺手", "适合谁：常用命令行、想提效的人"]},
    {"keys": ["learn", "学习", "课程", "tutorial", "course", "freecodecamp", "教育"], "title": "开源编程学习平台",
     "points": ["是什么：免费学编程、做项目的在线平台", "能干啥：互动教程、练手项目，边学边做", "适合谁：想学编程、转行的人"]},
    {"keys": ["editor", "ide", "编辑器", "code"], "title": "开源代码编辑器 / IDE",
     "points": ["是什么：写代码、改配置用的免费编辑器", "能干啥：插件丰富，界面清爽", "适合谁：写代码、改配置的人"]},
    {"keys": ["browser", "浏览器"], "title": "开源浏览器 / 浏览器工具",
     "points": ["是什么：自己掌控的浏览工具或插件", "能干啥：去广告、护隐私、自定义", "适合谁：想干净上网、不被追踪的人"]},
    {"keys": ["scrap", "爬虫", "crawl"], "title": "开源爬虫 / 数据采集工具",
     "points": ["是什么：自动从网页抓数据的免费工具", "能干啥：定时采价格、资讯、榜单", "适合谁：要做数据分析、攒素材的人"]},
    {"keys": ["blog", "cms", "wiki", "博客", "建站"], "title": "开源建站 / 博客系统",
     "points": ["是什么：搭个人网站、博客、知识库的免费工具", "能干啥：写文章、发内容，数据自己存", "适合谁：想有自己的地盘、不想被平台绑的人"]},
    {"keys": ["database", "数据库", "db"], "title": "开源数据库 / 数据存储",
     "points": ["是什么：存数据、管数据的免费引擎", "能干啥：替代付费数据库，自己部署更安心", "适合谁：做项目、要存数据的人"]},
    {"keys": ["search", "搜索", "搜索引擎"], "title": "开源搜索引擎",
     "points": ["是什么：自己搭建的搜索工具，不依赖大厂", "能干啥：搜本地文件、搜全网都行", "适合谁：隐私控、想自己掌控搜索的人"]},
    {"keys": ["ebook", "电子书", "book"], "title": "开源电子书 / 阅读工具",
     "points": ["是什么：管电子书、做电子书阅读的免费工具", "能干啥：排版、转格式、舒心读", "适合谁：爱看书、攒电子书的人"]},
    {"keys": ["calendar", "日历", "email", "邮件", "schedule"], "title": "开源日历 / 邮件工具",
     "points": ["是什么：管日程、管邮件的免费工具", "能干啥：替代商业套件，数据自己留", "适合谁：想摆脱大厂邮箱日历的人"]},
    {"keys": ["file", "文件", "sync", "同步", "网盘"], "title": "开源文件 / 网盘同步工具",
     "points": ["是什么：自己搭的网盘，文件不用存别人家", "能干啥：多设备同步、分享链接", "适合谁：不想给网盘交会员费的人"]},
    {"keys": ["ai", "人工智能", "machine-learning", "deep-learning", "neural"], "title": "AI 开源项目",
     "points": ["是什么：和人工智能相关的免费开源项目", "能干啥：模型、工具、应用都能玩", "适合谁：想跟 AI 热点、写 AI 文章的人"]},
]


def load_article_data():
    try:
        if os.path.exists(ARTICLE_DATA):
            with open(ARTICLE_DATA, encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return []


def load_history():
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return []


def save_history(names):
    history = load_history()
    cutoff = (today - timedelta(days=14)).strftime("%Y-%m-%d")
    history = [h for h in history if h.get("date", "") > cutoff]
    for n in names:
        history.append({"name": n, "date": today.strftime("%Y-%m-%d")})
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_seen_names():
    history = load_history()
    cutoff = (today - timedelta(days=14)).strftime("%Y-%m-%d")
    return {h["name"] for h in history if h.get("date", "") > cutoff}


def load_hot_rotation():
    try:
        if os.path.exists(HOT_FILE):
            with open(HOT_FILE, encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return {"week": "", "pushed": []}


def save_hot_rotation(state):
    with open(HOT_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def search_github(query, per_page=10):
    url = f"https://api.github.com/search/repositories?q={requests.utils.quote(query)}&sort=stars&order=desc&per_page={per_page}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            items = r.json().get("items", [])
            print(f"  API 200: {len(items)} 个项目 ({query[:30]}...)")
            return items
        elif r.status_code == 403:
            print(f"  API 403 限速，等60秒... {r.text[:100]}")
            time.sleep(60)
            return search_github(query, per_page)
        else:
            print(f"  API {r.status_code}: {r.text[:100]}")
    except Exception as e:
        print(f"  搜索失败: {e}")
    return []


def score_repo(repo, articles):
    score = 0
    stars = repo["stargazers_count"]
    topics = repo.get("topics", [])
    desc = (repo.get("description") or "").lower()
    name = (repo.get("name") or "").lower()
    lang = repo.get("language") or ""
    match_reasons = []

    if stars >= 10000: score += 5
    elif stars >= 5000: score += 4
    elif stars >= 1000: score += 3
    elif stars >= 500: score += 2
    else: score += 1

    for pattern_name, pattern in PATTERNS.items():
        if any(k in desc or k in topics or k in name for k in pattern["keywords"]):
            score += pattern["score"]
            if pattern["score"] > 0:
                match_reasons.append(pattern["reason"])

    easy_lang = ["python", "javascript", "typescript", "shell"]
    hard_lang = ["c++", "c", "java", "rust", "go"]
    if lang.lower() in easy_lang:
        score += 1
    elif lang.lower() in hard_lang:
        score -= 1

    return score, match_reasons


def build_cn_card(repo):
    """生成全中文项目卡片：大白话标题 + 3条中文要点 + 星数/语言/更新。绝不出现英文原句。"""
    desc = (repo.get("description") or "").lower()
    topics = [t.lower() for t in repo.get("topics", [])]
    name = (repo.get("name") or "").lower()
    lang = repo.get("language") or "多语言"
    stars = repo.get("stargazers_count", 0)
    stars_k = f"{stars/1000:.1f}K" if stars >= 1000 else str(stars)
    blob = f"{name} {desc} {' '.join(topics)}"

    title = None
    points = None
    for card in CN_CARDS:
        if any(k in blob for k in card["keys"]):
            title = card["title"]
            points = card["points"]
            break

    if not title:
        is_ai = any(k in blob for k in ["ai", "llm", "gpt", "chat", "agent", "model"])
        is_free = any(k in blob for k in ["free", "open-source", "alternative", "开源"])
        is_web = any(k in blob for k in ["web", "online", "saas", "browser"])
        is_tool = any(k in blob for k in ["tool", "util", "manager", "cli", "script", "bot"])
        if is_ai and is_free:
            title = "免费的 AI 开源工具"
        elif is_ai:
            title = "AI 相关的开源工具"
        elif is_free:
            title = "免费开源工具"
        elif is_web:
            title = "在线就能用的开源工具"
        else:
            title = "开源工具（照名字就能看出能干啥）"
        # 描述缺失时，用项目名 + topics 生成真实可读的兜底要点，绝不出现“小叮当下次细说”
        name_cn = repo.get("name", "").replace("-", " ").replace("_", " ")
        topic_cn = "、".join(topics[:3]) if topics else ""
        points = [
            f"是什么：一个叫「{name_cn}」的开源项目" + (f"，标签是 {topic_cn}" if topic_cn else "，代码公开可免费自部署"),
            "能干啥：点下面链接进项目主页，README 里有完整功能说明和用法",
            "适合谁：想省会员费、或想自己掌控工具、跟着热点折腾的人",
        ]
        if not is_tool and not is_ai:
            points[1] = "能干啥：开源项目，自己部署就能用，具体看主页说明"

    updated = (repo.get("pushed_at") or "")[:10]
    fresh = f"本周有更新（{updated}）" if updated >= DATE_7D else f"最近更新 {updated}"
    lines = [title, "·" + points[0], "·" + points[1], "·" + points[2], f"星数 {stars_k} · 语言 {lang} · {fresh}"]
    return "\n".join(lines)


def get_hot_pool():
    """本周最热门：本周内有更新、星数较高的项目前10名。"""
    q = f"stars:>300 pushed:>{WEEK_MONDAY}"
    items = search_github(q, per_page=10)
    return items[:10]


def pick_hot(hot_pool, rotation, count=2):
    pushed = set(rotation.get("pushed", []))
    fresh = [r for r in hot_pool if r["full_name"] not in pushed]
    chosen = fresh[:count]
    for r in chosen:
        pushed.add(r["full_name"])
    rotation["pushed"] = list(pushed)
    rotation["updated"] = today.strftime("%Y-%m-%d")
    return chosen, rotation


def pick_data_related(repos, articles, exclude, count=3):
    seen = get_seen_names() | exclude
    scored = []
    for r in repos:
        if r["full_name"] in seen:
            continue
        s, reasons = score_repo(r, articles)
        s += random.uniform(0, 0.3)
        scored.append((s, r, reasons))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:count]


def build_message(hot_picks, data_picks, best):
    date_cn = f"{today.year}年{today.month}月{today.day}日"
    weekday_map = {"Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
                   "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"}
    weekday = weekday_map.get(today.strftime("%A"), "")
    title = f"老贾，{date_cn} GitHub 开源项目推荐"

    lines = [f"老贾，{date_cn}（{weekday}）早上好。今天给你 5 个项目：2 个本周最热 + 3 个最适合你写。\n"]

    lines.append("【一、本周最热的 GitHub 项目】（每天轮2个，不重复）")
    for r in hot_picks:
        lines.append(f"\n◆ {r['full_name']}")
        lines.append(build_cn_card(r))
        lines.append(f"项目主页：[{r['full_name']}]({r['html_url']})")

    lines.append("\n【二、最适合你写的 3 个项目】（结合你历史数据）")
    for i, (s, r, reasons) in enumerate(data_picks, 1):
        if not r.get("full_name") or r["full_name"].startswith("（"):
            continue
        lines.append(f"\n{i}. {r['full_name']}")
        lines.append(build_cn_card(r))
        lines.append(f"项目主页：[{r['full_name']}]({r['html_url']})")

    best_repo = best[1] if isinstance(best[1], dict) else {}
    if best_repo.get("full_name") and not best_repo["full_name"].startswith("（"):
        best_reasons = best[2]
        lines.append("\n【三、今天最推荐你写这个】")
        lines.append(f"\n★ {best_repo['full_name']}")
        lines.append(build_cn_card(best_repo))
        lines.append(f"\n为什么推荐你写：")
        for rsn in best_reasons[:3]:
            lines.append(f"  · {rsn}")
        blob = f"{(best_repo.get('description') or '').lower()} {' '.join(best_repo.get('topics', []))} {best_repo.get('name','').lower()}"
        if any(k in blob for k in ["free", "省钱", "免费", "替代", "alternative"]):
            lines.append("  · 你之前写省钱/免费类文章，最高891播放、155转发，读者很爱看")
        if any(k in blob for k in ["money", "job", "印钞", "赚钱", "搞钱"]):
            lines.append("  · 你之前写搞钱类文章，最高5617播放、811转发，爆款潜力大")
        if any(k in blob for k in ["google", "microsoft", "apple", "openai", "meta", "deepseek"]):
            lines.append("  · 蹭大厂热度，你之前写Google相关文章最高8830播放")
        lines.append(f"链接：[{best_repo['full_name']}]({best_repo['html_url']})")

    lines.append("\n（想写哪个回复编号或“写”，我帮你出文章）")
    return title, "\n".join(lines)


def send_wechat(title, content):
    if not SENDKEY:
        print("SENDKEY 未设定，跳过推送")
        return
    url = f"https://sctapi.ftqq.com/{SENDKEY}.send"
    try:
        r = requests.post(url, data={"title": title, "desp": content}, timeout=10)
        print("推送结果:", r.text[:200])
    except Exception as e:
        print("推送失败:", e)


def main():
    dry_run = "--dry-run" in sys.argv
    print(f"抓取 GitHub 项目 ({today.strftime('%Y-%m-%d')})...")

    articles = load_article_data()
    print(f"已加载 {len(articles)} 条文章数据")

    # 搜索“数据相关”候选。前面几条是「涨粉高类型」的定向捞货（求职/搞钱/省钱替代），
    # 保证候选池里一定有读者最爱看的类型，不会断供；后面几条泛热门兜底。
    DATE_30D = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    queries = [
        f"job OR career OR resume OR interview stars:>300 pushed:>{DATE_30D}",   # 涨粉冠军：求职上岸
        f"alternative OR self-hosted OR free stars:>500 pushed:>{DATE_7D}",       # 省钱替代付费
        f"money OR monetize OR automation OR agent stars:>500 pushed:>{DATE_7D}", # 搞钱/自动化
        f"stars:>800 pushed:>{DATE_7D}",                                          # 泛热门兜底
        f"topic:ai stars:>300 pushed:>{DATE_7D}",                                 # AI 兜底
    ]
    all_repos = []
    for q in queries:
        results = search_github(q, per_page=10)
        all_repos.extend(results)
        time.sleep(0.5)
        seen = set()
        unique = [r for r in all_repos if not (r["full_name"] in seen or seen.add(r["full_name"]))]
        if len(unique) >= 20:
            break

    # 本周热门（带轮转）
    hot_pool = get_hot_pool()
    rotation = load_hot_rotation()
    if rotation.get("week") != WEEK_MONDAY or len(rotation.get("pushed", [])) >= 10:
        rotation = {"week": WEEK_MONDAY, "pushed": []}
    hot_chosen, rotation = pick_hot(hot_pool, rotation, count=2)
    print(f"  热门轮转：本周已推 {len(rotation.get('pushed', []))} 个，本次选 {len(hot_chosen)} 个")

    # 数据相关3个，排除已选热门
    hot_names = {r["full_name"] for r in hot_chosen}
    data_picks = pick_data_related(all_repos, articles, hot_names, count=3)
    while len(data_picks) < 3:
        data_picks.append((0, {"full_name": "（今天数据相关项目不足，明天补）", "description": "", "topics": [], "html_url": "", "stargazers_count": 0, "language": "", "pushed_at": ""}, []))

    # 主推：数据相关里分数最高的（最适合写）；否则取热门第一个
    best = data_picks[0] if data_picks else (0, {}, [])
    if not isinstance(best[1], dict) or not best[1].get("full_name") or best[1]["full_name"].startswith("（"):
        best = (0, hot_chosen[0], []) if hot_chosen else (0, {"full_name": "", "html_url": ""}, [])

    # 保存下游状态（兼容 planet 任务）
    github_state_file = os.path.join(BASE, "state_github_projects.json")
    out_projects = []
    for _, r, _ in data_picks:
        if isinstance(r, dict) and r.get("full_name") and not r["full_name"].startswith("（"):
            out_projects.append(r)
    out_projects.extend(hot_chosen)
    with open(github_state_file, "w", encoding="utf-8") as f:
        json.dump({
            "projects": [{
                "name": r["full_name"],
                "stars": r.get("stargazers_count", 0),
                "lang": r.get("language", ""),
                "description": r.get("description", ""),
                "url": r.get("html_url", ""),
                "topics": r.get("topics", []),
                "updated": (r.get("pushed_at") or "")[:10],
            } for r in out_projects],
            "date": today.strftime("%Y-%m-%d"),
            "best_pick": best[1]["full_name"] if isinstance(best[1], dict) else "",
        }, f, ensure_ascii=False)

    title, content = build_message(hot_chosen, data_picks, best)
    print("\n========== 推送预览 ==========")
    print(content)
    print("==============================\n")

    if dry_run:
        print("[dry-run] 不推送，仅预览")
    else:
        send_wechat(title, content)
        all_names = hot_names | {r["full_name"] for _, r, _ in data_picks if isinstance(r, dict) and r.get("full_name") and not r["full_name"].startswith("（")}
        save_history(list(all_names))
        save_hot_rotation(rotation)
        print(f"推送完成：热门 {len(hot_chosen)} + 数据 {len([p for p in data_picks if isinstance(p[1], dict) and p[1].get('full_name') and not p[1]['full_name'].startswith('（')])}")


if __name__ == "__main__":
    main()
