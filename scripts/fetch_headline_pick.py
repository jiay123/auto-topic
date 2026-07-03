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

MORNING_STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "state_topics.json")


def load_morning_picks():
    try:
        filepath = MORNING_STATE_FILE
        if os.path.exists(filepath):
            with open(filepath) as f:
                state = json.load(f)
                return state.get("morning_picks", [])
    except:
        pass
    return []


def score_project(repo):
    score = 0
    topics_str = " ".join(repo.get("topics", [])) + " " + (repo.get("description") or "")
    if any(t in topics_str for t in ["ai", "llm", "gpt", "chat"]):
        score += 3
    if any(t in topics_str for t in ["chinese", "zh", "cn"]):
        score += 2
    if "tool" in topics_str or "cli" in topics_str:
        score += 1
    if repo.get("stars", 0) > 5000:
        score += 3
    elif repo.get("stars", 0) > 1000:
        score += 2
    else:
        score += 1
    if repo.get("description") and len(repo["description"]) > 30:
        score += 1
    return score


def why_recommend(repo):
    reasons = []
    desc = (repo.get("description") or "").lower()
    topics = repo.get("topics", [])
    stars = repo.get("stars", 0)

    if any(t in topics for t in ["ai", "llm", "gpt", "chat"]) or "ai" in desc:
        reasons.append("AI 赛道自带流量，读者最爱看")
    if any(t in topics for t in ["chinese", "cn", "zh"]):
        reasons.append("有中文支持，国内读者上手零门槛")
    if stars > 5000:
        reasons.append(f"万星项目口碑已认证，读者信任度高")
    if any(t in ["cli", "tool", "app"] for t in topics):
        reasons.append("实用工具类好写好读好转发")
    if any(t in ["python", "javascript", "typescript", "rust", "go"] for t in topics):
        reasons.append("开发者工具，读者基数大")

    if not reasons:
        reasons.append("有新鲜感的开源项目，适合做发现系列")

    return "；".join(reasons[:2])


def writing_angle(repo):
    desc = (repo.get("description") or "").lower()
    stars = repo.get("stars", 0)
    topics = repo.get("topics", [])

    if "ai" in desc or "llm" in desc or any(t in ["ai", "llm", "gpt"] for t in topics):
        return "AI 工具省钱/赚钱切入点"
    if stars > 5000:
        return "万星项目，制造信息差"
    if any(t in ["chinese", "cn", "zh"] for t in topics):
        return "国产/中文项目，读者亲切感"
    if any(t in ["cli", "tool"] for t in topics):
        return "实用神器，重点写使用体验"
    return "从解决痛点切入"


def build_message(project1, project2):
    title = "老贾，今天推荐这 2 个项目写公众号"

    lines = ["## 老贾！从今天 6 个选题里挑了 2 个最适合写文章的\n"]

    for idx, repo in enumerate([project1, project2], 1):
        stars_k = f"{repo['stars'] / 1000:.1f}K" if repo['stars'] >= 1000 else str(repo['stars'])
        desc = repo.get("description") or "暂无简介"
        reason = why_recommend(repo)
        angle = writing_angle(repo)

        lines.append(f"---")
        lines.append(f"### 推荐 {idx}：{repo['name']}")
        lines.append(f"星 {stars_k} · {repo.get('lang') or '多语言'}")
        lines.append(f"")
        lines.append(f"**项目简介：** {desc}")
        lines.append(f"")
        lines.append(f"**推荐理由：** {reason}")
        lines.append(f"")
        lines.append(f"**写作角度：** {angle}")
        lines.append(f"")
        lines.append(f"🔗 {repo['url']}")
        lines.append("")

    lines.append("---")
    lines.append("回复「写1」或「写2」我马上帮你写文章。")
    lines.append("不想写这两个？回复「换」我从剩下 4 个再挑。")

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
    print(f"头条精选 ({today_str})...")

    morning_picks = load_morning_picks()
    if not morning_picks or len(morning_picks) < 2:
        print(f"早上选题数据不足（{len(morning_picks) if morning_picks else 0} 条），跳过推送")
        send_to_wechat("头条精选失败", "今天早上 9:00 没有选题数据，无法精选。")
        return

    scored = [(score_project(r), r) for r in morning_picks]
    scored.sort(key=lambda x: x[0], reverse=True)

    project1 = scored[0][1]
    project2 = scored[1][1]

    print(f"精选 2 个：{project1['name']}、{project2['name']}")
    title, content = build_message(project1, project2)
    send_to_wechat(title, content)
    print("推送完成")


if __name__ == "__main__":
    main()
