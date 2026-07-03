"""
11:00 文章选题推荐
从 09:00 的 6 个项目里，选出 2 个最适合写公众号的。
重点：写清楚"为什么选这两个"。
"""
import requests
import os
import json
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


GITHUB_STATE = os.path.join(os.path.dirname(__file__), "..", "state_github_projects.json")
PICK_HISTORY = os.path.join(os.path.dirname(__file__), "..", "state_pick_history.json")  # 30天去重


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


def load_today_projects():
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        if os.path.exists(GITHUB_STATE):
            with open(GITHUB_STATE) as f:
                data = json.load(f)
                if data.get("date") == today:
                    return data.get("projects", [])
    except:
        pass
    return []


def load_pick_history():
    """加载30天已选项目记录。"""
    try:
        if os.path.exists(PICK_HISTORY):
            with open(PICK_HISTORY) as f:
                return json.load(f)
    except:
        pass
    return {"picked": [], "last_date": ""}


def save_pick_history(history, picked_names, today):
    """保存本次选题记录。"""
    history["picked"].extend(picked_names)
    # 只保留近30天
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    history["picked"] = [n for n in history["picked"] if n not in picked_names or True]
    history["picked"] = history["picked"][-60:]  # 保留稍多一点
    history["last_date"] = today


def score_for_writing(repo):
    """给项目评分，看适不适合写公众号。"""
    score = []
    stars = repo.get("stars", 0)
    topics = repo.get("topics", [])
    desc = repo.get("description", "").lower()
    name = repo.get("name", "").lower()

    # 1. 星星数（知名项目有天然流量）
    if stars >= 5000:
        score.append(("stars", 5, f"⭐ {stars//1000}K 星，知名度高，读者信任"))
    elif stars >= 1000:
        score.append(("stars", 4, f"⭐ {stars//1000}K 星，有一定口碑"))
    elif stars >= 200:
        score.append(("stars", 2, f"⭐ {stars} 星，小众但有潜力"))
    else:
        score.append(("stars", 0, f"⭐ {stars} 星，冷门题材"))

    # 2. AI 相关性（公众号流量密码）
    ai_kw = ["ai", "llm", "gpt", "chatgpt", "machine-learning", "deep-learning",
             "nlp", "copilot", "ollama", "openai", "claude", "gemini", "mistral",
             "langchain", "rag", "embedding", "vector", "agent"]
    has_ai = any(k in topics or k in desc for k in ai_kw)
    score.append(("ai", 3 if has_ai else 0, "🤖 AI相关，流量有保障" if has_ai else "非AI项目"))

    # 3. 实用工具属性（好写好读）
    tool_kw = ["cli", "tool", "app", "gui", "desktop", "extension", "plugin"]
    is_tool = any(k in topics for k in tool_kw)

    # 4. 有截图/演示（文章配图容易）
    demo_kw = ["demo", "screenshot", "preview", "playground", "web", "ui"]
    has_demo = any(k in topics or k in desc or k in name for k in demo_kw)

    # 5. 中文友好（老贾读者门槛低）
    cn_kw = ["chinese", "cn", "zh", "中文"]
    is_cn = any(k in topics for k in cn_kw)
    score.append(("cn", 2 if is_cn else 0, "🇨🇳 中文友好，读者上手零门槛" if is_cn else "英文为主"))

    # 6. 上手难度（老贾不会写代码，越简单越好）
    hard_lang = ["c++", "c", "java", "rust", "go"]  # 相对难
    easy_lang = ["python", "javascript", "typescript", "shell"]  # 相对简单
    lang = (repo.get("lang") or "").lower()
    if lang in hard_lang:
        score.append(("easy", -1, f"⚠️ {lang} 实现，代码部分可能需要简化"))
    elif lang in easy_lang:
        score.append(("easy", 1, f"✅ {lang} 实现，代码示例友好"))

    # 综合评分
    total = sum(s for _, s, _ in score)
    return total, score


