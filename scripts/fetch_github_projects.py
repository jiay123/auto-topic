"""
09:00 GitHub 优质项目推荐
筛选条件：
  - 一周内创建或更新
  - stars 数量较高（综合排序）
  - 有人维护（15天内有提交）
  - 每天不重复（排除近30天已推送项目）
输出6个项目，每个带中文标签、简介。
"""
import requests
import os
import json
import random
from datetime import datetime, timedelta

def _get_sendkey():
    SENDKEY = os.environ.get("SENDKEY", "")
    if not SENDKEY:
        try:
            with open(os.path.join(os.path.dirname(__file__), "..", ".env")) as f:
                for line in f:
                    if line.startswith("SENDKEY="):
                        SENDKEY = line.strip().split("=", 1)[1]
                        break
        except:
            pass
    return SENDKEY

SENDKEY = _get_sendkey()


GH_TOKEN = os.environ.get("GH_TOKEN", "")
STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "state_github.json")

HEADERS = {"Accept": "application/vnd.github.v3+json", "User-Agent": "auto-topic-bot"}
if GH_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GH_TOKEN}"


def _read_sendkey():
    SENDKEY = os.environ.get("SENDKEY", "")
    if not SENDKEY:
        try:
            with open(os.path.join(os.path.dirname(__file__), "..", ".env")) as f:
                for line in f:
                    if line.startswith("SENDKEY="):
                        SENDKEY = line.strip().split("=", 1)[1]
                        break
        except:
            pass
    return SENDKEY


def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                return json.load(f)
    except:
        pass
    return {"pushed": [], "last_date": ""}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def is_active(repo):
    """检查项目是否有人在维护（15天内有更新）。"""
    push_date = repo.get("pushed_at", "") or repo.get("updated_at", "")
    if not push_date:
        return False
    try:
        push = datetime.strptime(push_date[:10], "%Y-%m-%d")
        return (datetime.now() - push).days <= 15
    except:
        return True


def search_github(query, per_page=10):
    url = f"https://api.github.com/search/repositories?q={requests.utils.quote(query)}&sort=stars&order=desc&per_page={per_page}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json().get("items", [])
        elif r.status_code == 403:
            print("GitHub API 限速，等待60秒...")
            time.sleep(60)
            return search_github(query, per_page)
    except Exception as e:
        print(f"搜索失败 ({query}): {e}")
    return []


def score_repo(repo):
    score = 0
    stars = repo["stargazers_count"]
    topics = repo.get("topics", [])
    desc = (repo.get("description") or "").lower()
    lang = repo.get("language") or ""

    # 星星评分
    if stars >= 10000:
        score += 5
    elif stars >= 5000:
        score += 4
    elif stars >= 1000:
        score += 3
    elif stars >= 500:
        score += 2
    else:
        score += 1

    # AI 相关性强加分
    ai_kw = ["ai", "llm", "gpt", "chatgpt", "machine-learning", "deep-learning",
             "neural", "nlp", "copilot", "claude", "gemini", "langchain", "rag",
             "embedding", "vector", "mistral", "ollama", "openai"]
    has_ai = any(t in topics or t in desc for t in ai_kw)
    if has_ai:
        score += 3

    # 中文支持
    cn_kw = ["chinese", "cn", "zh", "中文"]
    has_cn = any(t in topics for t in cn_kw)
    if has_cn:
        score += 2

    # 实用工具类
    tool_kw = ["cli", "tool", "app", "gui", "desktop", "extension"]
    if any(t in topics for t in tool_kw):
        score += 1

    # 编程语言加分
    popular_lang = ["python", "javascript", "typescript", "rust", "go"]
    if lang and lang.lower() in popular_lang:
        score += 1

    return score


