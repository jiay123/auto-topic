"""
08:00 AI 资讯热点
来源：量子位、机器之心、Hacker News、微博AI热搜、Product Hunt
每天15条，每条带100-150字摘要。
"""
import os
import requests
import re
import concurrent.futures
import time
from datetime import datetime

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



RSS_SOURCES = [
    {"name": "量子位", "url": "https://www.qbitai.com/feed", "lang": "zh"},
    {"name": "机器之心", "url": "https://rsshub.app/jiqizhixin", "lang": "zh"},
]

HN_API = "https://hn.algolia.com/api/v1/search?query=AI+OR+artificial+intelligence+OR+GPT+OR+LLM&tags=story&hitsPerPage=30"
PRODUCT_HUNT = "https://api.producthunt.com/v1/posts?search[ategories][]=artificial-intelligence&per_page=20"


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


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Firefox/120.0"
}


def fetch_summary(session, url, timeout=10):
    """抓取文章正文，提炼100-150字摘要。"""
    try:
        r = session.get(url, headers=HEADERS, timeout=timeout)
        r.encoding = "utf-8"
        # 提取段落
        paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", r.text, re.DOTALL)
        for p in paragraphs:
            clean = re.sub(r"<[^>]+>", "", p).strip()
            if 40 < len(clean) < 600:
                return clean[:150]
        # 备用：meta description
        desc = re.findall(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', r.text, re.I)
        if desc:
            return desc[0][:150]
        return ""
    except:
        return ""


def translate_title(title):
    """简单翻译 Hacker News 英文标题为中文。"""
    trans_map = {
        "OpenAI": "OpenAI", "Anthropic": "Anthropic", "Google": "谷歌",
        "Meta": "Meta", "Microsoft": "微软", "Apple": "苹果",
        "Amazon": "亚马逊", "Tesla": "特斯拉", "Nvidia": "英伟达",
        "GPT": "GPT", "LLM": "大模型", "AI": "AI", "ML": "机器学习",
        "model": "模型", "agent": "智能体", "chatbot": "聊天机器人",
        "neural": "神经网络", "deep learning": "深度学习",
        "launch": "发布", "release": "发布", "announce": "宣布",
        "introduces": "推出", "new": "新", "show": "展示",
        "study": "研究", "research": "研究", "发现": "发现",
        "warning": "警告", "risk": "风险", "safety": "安全",
    }
    result = title
    for en, zh in trans_map.items():
        result = re.sub(rf'\b{re.escape(en)}\b', zh, result, flags=re.I)
    return result


def fetch_qbitai():
    """抓量子位 RSS，只能拿到标题和链接，摘要用fetch_summary补。"""
    articles = []
    try:
        r = requests.get(RSS_SOURCES[0]["url"], headers=HEADERS, timeout=15)
        r.encoding = "utf-8"
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r.text.encode("utf-8"))
        for item in root.findall(".//item")[:10]:
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            pubdate = item.findtext("pubDate", "")[:16]
            source = "量子位"
            if title and link:
                articles.append({"title": title, "url": link, "source": source, "pubdate": pubdate})
    except Exception as e:
        print(f"量子位抓取失败: {e}")
    return articles


def fetch_rszhixin():
    """抓机器之心 RSS。"""
    articles = []
    try:
        r = requests.get(RSS_SOURCES[1]["url"], headers=HEADERS, timeout=15)
        r.encoding = "utf-8"
        import xml.etree.ElementTree as ET
        root = ET.fromstring(r.text.encode("utf-8"))
        for item in root.findall(".//item")[:8]:
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            if title and link:
                articles.append({"title": title, "url": link, "source": "机器之心", "pubdate": ""})
    except Exception as e:
        print(f"机器之心抓取失败: {e}")
    return articles


