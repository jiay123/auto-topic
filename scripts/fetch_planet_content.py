"""
15:00 知识星球内容
方向：公众号的"深度版"——不是重复内容，而是：
  - 工具详细教程（图文版，比视频更细）
  - 内测/内参（新工具先发星球）
  - 资源导航（星球专属工具合集）
  - 粉丝答疑
内容来源：读当天的 GitHub 项目 + 历史文章 + 公众号后台数据
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


GITHUB_STATE = os.path.join(os.path.dirname(__file__), "..", "state_github_projects.json")
HISTORY_DIR = r"D:\jithub最新項目\my--公众号文章\articles"
PROGRESS_FILE = r"D:\jithub最新項目\当前进度.md"
PLANET_ARTICLES_FILE = os.path.join(os.path.dirname(__file__), "..", "state_planet_content.json")


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


def load_planet_history():
    """读取星球历史，避免重复写同一主题。"""
    try:
        if os.path.exists(PLANET_ARTICLES_FILE):
            with open(PLANET_ARTICLES_FILE) as f:
                return json.load(f)
    except:
        pass
    return {"published": [], "last_date": ""}


def save_planet_history(history):
    with open(PLANET_ARTICLES_FILE, "w") as f:
        json.dump(history, f)


TOPIC_TEMPLATES = [
    {
        "type": "工具教程",
        "templates": [
            ("{project}完整安装教程",
             "很多人在安装{project}时踩了坑，今天手把手带你们走一遍。\n\n先说结论：安装其实很简单，只需要3步。\n\n**第一步：下载**\n去官网找到最新版本，直接下载对应系统的安装包。\n\n**第二步：安装**\n双击安装包，一路点下一步即可。没有其他依赖。\n\n**第三步：配置**\n打开后默认配置就能用，如果要深度定制，可以参考我的配置文件。\n\n#工具教程 #上手指南"),
            ("{project}的5个隐藏用法",
             "用了{project}三个月，发现了5个官方文档没写、但巨好用的功能。\n\n**1. 快速启动**\n按住快捷键可以直接打开，不需要每次点图标。\n\n**2. 批量操作**\n选中多个文件，批量处理速度翻倍。\n\n**3. 自定义模板**\n把自己常用的设置保存成模板，下次直接调用。\n\n**4. 命令行模式**\n支持直接输入指令，高级用户效率翻倍。\n\n**5. 自动同步**\n设置好后，换电脑也能无缝衔接。\n\n#技巧分享 #实用功能"),
        ]
    },
    {
        "type": "开源推荐",
        "templates": [
            ("{project}免费替代了哪些付费工具",
             "{project}是最近发现的一个开源宝藏，完全免费，功能却不输那些月费几百的付费软件。\n\n**它的核心能力：**\n{description}\n\n**对比付费方案：**\n付费工具通常要$19/月，功能和{project}基本一样。但{project}免费，而且完全开源。\n\n**怎么用：**\n直接去GitHub下载，按照我之前发的教程安装就行。\n\n适合人群：不想每个月交软件费的技术人。\n\n#省钱攻略 #开源工具"),
            ("这个开源项目，解决了{problem}",
             "很多人在问{project}能做什么，今天来解答。\n\n**核心痛点：**\n{problem}\n\n**{project}的解决方案：**\n{description}\n\n**我的评价：**\n上手简单，不需要配置，写完就能用。但也有些局限，比如XXX。总体来说是目前开源社区里最好的解决方案之一。\n\n#开源工具 #问题解决"),
        ]
    },
    {
        "type": "资源导航",
        "templates": [
            ("免费AI工具合集（第X期）",
             "整理了最近用过的免费AI工具，按用途分类：\n\n**文本生成类**\n1. XXX - 免费额度够用\n2. XXX - 中文支持好\n3. XXX - API便宜\n\n**图片生成类**\n1. XXX - 每天免费50张\n2. XXX - 开源可本地部署\n3. XXX - 风格多样\n\n**工具效率类**\n1. XXX - 省时间神器\n2. XXX - 自动化工作流\n3. XXX - 开箱即用\n\n我会持续更新这个合集，星球成员免费获取最新版本。\n\n#资源分享 #AI工具"),
            ("{project}生态全景图",
             "想入{project}但不知道从哪开始？今天画一张生态图，帮你理清整个体系。\n\n**核心层：就是这个工具本身**\n\n**生态层：围绕它的插件和扩展**\n- XX插件：功能增强\n- XX插件：界面美化\n- XX插件：效率提升\n\n**资源层：学习资料**\n- 官方文档（英文，但写得很清楚）\n- 我的中文简明教程（星球内）\n- B站视频教程（推荐XXX UP主的系列）\n\n#资源导航 #上手指南"),
        ]
    },
    {
        "type": "经验分享",
        "templates": [
            ("写公众号这X个月，我踩过的坑",
             "从第一篇文章到现在，有几个坑希望你们别再踩了。\n\n**坑1：选题太技术**\n粉丝很多不是程序员，用太多术语直接掉粉。\n→ 解决：所有术语用大白话解释，加类比。\n\n**坑2：更新没规律**\n想起来写一篇，不想写半个月不更，粉丝取关。\n→ 解决：固定每周X更新，提前备稿。\n\n**坑3：只看流量**\n追热点短期涨粉，长期没有忠实读者。\n→ 解决：找到自己的定位，坚持输出。\n\n#经验分享 #做号心得"),
            ("我常用的这几个AI工具",
             "日常写文章、做视频，我常备这几个AI工具：\n\n**文章写作**\nClaude - 逻辑清晰，适合写结构化内容\no3 - 创意发散，适合想选题\n豆包 - 中文理解好，适合改稿\n\n**配图制作**\nStable Diffusion - 本地部署，免费无限用\nMidjourney - 付费但质量高\n\n**视频脚本**\nChatGPT - 框架清晰\nClaude - 细节丰富\n\n#AI工具 #工作流分享"),
        ]
    },
    {
        "type": "粉丝答疑",
        "templates": [
            ("本周粉丝问题答疑",
             "这周收到了几个好问题，整理出来供大家参考：\n\n**Q1：怎么快速找到值得写的开源项目？**\n我用GitHub的trending页面，配合关键词过滤，筛选一周内活跃、高星、有人维护的项目。每天自动推送，不需要手动找。\n\n**Q2：不会编程，推荐的工具能用吗？**\n能。我推荐的工具大部分不需要写代码，有图形界面或简单命令就能用。偶尔有需要代码的，我会在文章里一步步教你们。\n\n**Q3：做公众号多久能看到效果？**\n我自己做了X个月，坚持更新的情况下，3个月开始有自然流量。关键是内容质量，不是更新频率。\n\n#粉丝答疑 #问答"),
        ]
    }
]


def get_topic_for_today():
    """根据今天情况，选择最适合的星球内容类型。"""
    today = datetime.now().weekday()  # 0=周一，4=周五
    hour = datetime.now().hour

    # 周一到周五工作日，适合工具类内容
    # 周六周日，适合经验分享类

    if today in [0, 2, 4]:  # 周一、三、五
        return random.choice(["工具教程", "开源推荐"])
    elif today in [1, 3]:  # 周二、四
        return random.choice(["资源导航", "粉丝答疑"])
    else:  # 周末
        return "经验分享"


def load_today_github_project():
    """读取今天推荐的GitHub项目。"""
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        if os.path.exists(GITHUB_STATE):
            with open(GITHUB_STATE) as f:
                data = json.load(f)
                if data.get("date") == today:
                    return data.get("projects", [{}])[0] if data.get("projects") else {}
    except:
        pass
    return {}


def build_content_for_topic(topic_type, github_project=None):
    """根据类型和GitHub项目生成内容。"""
    project_name = github_project.get("name", "这个工具") if github_project else "该项目"
    description = github_project.get("description", "") if github_project else ""
    problems = {
        "ai写作效率低": "ai写作效率低",
        "每天找素材费时间": "每天找素材费时间",
        "配图不知道去哪找": "配图不知道去哪找",
        "视频脚本写不出来": "视频脚本写不出来",
        "不知道怎么推广公众号": "不知道怎么推广公众号",
        "免费工具找不到": "免费工具找不到",
    }

    for cat in TOPIC_TEMPLATES:
        if cat["type"] == topic_type:
            tpl = random.choice(cat["templates"])
            content = tpl[1].format(
                project=project_name,
                description=description,
                problem=random.choice(list(problems.values())),
                X=random.randint(1, 9)
            )
            title = tpl[0].format(
                project=project_name,
                problem=random.choice(list(problems.keys())),
                X=random.randint(1, 9)
            )
            return title, content

    # 默认：工具教程
    title = f"{project_name}上手指南"
    content = f"这是今天推荐的GitHub项目，适合入门。\n\n**项目简介：**\n{description}\n\n**主要内容：**\n1. 什么是{project_name}\n2. 能解决什么问题\n3. 如何快速上手\n4. 注意事项\n\n#知识星球 #入门教程"
    return title, content


def build_message(title, content, topic_type):
    now = datetime.now().strftime("%Y-%m-%d")
    date_cn = f"{datetime.now().year}年{datetime.now().month}月{datetime.now().day}日"
    weekday_map = {
        "Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
        "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"
    }
    weekday = weekday_map.get(datetime.now().strftime("%A"), "")
    full_title = f"老贾，今天是{date_cn}早上好，知识星球内容"

    lines = [
        f"老贾，今天是{date_cn}（{weekday}）。以下是星球专属内容：\n",
        f"内容类型：**{topic_type}**\n",
        "---",
        f"### {title}",
        "",
        content,
        "",
        "---",
        "💡 这是星球专属内容，如果你还没加入，点击公众号菜单栏「知识星球」加入。",
    ]
    return full_title, "\n".join(lines)


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
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"生成知识星球内容 ({today})...")

    history = load_planet_history()

    # 避免连续两天发同一类型
    recent_types = history.get("recent_types", [])
    topic_type = get_topic_for_today()
    # 如果上一条是同一类型，换一个
    if recent_types and recent_types[-1] == topic_type:
        topic_type = random.choice([t["type"] for t in TOPIC_TEMPLATES if t["type"] != topic_type])

    github_project = load_today_github_project()
    title, content = build_content_for_topic(topic_type, github_project)

    # 记录历史
    history.setdefault("published", []).append({"date": today, "title": title})
    history["published"] = history["published"][-30:]
    history.setdefault("recent_types", []).append(topic_type)
    history["recent_types"] = history["recent_types"][-7:]
    history["last_date"] = today
    save_planet_history(history)

    full_title, msg_content = build_message(title, content, topic_type)
    send_wechat(full_title, msg_content)
    print(f"推送完成：{topic_type} - {title}")


if __name__ == "__main__":
    import random as _random
    random = _random
    main()