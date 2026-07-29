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
    {"keys": ["selfhosted", "self-host", "self hosted"], "title": "可以自己搭建的免费软件合集",
     "points": ["收集几百个开源软件，自己部署就能用", "替代网盘、笔记、密码管理器等付费服务", "数据自己掌控，不用交会员费"]},
    {"keys": ["note", "notes", "notion", "obsidian", "markdown"], "title": "笔记 / 写作工具",
     "points": ["帮你记笔记、写文档、整理知识", "支持本地保存、双向链接、导出分享", "数据自己留着，不怕平台跑路"]},
    {"keys": ["pdf"], "title": "PDF 处理工具",
     "points": ["合并、拆分、压缩、转换 PDF", "不用开会员就能处理各种 PDF 文件", "经常和 PDF 打交道的人能省不少钱"]},
    {"keys": ["ocr", "recogni", "文字识别"], "title": "文字识别（OCR）工具",
     "points": ["把图片里的文字自动提取出来", "截图、扫描件一键变成可编辑文字", "不用手动抄写，省时省力"]},
    {"keys": ["translat", "翻译"], "title": "翻译工具",
     "points": ["自己部署的翻译工具，不依赖付费接口", "文档、网页、对话都能翻", "免费又好用，还保护隐私"]},
    {"keys": ["agent", "automat", "workflow", "自动化"], "title": "自动化工具 / AI 智能体",
     "points": ["按你的指令自动跑流程、调工具", "自动填表、爬数据、发消息", "省下重复劳动，专注更重要的事"]},
    {"keys": ["chatbot", "chat", "llm", "gpt", "chatgpt", "大模型", "大语言模型"], "title": "AI 对话助手",
     "points": ["自己部署的 AI 对话工具", "数据留在自己手里，不用上传", "问答、写稿、总结，不用给大厂交钱"]},
    {"keys": ["image", "photo", "图片", "绘画", "diffusion", "stable diffusion", "midjourney"], "title": "AI 绘画 / 图片处理工具",
     "points": ["生成或处理图片的免费工具", "文生图、改图、抠图都能做", "省掉付费软件，自己做封面和素材"]},
    {"keys": ["video", "视频"], "title": "视频处理工具",
     "points": ["剪辑、压制、下载、处理视频", "不用开剪映会员也能剪视频", "做短视频、做内容的人能用上"]},
    {"keys": ["audio", "music", "音乐", "播客", "podcast", "tts", "语音"], "title": "音频 / 语音工具",
     "points": ["播放、剪辑、生成音频的免费工具", "配音、转字幕、做播客都行", "做音频内容、播客的人可以试试"]},
    {"keys": ["download", "下载", "youtube", "bilibili"], "title": "下载工具",
     "points": ["从各平台下载视频、音频、文件", "一键保存想保留的在线内容", "看到好视频随时存下来"]},
    {"keys": ["rss", "订阅"], "title": "RSS 订阅阅读器",
     "points": ["把各网站更新汇总到一个地方", "自己掌控想看什么，不被算法推荐牵着走", "安静刷资讯，不被平台打扰"]},
    {"keys": ["password", "密码", "vault", "secret"], "title": "密码管理器",
     "points": ["把账号密码加密存好", "一个主密码管所有账号", "跨设备同步，不怕密码泄漏"]},
    {"keys": ["vpn", "proxy", "代理", "tunnel"], "title": "网络代理工具",
     "points": ["帮你科学联网的免费工具", "自建节点，不用买商业套餐", "自己掌控网络，省订阅费"]},
    {"keys": ["dashboard", "看板", "monitor", "监控", "grafana"], "title": "数据看板 / 监控工具",
     "points": ["把各种数据画成图表", "服务器、业务指标一眼看清", "随时盯数据，不用付费买监控"]},
    {"keys": ["docker", "container", "容器", "kubernetes", "k8s"], "title": "容器部署工具",
     "points": ["把应用打包好、一键跑起来", "部署服务不再折腾环境", "爱折腾服务器的人必备（安装略复杂）"]},
    {"keys": ["cli", "terminal", "终端", "命令行"], "title": "命令行效率工具",
     "points": ["在终端里帮你提速的小工具集", "批量改名、查文件、跑脚本更顺手", "常用命令行的人能提效不少"]},
    {"keys": ["learn", "学习", "课程", "tutorial", "course", "freecodecamp", "教育"], "title": "编程学习平台",
     "points": ["免费学编程、做项目", "互动教程、练手项目，边学边做", "想学编程、想转行的人可以看看"]},
    {"keys": ["editor", "ide", "编辑器", "code"], "title": "代码编辑器",
     "points": ["写代码、改配置用的编辑器", "插件丰富，界面清爽", "程序员写代码的趁手工具"]},
    {"keys": ["browser", "浏览器"], "title": "浏览器工具",
     "points": ["自己掌控的浏览工具或插件", "去广告、护隐私、自定义体验", "想干净上网、不被追踪的人适用"]},
    {"keys": ["scrap", "爬虫", "crawl"], "title": "爬虫 / 数据采集工具",
     "points": ["自动从网页抓数据", "定时采价格、资讯、榜单", "做数据分析、攒素材的人能用上"]},
    {"keys": ["blog", "cms", "wiki", "博客", "建站"], "title": "建站 / 博客系统",
     "points": ["搭个人网站、博客、知识库", "写文章、发内容，数据自己存", "想有自己的地盘、不被平台绑的人"]},
    {"keys": ["database", "数据库", "db"], "title": "数据库工具",
     "points": ["存数据、管数据的免费引擎", "替代付费数据库，自己部署更放心", "做项目、要存数据的人能用"]},
    {"keys": ["search", "搜索", "搜索引擎"], "title": "搜索引擎工具",
     "points": ["自己搭建的搜索工具", "搜本地文件、搜全网都行", "隐私控、想自己掌控搜索的人适用"]},
    {"keys": ["ebook", "电子书", "book"], "title": "电子书 / 阅读工具",
     "points": ["管电子书、看电子书的免费工具", "排版、转格式、舒心阅读", "爱看书、攒电子书的人必备"]},
    {"keys": ["calendar", "日历", "email", "邮件", "schedule"], "title": "日历 / 邮件工具",
     "points": ["管日程、管邮件的免费工具", "替代商业套件，数据自己留着", "想摆脱大厂邮箱日历的人可以试试"]},
    {"keys": ["file", "文件", "sync", "同步", "网盘"], "title": "文件同步 / 网盘工具",
     "points": ["自己搭的网盘，文件不用存别人那", "多设备同步、分享链接", "不想给网盘交会员费的人适合"]},
    {"keys": ["job", "career", "resume", "interview"], "title": "求职面试工具",
     "points": ["简历优化、面试准备、求职攻略合集", "涵盖各公司面经和技术准备", "找工作、跳槽的人可以参考"]},
    {"keys": ["algorithm", "algorithms", "数据结构"], "title": "算法学习工具",
     "points": ["学习常见算法和数据结构的免费资源", "带代码实现和详细讲解，边学边练", "准备面试、提升编程功底的人适合"]},
    {"keys": ["ai", "人工智能", "machine-learning", "deep-learning", "neural"], "title": "AI 开源项目",
     "points": ["和人工智能相关的开源项目", "模型、工具、应用都能玩", "想跟 AI 热点、写 AI 文章的人关注"]},
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
    """简单中文卡片：标题 + 3个能做什么 + 星标 + 链接"""
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
        raw_name = repo.get("name", "").replace("-", " ").replace("_", " ")
        raw_topics = [t for t in repo.get("topics", []) if t.lower() not in ("awesome", "awesome-list")]
        topic_str = "、".join(raw_topics[:3]) if raw_topics else ""
        title = raw_name if not topic_str else raw_name + "（" + topic_str + "）"
        pts = []
        if raw_topics:
            pts.append(f"涉及 {topic_str} 相关技术")
        if stars >= 3000:
            pts.append(f"{stars//1000}K 星热门项目，社区活跃")
        else:
            pts.append("开源免费，感兴趣可以看看")
        if raw_name:
            pts.append(f"项目名称：{raw_name}")
        while len(pts) < 3:
            pts.append("点下面链接进项目主页查看详情")
        points = pts[:3]

    url = repo.get("html_url", "")
    lines = [title, "· " + points[0], "· " + points[1], "· " + points[2], f"☆ Star {stars_k} · {lang}", url]
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