def pick_top6(repos, exclude_names, seed=None):
    """从候选项目中选6个，优先高分，多样化。"""
    scored = []
    for r in repos:
        name = r["full_name"]
        if name in exclude_names:
            continue
        if not is_active(r):
            continue
        s = score_repo(r)
        s += random.uniform(0, 0.5)  # 加点随机性，避免每天都一样
        scored.append((s, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:6]]


def summarize_repo(repo):
    topics = repo.get("topics", [])
    desc = repo.get("description") or ""
    lang = repo.get("language") or ""

    parts = []
    if topics:
        parts.append("、".join(topics[:3]))
    if desc:
        parts.append(desc)
    result = "。".join(parts) if parts else "暂无简介"
    return result


def build_message(repos):
    now = datetime.now().strftime("%Y-%m-%d")
    weekday_map = {
        "Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
        "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"
    }
    weekday = weekday_map.get(datetime.now().strftime("%A"), "")
    title = f"【{weekday}】GitHub 优质项目推荐"

    lines = [
        f"## 🛠 GitHub 优质项目推荐 · {now}\n",
        "筛选条件：一周内活跃 · 星星多 · 有人维护 · 每天不重复\n",
        "---",
    ]

    for i, repo in enumerate(repos, 1):
        stars_k = f"{repo['stargazers_count'] / 1000:.1f}K" if repo["stargazers_count"] >= 1000 else str(repo["stargazers_count"])
        lang = repo.get("language") or "多语言"
        summary = summarize_repo(repo)

        lines.append(f"### {i}. {repo['full_name']}")
        lines.append(f"⭐ {stars_k}　🔧 {lang}")
        lines.append(f"📝 {summary}")
        lines.append(f"🔗 {repo['html_url']}")
        lines.append("")

    lines.append("---")
    lines.append("回复「写X」（如「写2」）我立刻为你写文章。")
    lines.append("不想写这些？回复「换」重新推荐。")
    return title, "\n".join(lines)


def send_wechat(title, content):
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
    print(f"抓取 GitHub 热门项目 ({today_str})...")

    state = load_state()

    # 如果是今天第一次跑，清空当天已推送
    if state.get("last_date") != today_str:
        state["pushed"] = []
        state["last_date"] = today_str

    exclude_names = set(state.get("pushed", []))

    # 多种搜索策略，确保覆盖面
    queries = [
        "stars:>500 pushed:>7days",            # 高星近期活跃
        "topic:ai stars:>200 pushed:>7days",   # AI赛道
        "topic:open-source stars:>300 pushed:>7days",  # 精品开源
        "topic:developer-tools stars:>200 pushed:>7days",  # 开发者工具
        "stars:>100 pushed:>3days",           # 3天内新热
        "topic:chatgpt OR topic:llm OR topic:ollama stars:>100 pushed:>7days",  # AI工具
    ]

    all_repos = []
    for q in queries:
        results = search_github(q, per_page=8)
        all_repos.extend(results)
        time.sleep(0.5)  # 避免太快触发限速

    # 去重
    seen = set()
    unique = []
    for r in all_repos:
        if r["full_name"] not in seen:
            seen.add(r["full_name"])
            unique.append(r)

    print(f"候选项目：{len(unique)} 个，筛选中...")
    picked = pick_top6(unique, exclude_names, seed=int(today_str.replace("-", "")))

    if not picked:
        send_wechat("GitHub 选题抓取失败", "今天没有找到合适的项目，明天再试。")
        return

    # 更新状态
    state["pushed"].extend([r["full_name"] for r in picked])
    state["pushed"] = state["pushed"][-30:]  # 只保留近30天
    save_state(state)

    # 保存供 11:00 脚本使用
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
                "updated": r.get("pushed_at", "")[:10] if r.get("pushed_at") else r.get("updated_at", "")[:10],
            } for r in picked],
            "date": today_str
        }, f)

    title, content = build_message(picked)
    send_wechat(title, content)
    print(f"推送完成：{len(picked)} 个项目")


if __name__ == "__main__":
    import time as _time
    time = _time
    import random as _random
    random = _random
    main()