def fetch_hackernews():
    """抓 Hacker News AI 相关文章，标题翻译成中文。"""
    articles = []
    try:
        r = requests.get(HN_API, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            for hit in data.get("hits", [])[:15]:
                raw_title = hit.get("title", "")
                title = translate_title(raw_title)
                url = hit.get("url", "") or f"https://news.ycombinator.com/item?id={hit.get('objectID','')}"
                if title:
                    articles.append({"title": title, "url": url, "source": "Hacker News", "pubdate": ""})
    except Exception as e:
        print(f"Hacker News 抓取失败: {e}")
    return articles


def fetch_producthunt():
    """抓 Product Hunt AI 类新产品。"""
    articles = []
    try:
        token = os.environ.get("PH_TOKEN", "")
        if not token:
            print("未配置 PH_TOKEN，跳过 Product Hunt")
            return []
        ph_headers = {**HEADERS, "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        r = requests.get(PRODUCT_HUNT, headers=ph_headers, timeout=15)
        if r.status_code == 200:
            for post in r.json().get("posts", [])[:8]:
                name = post.get("name", "")
                tagline = post.get("tagline", "")
                url = f"https://producthunt.com{post.get('url', '')}"
                if name:
                    title = f"{name}：{tagline}" if tagline else name
                    articles.append({"title": title, "url": url, "source": "Product Hunt", "pubdate": ""})
    except Exception as e:
        print(f"Product Hunt 抓取失败: {e}")
    return articles


def enrich_with_summaries(articles):
    """并发抓每条的摘要。"""
    session = requests.Session()
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(fetch_summary, session, a["url"]): a for a in articles}
        for f in concurrent.futures.as_completed(futures):
            article = futures[f]
            try:
                article["summary"] = f.result()
            except:
                article["summary"] = ""
    return articles


def build_message(articles):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    weekday_map = {
        "Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
        "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"
    }
    weekday = weekday_map.get(datetime.now().strftime("%A"), "")
    title = f"【{weekday}】AI 热点速递 · {now}"

    lines = [
        f"## 📰 AI 热点速递 · {now}\n",
        f"来源：量子位 · 机器之心 · Hacker News · Product Hunt",
        f"整理：小叮当\n",
    ]

    # 按来源分组显示，来源标签突出
    sources_order = ["量子位", "机器之心", "Hacker News", "Product Hunt"]
    by_source = {}
    for a in articles:
        by_source.setdefault(a["source"], []).append(a)

    idx = 1
    for src in sources_order:
        if src not in by_source:
            continue
        for a in by_source[src]:
            emoji_map = {"量子位": "🔬", "机器之心": "🤖", "Hacker News": "🌐", "Product Hunt": "🚀"}
            emoji = emoji_map.get(src, "📌")
            lines.append(f"### {emoji} {a['title']}")
            if a.get("pubdate"):
                lines.append(f"**时间：** {a['pubdate']}")
            summary = a.get("summary", "").strip()
            if summary:
                lines.append(f"{summary}")
            lines.append(f"来源：[{src}]({a['url']})")
            lines.append("")
            idx += 1

    lines.append("---")
    lines.append("以上资讯由小叮当整理，每条均附摘要。如有帮助，点个赞 👍")
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
    print("开始抓取 AI 资讯热点...")
    all_articles = []

    # 并行抓国内来源
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
        f1 = ex.submit(fetch_qbitai)
        f2 = ex.submit(fetch_rszhixin)
        all_articles += f1.result()
        all_articles += f2.result()

    # 抓国际来源
    all_articles += fetch_hackernews()
    all_articles += fetch_producthunt()

    print(f"抓取到 {len(all_articles)} 条标题，开始抓摘要...")
    # 打乱顺序，让每天来源分布不同
    import random
    random.seed(datetime.now().strftime("%Y%m%d"))
    random.shuffle(all_articles)

    # 取15条
    all_articles = all_articles[:15]
    articles_with_summary = enrich_with_summaries(all_articles)

    title, content = build_message(articles_with_summary)
    send_wechat(title, content)
    print(f"推送完成，共 {len(articles_with_summary)} 条")


if __name__ == "__main__":
    import os as _os
    os = _os
    main()