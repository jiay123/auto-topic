"""
08:00 GitHub 项目推荐 + 智能选文
根据老贾37篇文章数据，匹配最适合写的开源项目。
只推2-3个，明确推荐最好写的那个。
"""
import requests
import os
import json
import random
import time
from datetime import datetime, timedelta

today = datetime.now()
DATE_7D = (today - timedelta(days=7)).strftime("%Y-%m-%d")
DATE_3D = (today - timedelta(days=3)).strftime("%Y-%m-%d")

SENDKEY = os.environ.get("SENDKEY", "")
GH_TOKEN = os.environ.get("GH_TOKEN", "")
STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "state_github.json")
ARTICLE_DATA = os.path.join(os.path.dirname(__file__), "..", "article_data.json")

HEADERS = {"Accept": "application/vnd.github.v3+json", "User-Agent": "auto-topic-bot"}
if GH_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GH_TOKEN}"

# 老贾爆款规律（来自37篇文章数据分析）
PATTERNS = {
    "省钱免费": {"keywords": ["free", "替代", "alternative", "省钱", "免费", "省", "open-source"], "score": 6, "reason": "省钱/免费类你之前转发率11-21%，非常稳"},
    "大厂热度": {"keywords": ["google", "microsoft", "apple", "openai", "meta", "nvidia", "deepseek", "gemini", "claude", "anthropic"], "score": 4, "reason": "蹭大厂热度，你之前最高播放8830"},
    "搞钱情绪": {"keywords": ["money", "job", "career", "印钞", "赚钱", "搞钱", "慌", "被开除", "裁员", "省"], "score": 3, "reason": "搞钱/情绪类转发率14-17%，最高播放15611"},
    "AI相关": {"keywords": ["ai", "llm", "gpt", "chatgpt", "machine-learning", "ollama", "openai", "claude", "gemini", "langchain", "rag", "agent"], "score": 3, "reason": "AI类流量有保障，稳定1000+"},
    "直接能用": {"keywords": ["web", "online", "saas", "app", "gui", "browser", "extension"], "score": 2, "reason": "在线可用不用安装，读者门槛低"},
    "中文友好": {"keywords": ["chinese", "cn", "zh", "中文"], "score": 2, "reason": "支持中文，读者上手快"},
    "安装复杂": {"keywords": ["docker", "kubernetes", "helm", "terraform"], "score": -5, "reason": "安装复杂劝退读者"},
}

def load_article_data():
    """读取老贾的文章数据，用于匹配推荐理由。"""
    try:
        if os.path.exists(ARTICLE_DATA):
            with open(ARTICLE_DATA, encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return []

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

    # 星星分
    if stars >= 10000: score += 5
    elif stars >= 5000: score += 4
    elif stars >= 1000: score += 3
    elif stars >= 500: score += 2
    else: score += 1

    # 匹配爆款规律
    for pattern_name, pattern in PATTERNS.items():
        if any(k in desc or k in topics or k in name for k in pattern["keywords"]):
            score += pattern["score"]
            if pattern["score"] > 0:
                match_reasons.append(pattern["reason"])

    # 编程语言友好度
    easy_lang = ["python", "javascript", "typescript", "shell"]
    hard_lang = ["c++", "c", "java", "rust", "go"]
    if lang.lower() in easy_lang:
        score += 1
    elif lang.lower() in hard_lang:
        score -= 1

    return score, match_reasons

def pick_top_projects(repos, articles, count=5):
    scored = []
    for r in repos:
        name = r["full_name"]
        s, reasons = score_repo(r, articles)
        s += random.uniform(0, 0.3)
        scored.append((s, r, reasons))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:count]

def translate_desc(desc):
    """把英文描述转成简短中文说明。"""
    if not desc:
        return "暂无简介"
    desc_lower = desc.lower()
    if "ai" in desc_lower or "llm" in desc_lower or "gpt" in desc_lower:
        return f"AI工具：{desc[:60]}..."
    elif "free" in desc_lower or "open" in desc_lower:
        return f"免费开源：{desc[:60]}..."
    elif "tool" in desc_lower or "cli" in desc_lower or "library" in desc_lower:
        return f"开发工具：{desc[:60]}..."
    else:
        return desc[:80]

