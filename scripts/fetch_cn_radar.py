# -*- coding: utf-8 -*-
"""
中文开源项目雷达（cn-radar）
==========================================
为什么有这个脚本（10/12 老贾亲口说痛点）：
  "这些 GitHub 开源项目，都是老贾自己在今日头条/各种平台看到别人发的，
   然后截图带回家让小叮当分解。"

=> 这个脚本就是替老贾去刷那些平台的。以后不用截图。

干什么（一步到位，五件事）：
  1. 爬中文平台搜索页（今日头条 / B站）——10/12 实测：无登录墙，能拿到正文
  2. 从正文里正则抓 GitHub 仓库名（owner/repo）
  3. 拿 GitHub API 逐个实测：星数 / fork / 协议 / 建仓 / 最后push / issue
  4. 跟视频台账里"已经讲过的集"去重（讲过的自动淘汰）
  5. 按老贾已验证的选题规律打分排序，输出候选清单

跑法：
  python fetch_cn_radar.py            # 正常跑
  python fetch_cn_radar.py --days 3   # 看最近3天的源内容

输出：
  - stdout：人看的候选清单（直接给老贾挑）
  - cn_radar_candidates.json：给下游脚本吃
"""
import sys, os, re, json, time, io
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

LEDGER = os.environ.get("LEDGER_PATH", r"D:\视频探索\视频台账\视频台账.md")
OUT_JSON = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cn_radar_candidates.json")
HISTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_cn_radar_history.json")

# ---------------------------------------------------------------- 平台源
# 10/12 用 playwright MCP 实测：头条 ✅ / B站 ✅ 无登录墙；微博 ❌ 知乎 ❌（要登录，不进）
SOURCES = [
    {"name": "今日头条", "url": "https://so.toutiao.com/search?keyword=GitHub%E5%BC%80%E6%BA%90%E9%A1%B9%E7%9B%AE"},
    {"name": "今日头条2", "url": "https://so.toutiao.com/search?keyword=%E5%BC%80%E6%BA%90%E9%A1%B9%E7%9B%AE%20%E6%98%9F"},
    {"name": "B站", "url": "https://www.bilibili.com/search?keyword=GitHub%E5%BC%80%E6%BA%90%E9%A1%B9%E7%9B%AE"},
]

# 明显不是"能讲一集的项目"的噪音词
NOISE = re.compile(
    r"(awesome|roadmap|interview|cheat|tutorial|book|course|roadmap|面试|教程|课程|书籍|路线图|"
    r"awesome-list|learn-|how-to|100-days|interview-)", re.I)

# 抓仓库名：github.com/owner/repo 优先，其次 owner/repo
RE_URL = re.compile(r"github\.com/([A-Za-z0-9_.\-]+)/([A-Za-z0-9_.\-]+)")
RE_SLASH = re.compile(r"\b([A-Za-z0-9_.\-]{2,40})/([A-Za-z0-9_.\-]{2,60})\b")
# GitHub 保留词，别当仓库名
RESERVED = {"github.com","gist.github.com","raw.githubusercontent.com","api.github.com",
            "twitter.com","www.google.com","images.unsplash.com"}

BAD_TAIL = re.compile(r"\.(png|jpg|jpeg|gif|md|html?|pdf|json|yml|yaml|svg|webp|mp4)$", re.I)


def clean(repo: str) -> str:
    repo = repo.rstrip(".,;:!?)）】\"'")
    if repo.endswith(".git"):
        repo = repo[:-4]
    return repo


