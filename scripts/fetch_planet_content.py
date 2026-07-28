"""
09:00 每日运营 + 热点拆解
内容：
  - 一条运营技巧（公众号涨粉/排版/推广）
  - 微博热搜爆款标题拆解（2-3条）
  - 知乎热榜高赞话题（1-2条）
  - 老贾今日可蹭热点建议
数据来源：内置运营技巧库 + 微博热搜API + 知乎热榜API
"""
import requests
import os
import json
import random
from datetime import datetime

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

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
TIP_STATE_FILE = os.path.join(BASE_DIR, "state_daily_tips.json")


# --- 运营技巧库（每周7大类，轮流推送）---
TIPS = [
    # 标题技巧
    {"type": "标题", "tips": [
        {"title": "标题加数字，打开率高30%", "content": "比如「5个免费替代Photoshop的工具」比「免费替代Photoshop的工具」效果好得多。因为数字给读者确定感——知道要读几条，大脑更喜欢处理有结构的信息。下次起标题，试着把「几个」「这些」换成明确的数字。"},
        {"title": "标题最后6个字决定打开率", "content": "公众号列表只显示标题前20字左右，但用户余光扫到的最后几个字是关键。把最劲爆的词放在标题末尾。比如不说「这个免费工具太好用了，你一定要试试」，而说「你一定要试试的这个免费工具，用完我卸载了付费版」。"},
        {"title": "问句标题互动率高2倍", "content": "「你知道XXX吗？」「你还在用XXX吗？」——问句制造悬念，读者本能想点开看答案。但注意：问句后面的正文必须给出明确答案，否则读者会失望取关。"},
        {"title": "蹭热点标题：3小时窗口期", "content": "热点出来后3小时内发文章效果最好。标题里直接带热点关键词，比如「XXX事件后，我用这个工具省了500块」。超过6小时基本凉了，别发了。"},
        {"title": "反常识标题最容易爆", "content": "「每天写500字，不如每周写一篇3000字」「涨粉最快的不是追热点，而是写教程」——和读者常识反着来，好奇心会驱使他们点开。但内容必须真的有理有据，不能标题党。"},
    ]},
    # 涨粉技巧
    {"type": "涨粉", "tips": [
        {"title": "文末引导决定80%的关注转化", "content": "看完文章的人是最容易点关注的。文末不要只说「求关注」，而是说「我每周挖掘5个免费开源工具，关注我下周不错过」。给一个具体的、读者能获得的利益点。"},
        {"title": "合集功能是涨粉利器", "content": "公众号后台「合集」功能可以把同主题文章打包。合集页面会被微信搜一搜收录，带来搜索流量。每写5篇同主题文章就建一个合集，标题带关键词比如「免费AI工具合集」。"},
        {"title": "留言区是第二篇文章", "content": "认真回复每条留言，特别是提问的。回复内容本身可以成为下一篇文的素材。读者看到你认真回复，关注意愿更强。挑精彩留言置顶，能带动更多留言。"},
        {"title": "跨平台引流：知乎和小红书", "content": "把公众号文章的核心观点改写成知乎回答或小红书笔记，文末附公众号名称。知乎长文引流效果最好，小红书适合工具类。每天花10分钟同步一篇，一个月后效果明显。"},
        {"title": "互推要找同类不同号的号主", "content": "互推是涨粉最快的方式之一。找粉丝量差不多、内容方向互补（不是直接竞争）的号主，互相在文末推荐。一次好的互推可以带来50-200精准粉丝。"},
    ]},
    # 排版技巧
    {"type": "排版", "tips": [
        {"title": "手机预览是排版的唯一标准", "content": "95%读者用手机看。排版好不好，电脑上看不算数，必须手机预览。字号15-16px最舒适，段间距1.5-1.8倍，每段不超过3行（手机屏宽约40字/行），否则读者会累。"},
        {"title": "配图3-5张最佳", "content": "全是文字读者会跑。每800-1000字插一张图，保持阅读节奏。图要有信息量（截图/示意图/数据图），不要纯装饰。首图最重要——决定朋友圈转发后的预览效果。"},
        {"title": "配色不超过3种", "content": "正文一色、标题一色、重点标注一色，够了。颜色越多越廉价。深灰正文（#3f3f3f）+ 品牌色标题 + 品牌色高亮，是最安全的组合。"},
        {"title": "引用和列表让文章可扫读", "content": "大多数人是扫读不是精读。重点句用引用块，并列信息用列表。把文章最核心的3句话放在引用块里，扫一眼就知道值不值得细看。"},
    ]},
    # 选题技巧
    {"type": "选题", "tips": [
        {"title": "搜索量高的选题，自带流量", "content": "去微信搜一搜输入关键词，看下拉联想词。那些词就是读者正在搜的。围绕这些词写文章，微信搜索会给你推流量。比如搜「免费」「替代」「开源」，看哪些联想词高。"},
        {"title": "写系列文章比单篇涨粉多3倍", "content": "单篇文章读者看完就走。系列文章（比如「开源替代付费软件第X期」）会让读者期待下一篇，主动关注。系列做到第5期以后，新读者会回头翻前面的一起看。"},
        {"title": "工具类文章加「对比表」打开率高", "content": "文章开头放一张对比表（免费工具 A vs 付费工具 B），读者一看就懂。表格比文字快10倍。工具推荐文没有对比表等于没写。"},
        {"title": "你写过的爆款，换个角度再写一遍", "content": "不要怕重复。同一主题换角度（之前写「是什么」，这次写「怎么用」；之前写「入门」，这次写「进阶」）效果一样好。因为新粉丝没看过旧文。"},
    ]},
    # 变现技巧
    {"type": "变现", "tips": [
        {"title": "互选广告：750元/条的起步价怎么接", "content": "粉丝过500就可以开通互选广告。广告主选号的标准不是粉丝数，是「垂直度」。一篇纯AI工具推荐文比一篇杂谈更容易接到广告。保持内容垂直，广告单价会越来越高。"},
        {"title": "知识星球定价策略", "content": "99元/年是最优起步价——太低读者觉得没价值，太高没人加。星球内容要和公众号差异化：公众号免费给推荐文章，星球给详细教程+内测工具+一对一答疑。每篇文章末尾放星球入口，转化率最高。"},
        {"title": "赞赏引导一句话就够", "content": "文末加一句「如果这篇帮你省了钱，赞赏1元支持我继续写」，比「求赞赏」效果好10倍。因为给读者一个合理的理由（省钱+支持创作）。平均每500阅读有5-15人赞赏。"},
    ]},
    # 内容写作
    {"type": "写作", "tips": [
        {"title": "开头第一句不讲客气话", "content": "不要说「大家好今天我来介绍…」直接讲痛点：「你还在为XXX花冤枉钱吗？」或者直接讲结论：「XXX可以免费替代付费软件，我来告诉你怎么用。」前3秒决定读者留不留。"},
        {"title": "每篇文章只讲一件事", "content": "一篇文章塞多个工具=读者一个都记不住。一篇讲一个工具+一个场景+一个结论。文章越聚焦，转发率越高。想推多个工具？拆成系列。"},
        {"title": "结尾给行动指令", "content": "不要说「希望大家喜欢」——没人会因为这句话关注。说「去XXX下载这个工具，5分钟搞定。搞不定来留言问我。」给一个具体的、能立刻执行的动作，转化的读者会多很多。"},
    ]},
    # 数据分析
    {"type": "数据", "tips": [
        {"title": "转发量比阅读量更重要", "content": "阅读量高但转发低=内容不够好。转发率超过5%算优秀，超过10%是爆款。提升转发的核心：让读者转发后显得自己有品位（好工具分享）、有知识（学到了）、有态度（观点共鸣）。"},
        {"title": "取关高峰在推送后1小时内", "content": "别慌，这不是你写的不好。是有些读者收到推送才想起来「我什么时候关注了这个号」。持续取关是正常的，只要净增为正就行。关注取关比超过3:1算健康。"},
        {"title": "最佳推送时间是中午12点和晚上9点", "content": "中午12-13点午休刷手机，晚上21-22点睡前刷手机。这两个时段打开率最高。固定时间推送让读者养成习惯，比随机推效果好。"},
    ]},
]