def build_message(picked, best, articles):
    date_cn = f"{today.year}年{today.month}月{today.day}日"
    weekday_map = {"Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
                   "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"}
    weekday = weekday_map.get(today.strftime("%A"), "")
    title = f"老贾，今天是{date_cn}早上好，今日开源项目推荐"

    lines = [
        f"老贾，今天是{date_cn}（{weekday}）早上好。今天推荐5个开源项目：\n",
    ]

    # 最佳推荐（强烈建议写这篇）
    best_repo = best[1]
    best_reasons = best[2]
    stars_k = f"{best_repo['stargazers_count']/1000:.1f}K" if best_repo['stargazers_count'] >= 1000 else str(best_repo['stargazers_count'])
    lang = best_repo.get("language") or "多语言"

    lines.append("🏆 最佳推荐（建议写这篇）")
    lines.append(f"")
    lines.append(f"项目：{best_repo['full_name']}")
    lines.append(f"星数：⭐ {stars_k}　语言：{lang}")
    lines.append(f"简介：{translate_desc(best_repo.get('description', ''))}")
    lines.append(f"🔗 {best_repo['html_url']}")
    lines.append(f"")
    lines.append(f"为什么推荐：")
    for r in best_reasons[:3]:
        lines.append(f"  ✅ {r}")
    if any(k in (best_repo.get("description") or "").lower() or k in best_repo.get("topics", []) or k in best_repo.get("name", "").lower() for k in ["free", "省钱", "免费", "替代", "alternative"]):
        lines.append(f"  📊 你之前写省钱类最高891播放、155转发")
    if any(k in (best_repo.get("description") or "").lower() for k in ["money", "job", "印钞", "赚钱", "搞钱"]):
        lines.append(f"  📊 你之前写搞钱类最高5617播放、811转发")
    lines.append(f"")

    # 全部5个项目一览
    lines.append("---")
    lines.append("今日全部推荐（共5个）：\n")
    for i, (score, repo, reasons) in enumerate(picked, 1):
        stars_k = f"{repo['stargazers_count']/1000:.1f}K" if repo['stargazers_count'] >= 1000 else str(repo['stargazers_count'])
        lang = repo.get("language") or "多语言"
        is_best = "🏆 " if repo["full_name"] == best_repo["full_name"] else ""
        lines.append(f"{is_best}{i}. {repo['full_name']}（⭐ {stars_k} · {lang}）")
        lines.append(f"   {translate_desc(repo.get('description', ''))}")
        if repo["full_name"] == best_repo["full_name"]:
            lines.append(f"   ← 最推荐写这篇")
        lines.append(f"")

    lines.append("---")
    lines.append("回复「写」我就写推荐的那篇。")
    lines.append("想换一个？回复编号（如「写3」）我就写第3个。")

    return title, "\n".join(lines)

def send_wechat(title, content):
    if not SENDKEY:
        print("SENDKEY 未设定")
        return
    url = f"https://sctapi.ftqq.com/{SENDKEY}.send"
    try:
        r = requests.post(url, data={"title": title, "desp": content}, timeout=10)
        print("推送结果:", r.text[:200])
    except Exception as e:
        print("推送失败:", e)

def main():
    print(f"抓取 GitHub 热门项目 ({today.strftime('%Y-%m-%d')})...")

    articles = load_article_data()
    print(f"已加载 {len(articles)} 条文章数据")

    queries = [
        f"stars:>500 pushed:>{DATE_7D}",
        f"topic:ai stars:>200 pushed:>{DATE_7D}",
        f"topic:open-source stars:>300 pushed:>{DATE_7D}",
        f"stars:>100 pushed:>{DATE_3D}",
    ]

    # 循环搜索：凑满5个高分项目
    all_queries = queries[:]
    all_repos = []
    max_rounds = 3
    for round_num in range(max_rounds):
        if not all_queries:
            break
        q = all_queries.pop(0)
        results = search_github(q, per_page=12)
        all_repos.extend(results)
        time.sleep(0.5)

        # 去重+评分
        seen = set()
        unique = []
        for r in all_repos:
            if r["full_name"] not in seen:
                seen.add(r["full_name"])
                unique.append(r)

        picked = pick_top_projects(unique, articles, count=5)
        print(f"  第{round_num+1}轮：{len(results)} 个新项目，累计{len(unique)} 个唯一，已凑够{len(picked)} 个高分")

        if len(picked) >= 5:
            print("已凑满5个项目")
            break

    if not picked:
        send_wechat("老贾，今天没找到合适的项目", "GitHub 上没有匹配的项目，明天再试。")
        return

    # 最佳推荐 = 分数最高的
    best = picked[0]
    second = picked[1] if len(picked) > 1 else None

    # 保存供下游脚本
    github_state_file = os.path.join(os.path.dirname(__file__), "..", "state_github_projects.json")
    with open(github_state_file, "w") as f:
        json.dump({
            "projects": [{
                "name": r["full_name"],
                "stars": r["stargazers_count"],
                "lang": r.get("language", ""),
                "description": r.get("description") or "",
                "url": r["html_url"],
                "topics": r.get("topics", []),
                "updated": (r.get("pushed_at") or r.get("updated_at") or "")[:10],
            } for score, r, reasons in picked],
            "date": today.strftime("%Y-%m-%d"),
            "best_pick": best[1]["full_name"],
        }, f)

    title, content = build_message(picked, best, articles)
    send_wechat(title, content)
    print(f"推送完成：{len(picked)} 个项目")

if __name__ == "__main__":
    main()
