"""Optimize fetch_github_projects.py - better formatting, clear sections"""
import os, sys, requests, json, random, time
from datetime import datetime, timedelta

today = datetime.now()
WEEK_MONDAY = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
DATE_7D = (today - timedelta(days=7)).strftime("%Y-%m-%d")
DATE_30D = (today - timedelta(days=30)).strftime("%Y-%m-%d")

SENDKEY = os.environ.get("SENDKEY", "")
GH_TOKEN = os.environ.get("GH_TOKEN", "")
BASE = os.path.join(os.path.dirname(__file__), "..")
if not SENDKEY or not GH_TOKEN:
    try:
        with open(os.path.join(BASE, ".env"), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("SENDKEY=") and not SENDKEY:
                    SENDKEY = line.split("=", 1)[1]
                elif line.startswith("GH_TOKEN=") and not GH_TOKEN:
                    GH_TOKEN = line.split("=", 1)[1]
    except:
        pass
STATE_FILE = os.path.join(BASE, "state_github_projects.json")
HOT_FILE = os.path.join(BASE, "hot_rotation.json")
HISTORY_FILE = os.path.join(BASE, "recommended_history.json")
ARTICLE_DATA = os.path.join(BASE, "article_data.json")

HEADERS = {"Accept": "application/vnd.github.v3+json", "User-Agent": "auto-topic-bot"}
if GH_TOKEN: HEADERS["Authorization"] = f"Bearer {GH_TOKEN}"

PATTERNS = {
    "求职上岸": {"keywords": ["job", "career", "resume", "interview", "求职", "找工作", "简历", "面试", "上岸"], "score": 7},
    "省钱免费": {"keywords": ["free", "alternative", "省钱", "免费", "替代", "open-source"], "score": 6},
    "搞钱变现": {"keywords": ["money", "赚钱", "搞钱", "副业", "变现", "monetize"], "score": 6},
    "大厂干货": {"keywords": ["google", "microsoft", "openai", "meta", "nvidia", "deepseek", "claude"], "score": 5},
    "AI相关": {"keywords": ["ai", "llm", "gpt", "chatgpt", "agent", "langchain", "rag"], "score": 3},
    "直接能用": {"keywords": ["web", "online", "saas", "app", "gui", "extension", "browser"], "score": 2},
    "纯技术": {"keywords": ["driver", "kernel", "compiler", "benchmark", "kubernetes"], "score": -5},
}

CN_CARDS = [
    {"keys": ["selfhosted", "self-host"], "title": "可以自己搭建的免费软件合集",
     "points": ["收集几百个开源软件，自己部署就能用", "替代网盘、笔记、密码管理器等付费服务", "数据自己掌控，不用交会员费"]},
    {"keys": ["agent", "automat", "workflow"], "title": "自动化工具 / AI 智能体",
     "points": ["按你的指令自动跑流程、调工具", "自动填表、爬数据、发消息", "省下重复劳动，专注更重要的事"]},
    {"keys": ["job", "career", "resume", "interview"], "title": "求职面试工具",
     "points": ["简历优化、面试准备、求职攻略合集", "涵盖各公司面经和技术准备", "找工作、跳槽的人可以参考"]},
    {"keys": ["algorithm", "algorithms"], "title": "算法学习工具",
     "points": ["学习常见算法和数据结构的免费资源", "带代码实现和详细讲解，边学边练", "准备面试、提升编程功底的人适合"]},
    {"keys": ["note", "notes", "obsidian", "markdown"], "title": "笔记 / 写作工具",
     "points": ["帮你记笔记、写文档、整理知识", "支持本地保存、双向链接", "数据自己留着，不怕平台跑路"]},
    {"keys": ["pdf"], "title": "PDF 处理工具",
     "points": ["合并、拆分、压缩、转换 PDF", "不用开会员就能处理各种 PDF", "经常和 PDF 打交道的人能省不少钱"]},
    {"keys": ["ocr", "recogni"], "title": "文字识别（OCR）工具",
     "points": ["把图片里的文字自动提取出来", "截图、扫描件一键变成可编辑文字", "不用手动抄写，省时省力"]},
    {"keys": ["image", "photo", "diffusion", "stable diffusion"], "title": "AI 绘画 / 图片处理工具",
     "points": ["生成或处理图片的免费工具", "文生图、改图、抠图都能做", "省掉付费软件，自己做封面和素材"]},
    {"keys": ["video"], "title": "视频处理工具",
     "points": ["剪辑、压制、下载、处理视频", "不用开剪映会员也能剪视频", "做短视频和内容的人能用上"]},
    {"keys": ["password", "vault", "secret"], "title": "密码管理器",
     "points": ["把账号密码加密存好", "一个主密码管所有账号", "跨设备同步，不怕密码泄漏"]},
    {"keys": ["file", "sync", "网盘"], "title": "文件同步 / 网盘工具",
     "points": ["自己搭的网盘，文件不用存别人那", "多设备同步、分享链接", "不想给网盘交会员费的人适合"]},
    {"keys": ["chatbot", "chat", "llm", "gpt", "chatgpt", "大模型"], "title": "AI 对话助手",
     "points": ["自己部署的 AI 对话工具", "数据留在自己手里，不用上传", "问答、写稿、总结，不用给大厂交钱"]},
    {"keys": ["download", "youtube", "bilibili"], "title": "下载工具",
     "points": ["从各平台下载视频、音频、文件", "一键保存想保留的在线内容", "看到好视频随时存下来"]},
    {"keys": ["blog", "cms", "wiki", "博客", "建站"], "title": "建站 / 博客系统",
     "points": ["搭个人网站、博客、知识库", "写文章、发内容，数据自己存", "想有自己的地盘、不被平台绑的人"]},
    {"keys": ["database", "db"], "title": "数据库工具",
     "points": ["存数据、管数据的免费引擎", "替代付费数据库，自己部署更放心", "做项目、要存数据的人能用"]},
    {"keys": ["monitor", "监控"], "title": "数据看板 / 监控工具",
     "points": ["把各种数据画成图表", "服务器、业务指标一眼看清", "随时盯数据，不用付费买监控"]},
]

# ==================== 核心改进：优化排版 ====================

def get_category(repo):
    """返回项目命中的分类标题；没命中返回项目名"""
    desc = (repo.get("description") or "").lower()
    topics = [t.lower() for t in repo.get("topics", [])]
    name = (repo.get("name") or "").lower()
    blob = f"{name} {desc} {' '.join(topics)}"
    for card in CN_CARDS:
        if any(k in blob for k in card["keys"]):
            return card["title"]
    return None


def build_cn_card(repo, idx=None):
    """生成排版清晰的中文项目卡片，标题在上，要点分段，空行隔开"""
    desc = (repo.get("description") or "").lower()
    topics = [t.lower() for t in repo.get("topics", [])]
    name = (repo.get("name") or "").lower()
    blob = f"{name} {desc} {' '.join(topics)}"
    stars = repo.get("stargazers_count", 0)
    stars_k = f"{stars/1000:.1f}K" if stars >= 1000 else str(stars)
    lang = repo.get("language") or "多语言"
    repo_name = repo.get("full_name") or repo.get("name", "")

    title, points = None, None
    for card in CN_CARDS:
        if any(k in blob for k in card["keys"]):
            title = card["title"]
            points = card["points"]
            break

    if not title:
        raw_name = repo.get("name", "").replace("-", " ").replace("_", " ")
        topic_str = "、".join(topics[:3]) if topics else ""
        title = raw_name if not topic_str else f"{raw_name}（{topic_str}）"
        pts = []
        if stars >= 3000:
            pts.append(f"{stars//1000}K 星热门项目，社区活跃")
        else:
            pts.append("开源免费，感兴趣可以看看")
        if repo.get("description"):
            pts.append(repo.get("description")[:60])
        while len(pts) < 3:
            pts.append("点下面链接进项目主页查看详情")
        points = pts[:3]

    url = repo.get("html_url", "")

    head = f"【{idx}】📌 {repo_name}" if idx else f"📌 {repo_name}"
    sub = f"🏷 {title}"

    # 排版优化：编号+项目名 / 分类 / 每个要点单独成段（段间空行）/ 底部信息
    lines = [
        head,
        "",
        sub,
        "",
        f"  · {points[0]}",
        "",
        f"  · {points[1]}",
        "",
        f"  · {points[2]}",
        "",
        f"  ⭐ {stars_k}  |  {lang}",
        f"  🔗 {url}",
        "",
        "————————————",
        "",
    ]
    return "\n".join(lines)


def build_message(items, recommends):
    """更好的整体排版：标题 + 空行 + 逐个项目 + 空行 + 推荐"""
    lines = [
        "📬 今日 GitHub 开源项目推荐",
        "",
        f"共 {len(items)} 个精选项目",
        "",
        "=" * 30,
        "",
    ]

    for i, item in enumerate(items, 1):
        lines.append(build_cn_card(item, i))

    if recommends:
        lines.append("")
        lines.append("📝 推荐写公众号文章：")
        lines.append("")
        for i, r in enumerate(recommends, 1):
            lines.append(f"{i}. {r['name']}")
            lines.append(f"   {r['title']}")
            lines.append(f"   {r['url']}")
            lines.append("")

    lines.append("— End —")
    lines.append("")
    lines.append("明早8点见 👋")

    return "每日 GitHub 推荐", "\n".join(lines)


# ==================== 以下保持原逻辑，只改排版 ====================

def load_history():
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, encoding="utf-8") as f:
                return json.load(f)
    except: pass
    return []