def crawl():
    """
    用 playwright 爬每个源，返回 [(源名, 正文)]。
    10/12 第一版教训：只抓搜索结果页 → 只有标题摘要 → 仓库名几乎抓不到（只捞到1个2017年老项目）。
    现在改成【两步】：搜索页拿链接 → 点进详情页拿正文。正文里才有 github.com 链接。
    """
    out = []
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print("[!] 没装 playwright：", e)
        return out

    try:
        pw = sync_playwright().start()
    except Exception as e:
        print("[!] playwright 启动失败：", e)
        return out

    browser = None
    for kw in ({"headless": True, "args": ["--no-sandbox", "--disable-dev-shm-usage"]},
               {"headless": True, "channel": "msedge", "args": ["--no-sandbox", "--disable-dev-shm-usage"]},
               {"headless": False}):
        try:
            browser = pw.chromium.launch(**kw)
            break
        except Exception:
            continue

    if browser is None:
        print("[!] 浏览器起不来")
        pw.stop()
        return out

    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        viewport={"width": 1440, "height": 900},
        locale="zh-CN",
    )
    page = ctx.new_page()
    all_titles = []

    # 详情页链接的特征
    # 10/12 诊断：头条搜索结果的链接全是 so.toutiao.com/search/jump?... 中转页，不是 article 直链
    PAT = {
        "今日头条": re.compile(r"https?://so\.toutiao\.com/search/jump\?"),
        "今日头条2": re.compile(r"https?://so\.toutiao\.com/search/jump\?"),
        "B站": re.compile(r"https?://www\.bilibili\.com/video/BV[0-9A-Za-z]+"),
    }

    for s in SOURCES:
        src = s["name"]
        try:
            page.goto(s["url"], timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            try:
                page.wait_for_selector("body", timeout=5000)
            except Exception:
                pass
            snippet = page.evaluate("() => document.body.innerText") or ""
            out.append((src + "·搜索页", snippet))
            ts = extract_titles(page)
            all_titles.extend(ts)
            print(f"[爬] {src} 搜索页: {len(snippet)} 字, 抓到 {len(ts)} 个标题/摘要")

            # 抽详情页链接（去重、保序、取前 8 条）
            hrefs = page.evaluate("() => Array.from(document.querySelectorAll('a[href]')).map(a => a.href)") or []
            pat = PAT.get(src)
            links = []
            for h in hrefs:
                if not pat or not pat.match(h):
                    continue
                h = h.split("?")[0]
                if h not in links:
                    links.append(h)
            links = links[:8]
            print(f"[爬] {src} 找到 {len(links)} 个详情链接，逐个进正文")

            # 另开一个标签页爬详情，别污染搜索页
            p2 = ctx.new_page()
            for i, h in enumerate(links, 1):
                try:
                    p2.goto(h, timeout=40000, wait_until="domcontentloaded")
                    p2.wait_for_timeout(2200)
                    body = p2.evaluate("() => document.body.innerText") or ""
                    out.append((f"{src}·正文{i}", body))
                    all_titles.extend(extract_titles(p2))
                    print(f"     {i}/{len(links)} {h[:58]} → {len(body)} 字")
                except Exception as e:
                    print(f"     {i}/{len(links)} 失败：{str(e)[:60]}")
                time.sleep(1.0)
            try:
                p2.close()
            except Exception:
                pass
        except Exception as e:
            print(f"[爬] {src} 失败：{str(e)[:100]}")
        time.sleep(1.5)

    try:
        browser.close()
    except Exception:
        pass
    try:
        pw.stop()
    except Exception:
        pass
    seen_titles = []
    for t in all_titles:
        t = re.sub(r"\s+", " ", t).strip()
        if t and t not in seen_titles:
            seen_titles.append(t)
    return out, seen_titles


def extract_titles(page):
    """
    10/12 诊断真相：中文平台的人【不给仓库地址】，标题/简介写的是中文功能描述
    （例：「Github一周热点134期」WebGPU效果组件库、PS5游戏搬到电脑、AI逆向软件）
    老贾每天干的活 = 看到中文描述 → 自己跑去 GitHub 搜出仓库。
    => 所以这里要抓的是【标题里的技术关键词】，交给下面的 reverse_search 反查仓库。
    """
    js = """() => {
      const sel = 'h1,h2,h3,h4,h5,.title,[class*=title],[class*=Title],[class*=desc],[class*=abstract]';
      return Array.from(document.querySelectorAll(sel))
        .map(e => (e.innerText||'').trim())
        .filter(t => t.length > 6 && t.length < 200);
    }"""
    try:
        return page.evaluate(js) or []
    except Exception:
        return []


# 标题里值得拿去 GitHub 反查的关键词
STOP = set("""如何 什么 为什么 怎么 使用 教程 入门 实战 保姆级 案例 分享 推荐 盘点 干货
教程 视频 课程 资源 汇总 合集 技巧 方法 源码 开源 项目 项目 工具 软件 应用 系统 平台
支持 拥有 打造 实现 完成 可以 让 使 用 帮 轻松 快速 免费 简单 强大 神器 神仙
教程 入门 实战 详细 全面 新 手 学 习 掌握 提升 增强 改进 优化 最佳 排行 版本
the and for you with this that from have are was your 使用 支持 实现 具有 可以 通过 一个 我们""".split())


def keywords_from_titles(titles, limit=20):
    """
    10/12 踩坑修正：第一版把中文短语也当关键词，抽出来 626 条全是碎片
    （「数已经达到了恐怖的」「直接把想法丢给它」），全查不到还白烧 GitHub 搜索API配额
    （未认证 10次/分钟）。=> 只保留【英文/技术词】，中文描述留作"线索"不作查询词。
    """
    TECH = set("""webgpu gpu ps5 xbox switch nintendo rag llm mcp ocr tts asr agent agents
    agentic ai llm4v comfyui remotion ffmpeg ollama vllm pytorch tensorflow transformers
    whisper sora midjourney stable-diffusion react vue angular svelte nextjs tailwind
    python golang rust typescript javascript java kotlin swift objective-c cpp csharp
    sdk api cli gui ide devops docker kubernetes terraform ansible prometheus grafana
    nginx redis postgres mysql mongodb kafka rabbitmq elasticsearch clickhouse
    vscode neovim vim obs ffmpeg davinci davinci-resolve premiere
    gpt chatgpt deepseek claude gemini llama qwen kimi grok copilot cursor windsurf
    nvidia cuda opencv numpy pandas pytorch huggingface ollama
    open-source opensource awesome self-hosted localhost
    vs5 ps4 xiaomi bytedance tencent alibaba
    ray tracing renderer shader compiler kernel inference training""".split())
    kws, seen_w = [], set()
    for t in titles:
        for m in re.finditer(r"\b([A-Za-z][A-Za-z0-9\+\#\.\-]{1,20})\b", t):
            w = m.group(1)
            wl = w.lower()
            if wl in seen_w or wl in STOP:
                continue
            # 判定：属于技术词表，或本身有大写缩写特征（WebGPU/PS5/RAG）
            is_tech = (wl in TECH) or bool(re.search(r"[A-Z]{2,}", w)) or bool(re.search(r"^[A-Z][a-z]+[A-Z]", w))
            if not is_tech:
                continue
            if len(kws) >= limit:
                return kws
            seen_w.add(wl)
            kws.append(w)
    return kws


def reverse_search(kw, per_page=6):
    """拿中文平台看到的关键词，去 GitHub Search API 反查仓库（这就是老贾每天人工干的那步）"""
    import urllib.request, urllib.parse
    queries = [f"{kw} in:name,description,readme stars:>300",
               f"{kw} stars:>300"]
    got = []
    for q in queries:
        url = ("https://api.github.com/search/repositories?q="
               + urllib.parse.quote(q) + f"&sort=stars&order=desc&per_page={per_page}")
        req = urllib.request.Request(url, headers={
            "User-Agent": "cn-radar", "Accept": "application/vnd.github+json"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                data = json.loads(r.read().decode("utf-8"))
        except Exception:
            continue
        for it in (data.get("items") or []):
            full = it.get("full_name")
            if full and full not in got:
                got.append(full)
        time.sleep(2.2)   # GitHub 搜索 API 未认证 10次/分钟，别打爆
        if got:
            break
    return got


def extract_repos(texts):
    """从正文里抽 {repo: [来源, 上下文]}"""
    found = {}
    for src, txt in texts:
        for m in RE_URL.finditer(txt):
            o, r = m.group(1), clean(m.group(2))
            if r.lower() in ("", "blob", "tree", "releases", "issues", "pulls", "wiki"):
                continue
            repo = f"{o}/{r}"
            found.setdefault(repo, {"src": set(), "ctx": ""})
            found[repo]["src"].add(src)
            if not found[repo]["ctx"]:
                s = max(0, m.start() - 120)
                found[repo]["ctx"] = txt[s:m.start() + 160].replace("\n", " ").strip()

        # 退一步：正文里没有完整 URL 时，抓 owner/repo 形态（要求 owner 小写且不含中文）
        for m in RE_SLASH.finditer(txt):
            o, r = m.group(1), clean(m.group(2))
            if "." in o or " " in o or BAD_TAIL.search(r):
                continue
            if o.lower() in RESERVED or r.lower() in RESERVED:
                continue
            if not o[0].isalpha():
                continue
            repo = f"{o}/{r}"
            found.setdefault(repo, {"src": set(), "ctx": ""})
            found[repo]["src"].add(src + "(猜)")
    return found


def read_ledger_seen():
    """从视频台账里抓已经讲过的项目（英文项目名 + owner/repo）"""
    seen = set()
    try:
        with open(LEDGER, "r", encoding="utf-8") as f:
            t = f.read()
    except Exception as e:
        print("[!] 读台账失败：", e)
        return seen
    for m in RE_URL.finditer(t):
        seen.add(f"{m.group(1)}/{clean(m.group(2))}".lower())
    # 台账里写成 `owner/repo` 的
    for m in RE_SLASH.finditer(t):
        o, r = m.group(1), clean(m.group(2))
        if "." in o or " " in o or BAD_TAIL.search(r):
            continue
        seen.add(f"{o}/{r}".lower())
    # 已经做过的集标题里提到的英文项目名
    for kw in ["video-use", "context-mode", "Pipecat", "open-webui", "Lemo-Opuscar",
               "lemo-opuscar", "Our Free Model", "OpenMontage", "Strata", "Typesafe",
               "mediaCrawler", "MediaCrawler"]:
        seen.add(kw.lower())
    return seen


def gh_api(repo):
    """GitHub API 实测一个仓库。老贾铁律：数字必须实测。"""
    import urllib.request, urllib.error
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}",
        headers={"User-Agent": "cn-radar", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"__error__": str(e)}


def score(d):
    """
    按老贾已验证的数据规律打分：
      - 第24集 Pipecat 1.6万星 → 数据全线上涨（老贾原话"数据慢慢变好"）
      - 第26集 Lemo-Opuscar 1853星 → 老贾看片说"还可以"
      ⇒ 星数不是唯一，能讲、有反差、刚建仓的都要得高分
    """
    s = 0
    stars = d.get("stargazers_count", 0)
    if stars >= 30000: s += 40
    elif stars >= 10000: s += 34
    elif stars >= 3000: s += 26
    elif stars >= 1000: s += 18
    elif stars >= 300: s += 8

    # 近3个月还在动 = 活的
    pushed = d.get("pushed_at", "")
    if pushed:
        try:
            from datetime import datetime as _dt
            days = (_dt.now() - _dt.strptime(pushed[:19], "%Y-%m-%dT%H:%M:%S")).days
            if days <= 30: s += 18
            elif days <= 90: s += 12
            elif days <= 180: s += 5
            else: s -= 10
        except Exception:
            pass

    # 新仓库有"刚上线"的故事感（第26集"九月底建的"就是钩子）
    created = d.get("created_at", "")[:10]
    if created:
        try:
            from datetime import datetime as _dt
            cd = (_dt.now() - _dt.strptime(created, "%Y-%m-%d")).days
            if cd <= 45: s += 16
            elif cd <= 120: s += 9
            elif cd > 1000: s -= 8
        except Exception:
            pass

    # issue 少 = 维护好
    oi = d.get("open_issues_count", 0) or 0
    if oi <= 10: s += 10
    elif oi >= 300: s -= 8

    if d.get("description"):
        s += 5
    if d.get("license") and d["license"].get("spdx_id") not in (None, "NOASSERTION"):
        s += 6
    for k in ("topics",):
        if d.get(k):
            s += min(len(d[k]), 6)
    return s


def main():
    print("=" * 60)
    print("中文开源项目雷达  cn-radar   " + datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 60)

    texts, titles = crawl()
    if not texts:
        print("[!] 一个源都没爬到，退出。")
        return

    print(f"\n[提] 抓到 {len(titles)} 条中文标题/摘要（前8条示例）")
    for t in titles[:8]:
        print("   ·", t[:80])

    seen = read_ledger_seen()
    print(f"\n[重] 台账里已讲过的 {len(seen)} 个，自动淘汰")

    # ---- 路线A：正文里直接有 github 链接（小众但准）
    repos = extract_repos(texts)
    print(f"[A] 正文里直接抓到的仓库名: {len(repos)} 个")

    # ---- 路线B（主力）：中文描述 → GitHub 反查仓库（老贾每天人工干的那步）
    kws = keywords_from_titles(titles)
    print(f"[B] 从中文标题抽出 {len(kws)} 个关键词，开始去 GitHub 反查…")
    hit = 0
    for i, kw in enumerate(kws, 1):
        got = reverse_search(kw)
        if got:
            hit += 1
            print(f"   {i}/{len(kws)} 「{kw}」→ {', '.join(got[:4])}")
        else:
            print(f"   {i}/{len(kws)} 「{kw}」→ 无")
        for g in got:
            if g.lower() in seen:
                continue
            repos.setdefault(g, {"src": set(), "ctx": ""})
            repos[g]["src"].add(f"反查:{kw}")
        time.sleep(6.5)   # GitHub 搜索API未认证 10次/分钟，必须限速
    print(f"\n[合] 命中 {hit} 个关键词，候选仓库共 {len(repos)} 个\n")

    rows = []
    for repo, info in repos.items():
        if repo.lower() in seen:
            print(f"  ✂ 跳过(讲过) {repo}")
            continue
        if NOISE.search(repo):
            continue
        d = gh_api(repo)
        if "__error__" in d:
            print(f"  ✂ API404  {repo}")
            continue
        if d.get("fork"):
            continue
        stars = d.get("stargazers_count", 0)
        if stars < 200:          # 太冷门，讲不出信息差
            continue
        # 硬门槛：死仓库直接淘汰（第一版捞到 gifi 就是 2017 年最后 push 的僵尸项目）
        pushed_at = (d.get("pushed_at") or "")[:10]
        try:
            from datetime import datetime as _dt
            idle = (_dt.now() - _dt.strptime(pushed_at, "%Y-%m-%d")).days
        except Exception:
            idle = 9999
        if idle > 180:
            print(f"  ✂ 跳过(停更{idle}天) {repo}")
            continue
        rows.append({
            "repo": repo, "stars": stars, "forks": d.get("forks_count", 0),
            "license": (d.get("license") or {}).get("spdx_id"),
            "created": (d.get("created_at") or "")[:10],
            "pushed": (d.get("pushed_at") or "")[:10],
            "open_issues": d.get("open_issues_count", 0),
            "lang": d.get("language"), "topics": d.get("topics", []),
            "desc": (d.get("description") or "")[:160],
            "src": sorted(info["src"]), "ctx": info["ctx"][:200],
            "score": score(d),
        })
        time.sleep(0.4)   # 别把 GitHub API 打爆（未认证 60次/小时）

    rows.sort(key=lambda r: -r["score"])
    seen_before = set()
    try:
        with open(HISTORY, "r", encoding="utf-8") as f:
            seen_before = set(json.load(f).get("pushed", []))
    except Exception:
        pass

    fresh = [r for r in rows if r["repo"] not in seen_before]
    fresh.sort(key=lambda r: -r["score"])

    print("\n" + "=" * 60)
    print(f"候选清单（{len(fresh)} 个新项目，按选题分排序）")
    print("=" * 60)
    for i, r in enumerate(fresh[:15], 1):
        print(f"\n{i}. {r['repo']}  评分 {r['score']}")
        print(f"   {r['stars']:,}★ / {r['forks']:,}fork / {r['license']} / {r['lang']}")
        print(f"   建仓 {r['created']} · 最后push {r['pushed']} · issue {r['open_issues']}")
        print(f"   讲什么：{r['desc']}")
        print(f"   从哪看见的：{'、'.join(r['src'])}")
        if r['topics']:
            print(f"   topics: {', '.join(r['topics'][:8])}")

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"generated": datetime.now().isoformat(timespec="seconds"),
                   "items": fresh}, f, ensure_ascii=False, indent=2)
    with open(HISTORY, "w", encoding="utf-8") as f:
        json.dump({"pushed": sorted(seen_before | {r["repo"] for r in fresh})}, f, ensure_ascii=False)
    print(f"\n[存] {OUT_JSON}")
    print("\n[提示] 老贾只要回「讲第N个」或「跳过」，剩下的交给小叮当。")


if __name__ == "__main__":
    main()