def build_message(items, recommends):
    title = f"今日推荐 {len(items)} 个开源项目"

    lines = []
    for item in items:
        lines.append(build_cn_card(item))
        lines.append("")

    if recommends:
        lines.append("推荐写这 2 个：")
        for i, r in enumerate(recommends, 1):
            lines.append(f"{i}. {r.get('name', '')}（{r.get('title', '')}）")
            lines.append(r.get('url', ''))

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

    # 选5个：数据推荐+热门，去重
    seen_names = set()
    all_items = []
    for _, r, _ in data_picks:
        if isinstance(r, dict) and r.get("full_name") and not r["full_name"].startswith("（"):
            if r["full_name"] not in seen_names:
                seen_names.add(r["full_name"])
                all_items.append(r)
    for r in hot_chosen:
        if r.get("full_name") not in seen_names:
            seen_names.add(r["full_name"])
            all_items.append(r)
    all_items = all_items[:5]

    # 推荐2个写公众号
    top_data = [(s, r) for s, r, _ in data_picks if isinstance(r, dict) and r.get("full_name") and not r["full_name"].startswith("（")]
    top_data.sort(key=lambda x: x[0], reverse=True)
    recommends = []
    for s, r in top_data[:2]:
        raw = build_cn_card(r).split("\n")[0]
        title = raw.replace("\U0001f4dd", "").replace("\U0001f525", "").strip()
        recommends.append({"name": r["full_name"], "title": title, "url": r.get("html_url", "")})

    # 保存下游状态
    github_state_file = os.path.join(BASE, "state_github_projects.json")
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
            } for r in all_items],
            "date": today.strftime("%Y-%m-%d"),
        }, f, ensure_ascii=False)

    title, content = build_message(all_items, recommends)
    print("\n========== 推送预览 ==========")
    print(content)
    print("==============================\n")

    if dry_run:
        print("[dry-run] 不推送，仅预览")
    else:
        send_wechat(title, content)
        all_names = {r["full_name"] for r in all_items if isinstance(r, dict) and r.get("full_name")}
        save_history(list(all_names))
        save_hot_rotation(rotation)
        print(f"推送完成：{len(all_items)} 个项目")


if __name__ == "__main__":
    main()