def load_tip_state():
    try:
        if os.path.exists(TIP_STATE_FILE):
            with open(TIP_STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return {"used": [], "type_idx": 0}


def save_tip_state(state):
    with open(TIP_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def pick_daily_tip(state):
    used = set(state.get("used", []))
    available = []
    for cat in TIPS:
        for tip in cat["tips"]:
            if tip["title"] not in used:
                available.append((cat["type"], tip))

    if len(available) < 5:
        used = set()
        state["used"] = []
        for cat in TIPS:
            for tip in cat["tips"]:
                available.append((cat["type"], tip))

    choice = random.choice(available)
    used.add(choice[1]["title"])
    state["used"] = list(used)[-50:]
    return choice


# --- 微博热搜 ---
def fetch_weibo_hot():
    """抓取微博热搜，返回前15条。"""
    try:
        r = requests.get("https://weibo.com/ajax/side/hotSearch", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", {}).get("realtime", [])
            items = []
            for item in data[:20]:
                word = item.get("word", "").strip()
                if word and "微博" not in word and "公告" not in word:
                    items.append({"title": word, "rank": item.get("rank", 0), "num": item.get("num", 0)})
            return items[:15]
    except Exception as e:
        print(f"微博热搜抓取失败: {e}")
    return []


def analyze_weibo_title(item):
    """拆解一个微博热搜标题为什么能火。"""
    title = item["title"]
    rank = item["rank"]

    patterns = []
    if len(title) <= 8:
        patterns.append("短标题，一眼看完，适合快节奏刷屏")
    if "?" in title or "？" in title:
        patterns.append("问句制造悬念，让人想点进去找答案")
    if any(kw in title for kw in ["免费", "省", "赚", "钱", "元"]):
        patterns.append("带利益词（免费/省/赚），唤醒读者贪便宜心理")
    if any(kw in title for kw in ["爆", "炸", "最", "第一", "首次"]):
        patterns.append("极端词爆/最/首次，制造稀缺感和紧迫感")
    if any(kw in title for kw in ["AI", "人工智能", "大模型", "GPT", "ChatGPT"]):
        patterns.append("蹭AI热词，当前流量密码")
    if any(kw in title for kw in ["揭秘", "内幕", "曝光", "真相"]):
        patterns.append("揭秘/曝光类词触发好奇心")
    if any(kw in title for kw in ["崩了", "出事", "突发", "紧急"]):
        patterns.append("负面/紧急词，人天生对坏消息更敏感")
    is_num = any(ch.isdigit() for ch in title)
    if is_num:
        patterns.append("含数字，给读者确定感，比纯文字更抓眼球")

    if not patterns:
        patterns.append(f"热搜第{rank}名，蹭的是话题热度本身")

    return patterns


def analyze_weibo_for_laojia(item):
    """分析微博热搜标题，给老贾可以怎么蹭的建议。"""
    title = item["title"]
    suggestions = []
    if any(kw in title for kw in ["AI", "人工智能", "大模型", "GPT", "ChatGPT", "OpenAI"]):
        suggestions.append(f"「{title}」→ 老贾可写：这个AI事件背后的开源工具，或「AI又搞大事了，这3个免费工具帮你跟上」")
    if any(kw in title for kw in ["免费", "替代", "省"]):
        suggestions.append(f"「{title}」→ 老贾专长：直接写一篇免费替代付费方案的文章")
    if any(kw in title for kw in ["工具", "软件", "app", "App"]):
        suggestions.append(f"「{title}」→ 可以做成工具推荐文，加上对比表效果更好")
    if any(kw in title for kw in ["崩了", "出事", "投诉"]):
        suggestions.append(f"「{title}」→ 借负面事件推替代方案：「XXX崩了？试试这个免费替代」")
    if not suggestions:
        suggestions.append(f"「{title}」→ 热度高但和你的方向关联不强，可以不蹭")
    return suggestions


# --- 知乎热榜 ---
def fetch_zhihu_hot():
    """抓取知乎热榜，返回前10条。"""
    try:
        r = requests.get("https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=10", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", [])
            items = []
            for item in data:
                target = item.get("target", {})
                title = target.get("title", "").strip()
                if title:
                    items.append({
                        "title": title,
                        "excerpt": target.get("excerpt", "")[:100] if target.get("excerpt") else "",
                        "answer_count": target.get("answer_count", 0),
                        "follower_count": target.get("follower_count", 0),
                    })
            return items[:10]
    except Exception as e:
        print(f"知乎热榜抓取失败: {e}")
    return []


def analyze_zhihu_for_laojia(item):
    """分析知乎热榜话题，给老贾写作角度建议。"""
    title = item["title"]
    suggestions = []
    if "?" in title or "？" in title:
        suggestions.append(f"「{title}」→ 这是个提问，你可以写一篇回答式文章：先给结论再展开")
    if any(kw in title for kw in ["免费", "替代", "开源"]):
        suggestions.append(f"「{title}」→ 你的主场：推免费开源替代方案，知乎读者很吃这套")
    if any(kw in title for kw in ["推荐", "哪个好", "怎么选"]):
        suggestions.append(f"「{title}」→ 做对比评测文，表格对比几个方案，知乎高赞模版")
    if any(kw in title for kw in ["AI", "ChatGPT", "人工智能", "大模型"]):
        suggestions.append(f"「{title}」→ AI相关自带流量，但角度要够小，不写大而全")
    if item.get("answer_count", 0) > 500:
        suggestions.append(f"（{item['answer_count']}个回答，话题很热，值得写）")
    if not suggestions:
        suggestions.append(f"「{title}」→ 话题热度不错，可以从工具/效率角度切入")
    return suggestions


def build_message(tip_info, weibo_items, zhihu_items):
    now = datetime.now()
    date_cn = f"{now.year}年{now.month}月{now.day}日"
    weekday_map = {"Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
                   "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"}
    weekday = weekday_map.get(now.strftime("%A"), "")
    title = f"老贾，{date_cn}中午好，运营干货 + 热点拆解"

    lines = [
        f"老贾，{date_cn}（{weekday}）中午好。下面是今日运营干货和热点拆解。\n",
    ]

    tip_type, tip = tip_info
    lines.append("【一、今日运营技巧】")
    lines.append(f"**{tip['title']}**")
    lines.append(f"{tip['content']}")
    lines.append("")

    if weibo_items:
        lines.append("【二、微博热搜拆解】（今天在火什么？标题为什么能火？）")
        for item in weibo_items[:3]:
            lines.append(f"\n🔥 热搜第{item['rank']}名：{item['title']}")
            patterns = analyze_weibo_title(item)
            for p in patterns:
                lines.append(f"  → {p}")
            suggestions = analyze_weibo_for_laojia(item)
            for s in suggestions:
                lines.append(f"  ✏️ {s}")
        lines.append("")

    if zhihu_items:
        lines.append("【三、知乎热榜】（高赞话题 + 写作角度）")
        for item in zhihu_items[:2]:
            lines.append(f"\n📖 {item['title']}")
            if item.get("answer_count"):
                lines.append(f"  {item['answer_count']}个回答 · {item.get('follower_count', 0)}人关注")
            suggestions = analyze_zhihu_for_laojia(item)
            for s in suggestions:
                lines.append(f"  ✏️ {s}")
        lines.append("")

    best_topics = []
    for item in weibo_items[:3]:
        if any(kw in item["title"] for kw in ["AI", "免费", "工具", "替代"]):
            best_topics.append(("微博", item["title"]))
    for item in zhihu_items[:2]:
        if any(kw in item["title"] for kw in ["推荐", "替代", "开源", "免费"]):
            best_topics.append(("知乎", item["title"]))

    if best_topics:
        lines.append("【四、今日最值得蹭的话题】")
        source, topic = best_topics[0]
        lines.append(f"👉 {source}热榜「{topic}」——和你公众号方向最匹配，今天写这个打开率最高")
    else:
        lines.append("【四、今日最值得蹭的话题】")
        lines.append("👉 今天热榜没有特别匹配你方向的话题，专心打磨自己的选题，不强行蹭热点也是对的。")

    lines.append("\n---")
    lines.append("以上由小叮当整理，觉得有用点个赞 👍")
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
    print(f"生成每日运营 + 热点拆解 ({datetime.now().strftime('%Y-%m-%d %H:%M')})...")

    state = load_tip_state()
    tip_info = pick_daily_tip(state)
    save_tip_state(state)
    print(f"运营技巧：{tip_info[1]['title']}")

    print("抓取微博热搜...")
    weibo_items = fetch_weibo_hot()
    print(f"微博：{len(weibo_items)} 条")

    print("抓取知乎热榜...")
    zhihu_items = fetch_zhihu_hot()
    print(f"知乎：{len(zhihu_items)} 条")

    title, content = build_message(tip_info, weibo_items, zhihu_items)
    print("\n========== 推送预览 ==========")
    print(content[:500])
    print("==============================\n")

    send_wechat(title, content)
    print("推送完成")


if __name__ == "__main__":
    main()