def why_this_project(repo, score_detail, rank):
    """生成推荐理由。"""
    stars = repo.get("stars", 0)
    topics = repo.get("topics", [])
    desc = repo.get("description", "")
    name = repo.get("name", "")

    reasons = []

    # 看哪个维度得分高
    for _, pts, reason in score_detail:
        if pts >= 3:
            reasons.append(reason)

    # 根据 rank 给不同策略
    if rank == 0:
        # 第一推荐：稳选
        if stars >= 3000:
            reasons.append("🏆 选题稳妥，公众号已有相似爆款可参考")
        elif any(k in topics for k in ["ai", "llm", "gpt"]):
            reasons.append("🔥 蹭 AI 热度，流量有保障")
        else:
            reasons.append("🔄 有信息差：很多人听说过，但没深度用过")
    else:
        # 第二推荐：差异化（和第一选形成对比）
        if stars >= 1000:
            reasons.append("💡 同样是热门，但角度不同可选")
        else:
            reasons.append("🎯 小众精品，写出来有独特价值")

    return "；".join(reasons[:3])


def writing_angle(repo):
    """推荐写作角度。"""
    topics = repo.get("topics", [])
    stars = repo.get("stars", 0)
    desc = repo.get("description", "").lower()
    name = repo.get("name", "")

    ai_kw = ["ai", "llm", "gpt", "chatgpt", "machine-learning", "ollama", "openai"]
    tool_kw = ["cli", "tool", "app", "gui"]
    has_ai = any(k in topics for k in ai_kw)
    is_tool = any(k in topics for k in tool_kw)

    if has_ai and stars >= 3000:
        return "深度测评 + 省钱替代方案（对比同类付费产品）"
    elif has_ai:
        return "AI 工具发现类：这是什么、能做什么、如何上手"
    elif is_tool:
        return "神器推荐：5分钟安装、解决什么问题、适合谁用"
    elif stars >= 5000:
        return "万星项目解读：为什么这么多人用？值得吗？"
    else:
        return "小众宝藏项目推荐：藏得够深，知道的人不多"


def build_message(best1, best2):
    now = datetime.now().strftime("%Y-%m-%d")
    title = f"📝 今日文章选题推荐 · {now}"

    lines = [
        f"## 📝 今日文章选题推荐\n",
        "以下 2 个项目是今天最值得写的：\n",
    ]

    for rank, repo in enumerate([best1, best2], 0):
        stars = repo.get("stars", 0)
        stars_k = f"{stars//1000}K" if stars >= 1000 else str(stars)

        total_score, score_detail = score_for_writing(repo)
        why = why_this_project(repo, score_detail, rank)
        angle = writing_angle(repo)

        lines.append(f"---")
        lines.append(f"### 🥇 推荐 {rank+1}：{repo['name']}")
        lines.append(f"⭐ {stars_k}　🔧 {repo.get('lang', '多语言')}")
        lines.append("")
        lines.append(f"**简介：** {repo.get('description', '暂无')}")
        lines.append("")
        lines.append(f"**为什么选这个：**")
        lines.append(f"{why}")
        lines.append("")
        lines.append(f"**推荐写作角度：**")
        lines.append(f"{angle}")
        lines.append("")
        lines.append(f"🔗 {repo.get('url', '')}")
        lines.append("")

    lines.append("---")
    lines.append("回复「写1」或「写2」，我立刻为你写文章。")
    lines.append("不想写这两个？回复「换」，我重新选。")
    lines.append("")
    lines.append("💡 小叮当提示：选项目时，优先选你熟悉、喜欢、有话说的，写出来的文章更有温度。")

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
    print("正在选题...")
    today = datetime.now().strftime("%Y-%m-%d")
    projects = load_today_projects()

    if not projects:
        print("没有今日选题数据（可能是 09:00 脚本还没跑），跳过")
        send_wechat("选题失败", "早上 9:00 没有抓到 GitHub 项目，无法选题。\n请检查 09:00 推送是否成功。")
        return

    # 30天去重
    history = load_pick_history()
    exclude = set(history.get("picked", []))
    filtered = [p for p in projects if p.get("name") not in exclude]
    if len(filtered) < 2:
        filtered = projects  # 去重后不足2个就用全部

    # 评分排序
    scored = [(score_for_writing(p)[0], p) for p in filtered]
    scored.sort(key=lambda x: x[0], reverse=True)

    best1 = scored[0][1]
    best2 = scored[1][1]

    # 保存选题历史
    saved_history = load_pick_history()
    saved_history["picked"].extend([best1["name"], best2["name"]])
    saved_history["picked"] = saved_history["picked"][-60:]
    saved_history["last_date"] = today
    try:
        with open(PICK_HISTORY, "w") as f:
            json.dump(saved_history, f)
    except:
        pass

    print(f"精选：{best1['name']}、{best2['name']}")
    title, content = build_message(best1, best2)
    send_wechat(title, content)
    print("推送完成")


if __name__ == "__main__":
    main()