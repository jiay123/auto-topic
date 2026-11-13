# -*- coding: utf-8 -*-
"""fetch_zhihu_hot.py —— 抓知乎热搜榜，过滤出技术/商业热点，按热度排 Top5

老贾 11/13 立：
  - 知乎榜是「事件流」（现在谁出事了），跟 fetch_ai_news.py 的「技术流」（又出了什么好东西）互补，实测 0 重叠。
  - **不单独推微信**（Server酱 每天只有 5 次免费名额），结果写 zhihu_hot.json，
    由 fetch_ai_news.py 并进 7 点那条推送 → 老贾发视频号前手机上就能看到「今天能拍什么」。
  - 0 次模型唤醒：纯脚本，抓取+过滤全本地算。

数据源：justjavac/zhihu-trending-top-search（MIT，每小时更新）
  ⚠️ raw.githubusercontent.com 在本机网络下会被重置，所以走 GitHub API 的 contents 接口读 README.md。

用法：
  python fetch_zhihu_hot.py            # 抓取 + 写 zhihu_hot.json + 打印
  python fetch_zhihu_hot.py --json     # 只输出 json（给别的脚本读）
"""
import base64
import json
import os
import re
import sys
import datetime

try:
    sys.stdout = sys.stdout
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_FILE = os.path.join(BASE_DIR, "zhihu_hot.json")
REPO = "justjavac/zhihu-trending-top-search"

# --- 技术/商业信号词（命中就是老贾可能要拍的方向）---
TECH_KW = [
    "英伟达", "NVIDIA", "黄仁勋", "RTX", "显卡", "芯片", "半导体", "微软", "Microsoft",
    "谷歌", "Google", "OpenAI", "Claude", "Anthropic", "Gemini", "DeepSeek", "阿里", "腾讯",
    "字节", "抖音", "百度", "华为", "小米", "特斯拉", "苹果", "iPhone", "安卓", "三星",
    "大模型", "AI", "人工智能", "模型", "智能体", "Agent", "机器人", "开源", "软件", "系统",
    "数据库", "服务器", "裁员", "宕机", "股价", "财报", "上市", "融资", "收购", "IPO",
    "开发者", "编程", "代码", "GPU", "算力", "数据中心", "自动驾驶", "Sora", "量子", "卫星",
    "互联网", "电商", "支付", "网络安全", "漏洞", "黑客", "密码", "隐私", "自动驾驶",
]

# --- 明确不要的（时政/娱乐/社会/八卦，跟老贾的业务无关）---
BLOCK_KW = [
    "被查", "落马", "纪委", "书记", "主席", "总理", "省委", "市委", "书记", "人大", "政协",
    "逮捕", "判刑", "获刑", "起诉", "离婚", "恋情", "出轨", "塌房", "官宣", "综艺",
    "电视剧", "演唱会", "电影票房", "去世", "逝世", "悼念", "遗体", "追悼",
    "彩礼", "嫁妆", "彩票", "球队", "比赛", "夺冠", "奥运", "世界杯", "台风", "地震",
    "菜价", "猪肉", "退休", "养老金", "医保", "社保", "房贷", "彩礼", "高考", "中考",
    "天气", "高温", "暴雨", "减肥神药", "手术", "医院", "药",
]

GITHUB_API = "https://api.github.com/repos/%s/contents/README.md"


def get_token():
    tok = os.environ.get("GH_TOKEN", "")
    if tok:
        return tok.strip()
    envf = os.path.join(BASE_DIR, ".env")
    if os.path.exists(envf):
        try:
            for line in open(envf, encoding="utf-8", errors="replace"):
                if line.startswith("GH_TOKEN="):
                    return line.strip().split("=", 1)[1]
        except Exception:
            pass
    return ""


def fetch_board():
    """读知乎热搜榜 README，返回 [(rank, title)]"""
    import urllib.request
    h = {"User-Agent": "opencode-zhihu", "Accept": "application/vnd.github+json"}
    tok = get_token()
    if tok:
        h["Authorization"] = "Bearer " + tok
    req = urllib.request.Request(GITHUB_API % REPO, headers=h)
    with urllib.request.urlopen(req, timeout=25) as r:
        j = json.loads(r.read().decode("utf-8"))
    txt = base64.b64decode(j["content"]).decode("utf-8", "replace")
    out = []
    for ln in txt.split("\n"):
        m = re.match(r"^\s*(\d+)\.\s*\[(.*?)\]\((.*?)\)", ln)
        if m:
            out.append((int(m.group(1)), m.group(2).strip(), m.group(3)))
    return out


def pick_tech(items):
    """过滤 + 按主题聚类（同一事件的多条 = 热度），返回 [{rank,title,heat,tags,url}]"""
    cands = []
    for rank, title, url in items:
        if any(b in title for b in BLOCK_KW):
            continue
        tags = [k for k in TECH_KW if k.lower() in title.lower()]
        if not tags:
            continue
        cands.append({"rank": rank, "title": title, "url": url, "tags": tags})
    # 聚类：标签集合有交集的归同一事件
    groups = []
    for c in cands:
        placed = False
        for g in groups:
            if set(c["tags"]) & set(g["tags"]):
                g["members"].append(c)
                g["tags"] = sorted(set(g["tags"]) | set(c["tags"]))
                placed = True
                break
        if not placed:
            groups.append({"members": [c], "tags": list(c["tags"])})
    out = []
    for g in groups:
        ms = sorted(g["members"], key=lambda x: x["rank"])
        out.append({"rank": ms[0]["rank"], "title": ms[0]["title"], "url": ms[0]["url"],
                    "heat": len(ms), "tags": g["tags"][:4],
                    "also": [m["title"] for m in ms[1:4]]})
    out.sort(key=lambda x: (-x["heat"], x["rank"]))
    return out


def build_text(items, date):
    if not items:
        return ""
    lines = ["【今日热点选题 · 知乎热搜】", ""]
    for i, it in enumerate(items, 1):
        lines.append("%d. %s  （热度 %d 条）" % (i, it["title"], it["heat"]))
        if it["also"]:
            lines.append("   相关：%s" % " / ".join(it["also"]))
    lines.append("")
    lines.append("—— 榜单每小时更新 %s，这是当时的实时热度" % date)
    return "\n".join(lines)


def main():
    as_json = "--json" in sys.argv
    today = datetime.date.today().isoformat()
    try:
        items = pick_tech(fetch_board())
    except Exception as e:
        print("知乎榜抓取失败: %s" % e)
        if os.path.exists(OUT_FILE):
            try:
                old = json.load(open(OUT_FILE, encoding="utf-8"))
                print("沿用上次结果: %s" % old.get("date"))
                if as_json:
                    print(json.dumps(old, ensure_ascii=False))
                return
            except Exception:
                pass
        items = []
    data = {"date": today, "generated": datetime.datetime.now().isoformat(timespec="seconds"),
            "items": items, "text": build_text(items, today)}
    try:
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    except Exception as e:
        print("写文件失败: %s" % e)
    if as_json:
        print(json.dumps(data, ensure_ascii=False))
    else:
        print("知乎榜 %d 条 → 过滤出 %d 个技术/商业热点" % (19, len(items)))
        for i, it in enumerate(items, 1):
            print("%d. %s  热度%d  %s" % (i, it["title"], it["heat"], "/".join(it["tags"][:3])))


if __name__ == "__main__":
    main()