def save_history(names):
    history = load_history()
    cutoff = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    history = [h for h in history if h.get("date", "") > cutoff]
    for n in names:
        history.append({"name": n, "date": today.strftime("%Y-%m-%d")})
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_seen_names():
    history = load_history()
    cutoff = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    return {h["name"] for h in history if h.get("date", "") > cutoff}

def load_hot_rotation():
    try:
        if os.path.exists(HOT_FILE):
            with open(HOT_FILE, encoding="utf-8") as f:
                return json.load(f)
    except: pass
    return {"week": "", "pushed": []}

def save_hot_rotation(state):
    with open(HOT_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def search_github(query, per_page=10):
    url = f"https://api.github.com/search/repositories?q={requests.utils.quote(query)}&sort=stars&order=desc&per_page={per_page}"
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code == 200:
                return r.json().get("items", [])
            elif r.status_code == 403:
                time.sleep(60)
                continue
        except: pass
    return []

def score_repo(repo):
    score = 0
    stars = repo["stargazers_count"]
    topics = repo.get("topics", [])
    desc = (repo.get("description") or "").lower()
    name = (repo.get("name") or "").lower()

    if stars >= 10000: score += 5
    elif stars >= 5000: score += 4
    elif stars >= 1000: score += 3
    elif stars >= 500: score += 2
    else: score += 1

    for pname, p in PATTERNS.items():
        if any(k in desc or k in topics or k in name for k in p["keywords"]):
            score += p["score"]

    lang = repo.get("language") or ""
    if lang.lower() in ("python", "javascript", "typescript", "shell"): score += 1
    elif lang.lower() in ("c++", "c", "java", "rust", "go"): score -= 1

    return score

def get_hot_pool():
    WEEK_MONDAY = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
    items = search_github(f"stars:>300 pushed:>{WEEK_MONDAY}", per_page=10)
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
    print(f"GitHub 项目推荐 ({today.strftime('%Y-%m-%d')})...")

    queries = [
        f"job OR career OR resume OR interview stars:>300 pushed:>{DATE_30D}",
        f"alternative OR self-hosted OR free stars:>500 pushed:>{DATE_7D}",
        f"money OR monetize OR automation OR agent stars:>500 pushed:>{DATE_7D}",
        f"stars:>800 pushed:>{DATE_7D}",
        f"topic:ai stars:>300 pushed:>{DATE_7D}",
        f"notes OR docs OR markdown OR writing stars:>500 pushed:>{DATE_7D}",
        f"image OR video OR design OR pdf stars:>500 pushed:>{DATE_7D}",
    ]
    all_repos = []
    for q in queries:
        all_repos.extend(search_github(q, per_page=15))
        time.sleep(0.5)
        seen = set()
        unique = [r for r in all_repos if not (r["full_name"] in seen or seen.add(r["full_name"]))]
        if len(unique) >= 40:
            break

    hot_pool = get_hot_pool()
    rotation = load_hot_rotation()
    if rotation.get("week") != WEEK_MONDAY or len(rotation.get("pushed", [])) >= 10:
        rotation = {"week": WEEK_MONDAY, "pushed": []}
    hot_chosen, rotation = pick_hot(hot_pool, rotation, count=2)

    hot_names = {r["full_name"] for r in hot_chosen}
    scored = []
    seen = get_seen_names() | hot_names
    for r in all_repos:
        if r["full_name"] in seen: continue
        s = score_repo(r) + random.uniform(0, 0.3)
        scored.append((s, r))
    scored.sort(key=lambda x: x[0], reverse=True)

    # 分类去重后选取，保证每个分类只出现一次（先取分数高的，再补热门）
    seen_names = set()
    used_cats = set()
    all_items = []
    candidates = [r for _, r in scored] + hot_chosen
    for r in candidates:
        if len(all_items) >= 6:
            break
        if not r.get("full_name") or r["full_name"] in seen_names:
            continue
        cat = get_category(r) or r.get("name", "")
        if cat in used_cats:
            continue
        used_cats.add(cat)
        seen_names.add(r["full_name"])
        all_items.append(r)

    # 推荐2个写公众号（从已选项目里挑，分类不重复）
    recommends = []
    for r in all_items:
        if len(recommends) >= 2:
            break
        card_title = get_category(r) or r.get("name", "")
        recommends.append({"name": r["full_name"], "title": card_title, "url": r.get("html_url", "")})

    # 保存状态
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "projects": [{
                "name": r["full_name"], "stars": r.get("stargazers_count", 0),
                "lang": r.get("language", ""), "description": r.get("description", ""),
                "url": r.get("html_url", ""),
            } for r in all_items],
            "date": today.strftime("%Y-%m-%d"),
        }, f, ensure_ascii=False, indent=2)

    title, content = build_message(all_items, recommends)
    print("\n========== 推送预览 ==========")
    print(content)
    print("==============================")

    if dry_run:
        print("[dry-run] 跳过推送")
    else:
        send_wechat(title, content)
        save_history(list(seen_names))
        save_hot_rotation(rotation)
        print(f"推送完成：{len(all_items)} 个项目")

if __name__ == "__main__":
    main()
