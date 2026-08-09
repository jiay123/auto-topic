"""
07:00 AI 资讯热点（昨天+今天）
覆盖：OpenAI / 谷歌 / 千问 / 通义 / Kimi / 豆包 / 国内AI大模型动态
数据源：量子位、IT之家、InfoQ（备用中文源）
每天8-12条，每条带100-150字摘要，7天自动去重。
"""
import requests
import re
import os
import sys
import json
import subprocess
import concurrent.futures
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

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

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
STATE_FILE = os.path.join(BASE_DIR, "state_news_dedup.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# --- 日期范围：昨天 + 今天 ---
today = datetime.now().strftime("%Y-%m-%d")
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

def _git(*args):
    try:
        subprocess.run(["git", "-C", BASE_DIR] + list(args), check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def load_dedup():
    # 云端每次是全新 checkout，先尝试从远端拉取最新的去重状态
    if os.environ.get("GITHUB_ACTIONS") == "true":
        _git("pull", "--ff-only")
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                data = json.load(f)
                return set(data.get("titles", []))
    except:
        pass
    return set()

def save_dedup(titles):
    today_titles = list(titles)[-200:]
    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"titles": today_titles, "date": today}, f, ensure_ascii=False)
    except:
        pass
    # 云端把去重状态提交回仓库，保证下次运行能去重（不重复推送）
    if os.environ.get("GITHUB_ACTIONS") == "true":
        _git("config", "user.email", "bot@auto-topic.local")
        _git("config", "user.name", "auto-topic-bot")
        _git("add", "state_news_dedup.json")
        _git("commit", "-m", f"chore: 更新新闻去重状态 {today}")
        _git("push")

def is_recent(pubdate_str):
    """判断发布时间是否在昨天或今天（按 UTC）。"""
    if not pubdate_str:
        return True
    try:
        dt = parsedate_to_datetime(pubdate_str)
    except Exception:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d") in [today, yesterday]

def fetch_summary(url, timeout=8):
    """抓取正文，提取100-150字摘要。"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.encoding = "utf-8"
        paras = re.findall(r"<p[^>]*>(.*?)</p>", r.text, re.DOTALL)
        for p in paras:
            clean = re.sub(r"<[^>]+>", "", p).strip()
            if 40 < len(clean) < 600:
                return clean[:150]
        desc = re.findall(r'<meta[^>]+(?:name=["\']description["\']|property=["\']og:description["\'])[^>]+content=["\']([^"\']+)["\']', r.text, re.I)
        if desc:
            return desc[0][:150]
    except:
        pass
    return ""

# --- 数据源 ---
AI_KEYWORDS = ["AI", "大模型", "GPT", "ChatGPT", "人工智能", "DeepSeek", "豆包", "Kimi",
               "千问", "通义", "OpenAI", "Claude", "Gemini", "文心", "讯飞", "智谱",
               "Anthropic", "英伟达", "GPU", "芯片", "机器人", "智能体", "Agent", "Sora"]

RSS_FEEDS = [
    {"name": "量子位", "url": "https://www.qbitai.com/feed", "limit": 8},
    {"name": "IT之家", "url": "https://www.ithome.com/rss/", "limit": 15, "keywords": AI_KEYWORDS},
    {"name": "InfoQ", "url": "https://www.infoq.cn/feed", "limit": 8, "keywords": AI_KEYWORDS},
]

def fetch_rss(source, dedup_titles):
    articles = []
    import xml.etree.ElementTree as ET
    try:
        r = requests.get(source["url"], headers=HEADERS, timeout=15)
        r.encoding = "utf-8"
        root = ET.fromstring(r.text.encode("utf-8"))
        keywords = source.get("keywords")
        for item in root.findall(".//item")[:source["limit"]]:
            title = item.findtext("title", "").strip()
            if not title or title in dedup_titles:
                continue
            if keywords and not any(k in title for k in keywords):
                continue
            link = item.findtext("link", "").strip()
            pubdate = item.findtext("pubDate", "")[:22].strip()
            if not is_recent(pubdate):
                continue
            articles.append({"title": title, "url": link, "source": source["name"], "pubdate": pubdate[:16]})
    except Exception as e:
        print(f"{source['name']} 抓取失败: {e}")
    return articles

def enrich_summaries(articles):
    """并发抓摘要。"""
    session = requests.Session()
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(fetch_summary, a["url"]): a for a in articles}
        for f in concurrent.futures.as_completed(futures):
            article = futures[f]
            try:
                article["summary"] = f.result()
            except:
                article["summary"] = ""
    return articles

def build_message(articles):
    weekday_map = {
        "Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
        "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"
    }
    weekday = weekday_map.get(datetime.now().strftime("%A"), "")
    date_cn = f"{datetime.now().year}年{datetime.now().month}月{datetime.now().day}日"
    title = f"老贾，今天是{date_cn}早上好，AI 热点速递"

    lines = [
        f"老贾，今天是{date_cn}（{weekday}）早上好。以下是今天和昨天的 AI 资讯热点：\n",
        f"📅 内容范围：{yesterday} ~ {today}（昨天+今天）",
        "来源：量子位 · IT之家 · InfoQ",
        "筛选：仅保留含 AI / 大模型 / 国内大厂动态 的当天资讯",
        "",
        "---",
    ]

    emoji_map = {"量子位": "🔬", "IT之家": "💻", "InfoQ": "📡"}
    idx = 1
    for a in articles:
        emoji = emoji_map.get(a["source"], "📌")
        lines.append(f"### {emoji} {a['title']}")
        if a.get("pubdate"):
            lines.append(f"**时间：** {a['pubdate']}")
        summary = a.get("summary", "").strip()
        if summary:
            lines.append(summary)
        lines.append(f"来源：[{a['source']}]({a['url']})")
        lines.append("")
        idx += 1

    lines.append("---")
    lines.append("以上资讯由小叮当整理，每条均附摘要。点个赞 👍 支持一下")
    return title, "\n".join(lines)

def send_wechat(title, content):
    if not SENDKEY:
        print("SENDKEY 未设定，无法推送")
        return
    url = f"https://sctapi.ftqq.com/{SENDKEY}.send"
    try:
        r = requests.post(url, data={"title": title, "desp": content}, timeout=10)
        print(r.text[:200])
    except Exception as e:
        print(f"推送失败: {e}")

def main():
    print(f"抓取AI资讯热点 ({yesterday} 至 {today})...")

    dedup_titles = load_dedup()
    all_articles = []

    # 1. 并行抓RSS
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        futures = [ex.submit(fetch_rss, src, dedup_titles) for src in RSS_FEEDS]
        for f in concurrent.futures.as_completed(futures):
            all_articles.extend(f.result())

    # 去重（同标题）
    seen = set()
    unique = []
    for a in all_articles:
        if a["title"] not in seen:
            seen.add(a["title"])
            seen.update(dedup_titles)
            unique.append(a)

    # 取8-12条
    unique = unique[:12]

    # 并发抓摘要
    articles = enrich_summaries(unique)

    # 更新去重记录
    save_dedup(seen)

    title, content = build_message(articles)
    send_wechat(title, content)
    print(f"推送完成：{len(articles)} 条")

if __name__ == "__main__":
    main()