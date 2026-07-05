"""
17:00 每日复盘
内容：
  - 今日完成
  - 未完成 + 原因
  - 明日计划
  - 数据快报（公众号数据）
  - 小叮当建议
进度文件：只保留当天，其他移到进度存档。
"""
import requests
import os
import json
import shutil
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

# 兼容本地和云端（GitHub Actions Ubuntu）路径
_script_dir = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(_script_dir)  # auto-topic/
PROGRESS_FILE = os.path.join(ROOT_DIR, "..", "jithub最新項目", "当前进度.md")
ARCHIVE_DIR = os.path.join(ROOT_DIR, "进度存档")


def cleanup_progress():
    """进度文件只保留当天的，其他移到存档（本地Windows有效，云端优雅跳过）。"""
    try:
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        today_prefix = f"当前进度-{today}"
        moved = []
        if not os.path.isdir(ROOT_DIR):
            print("本地进度目录不存在，跳过归档")
            return moved
        for fname in os.listdir(ROOT_DIR):
            if not fname.startswith("当前进度-") or not fname.endswith(".md"):
                continue
            if today in fname:
                continue
            src = os.path.join(ROOT_DIR, fname)
            dst = os.path.join(ARCHIVE_DIR, fname)
            shutil.move(src, dst)
            moved.append(fname)
        return moved
    except Exception as e:
        print(f"归档跳过: {e}")
        return []


def parse_progress():
    """从当前进度.md提取：已完成、未完成、明日计划。云端无此文件时返回空。"""
    result = {"done": [], "undone": [], "next": [], "cloud_mode": False, "raw": ""}
    if not os.path.exists(PROGRESS_FILE):
        result["cloud_mode"] = True
        return result

    with open(PROGRESS_FILE, encoding="utf-8") as f:
        content = f.read()
        result["raw"] = content

    section = None
    for line in content.split("\n"):
        if "✅" in line or ("已完成" in content and "## ✅" in line):
            section = "done"
        elif "❌" in line:
            section = "undone"
        elif "⚡" in line or "下一步" in line:
            section = "next"
        elif line.startswith("##") and "已完成" not in line and "❌" not in line and "⚡" not in line and "下一步" not in line:
            section = None

        stripped = line.strip()
        if section == "done" and stripped.startswith("- "):
            item = stripped[2:].strip()
            if item:
                result["done"].append(item)
        elif section == "undone" and stripped.startswith("- "):
            item = stripped[2:].strip()
            if item:
                result["undone"].append(item)
        elif section == "next" and stripped.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")):
            # 提取 ] 后的内容
            if "]" in stripped:
                item = stripped.split("]", 1)[1].strip()
            else:
                item = stripped
            if item:
                result["next"].append(item)

    return result


def generate_suggestion(parsed):
    """根据当天情况，生成小叮当建议。"""
    if parsed.get("cloud_mode"):
        return [
            "今天推送全部完成。",
            "明天早上7点见，记得在本地更新当前进度.md。",
        ]

    suggestions = []

    done_count = len(parsed.get("done", []))
    undone_count = len(parsed.get("undone", []))

    if done_count == 0:
        suggestions.append("今天还没有完成记录，记得在当前进度.md里记录一下。")
    elif undone_count > 3:
        suggestions.append(f"你还有 {undone_count} 个未完成事项，是不是太多了？挑最重要的3个优先做，其他的可以先放一放。")
    elif undone_count >= 1:
        suggestions.append(f"{undone_count} 个未完成，注意时间分配。写文章优先于其他琐事。")

    if done_count >= 2:
        suggestions.append(f"今天完成了 {done_count} 项，干得不错！")

    # 通用建议
    if not suggestions:
        suggestions.append("保持节奏，每天进步一点点。")

    return suggestions


def build_message(parsed, archived, suggestions):
    now = datetime.now().strftime("%Y-%m-%d")
    weekday_map = {
        "Monday": "周一", "Tuesday": "周二", "Wednesday": "周三",
        "Thursday": "周四", "Friday": "周五", "Saturday": "周六", "Sunday": "周日"
    }
    weekday = weekday_map.get(datetime.now().strftime("%A"), "")
    date_cn = f"{datetime.now().year}年{datetime.now().month}月{datetime.now().day}日"
    title = f"老贾，今天是{date_cn}下午好，今日复盘"

    lines = [
        f"老贾，今天是{date_cn}（{weekday}）。以下是今日复盘：\n",
    ]

    # 今日完成
    lines.append("### ✅ 今日完成")
    done = parsed.get("done", [])
    if parsed.get("cloud_mode"):
        lines.append("  （云端模式，详细进度需在本地更新当前进度.md）")
    elif done:
        for i, item in enumerate(done, 1):
            lines.append(f"  {i}. {item}")
    else:
        lines.append("  （今日暂无记录）")
    lines.append("")

    # 未完成 + 原因
    lines.append("### ❌ 未完成")
    undone = parsed.get("undone", [])
    if undone:
        for i, item in enumerate(undone, 1):
            lines.append(f"  {i}. {item}")
    else:
        lines.append("  全部完成！🎉")
    lines.append("")

    # 明日计划
    lines.append("### ⚡ 明日计划")
    next_items = parsed.get("next", [])
    if next_items:
        for i, item in enumerate(next_items, 1):
            lines.append(f"  {i}. {item}")
    else:
        lines.append("  （待补充）")
    lines.append("")

    # 进度文件
    if archived:
        lines.append("### 📁 进度文件清理")
        lines.append(f"  已归档 {len(archived)} 个旧进度文件 → 进度存档/")
        for f in archived:
            lines.append(f"  ・{f}")
        lines.append("")
    else:
        lines.append("### 📁 进度文件")
        lines.append("  无需归档，今日进度即当天版本")
        lines.append("")

    # 小叮当建议
    lines.append("### 💡 小叮当建议")
    for s in suggestions:
        lines.append(f"  → {s}")
    lines.append("")

    # 今日推送汇总
    lines.append("### 📬 今日推送一览")
    lines.append("  07:00  AI 热点速递")
    lines.append("  09:00  GitHub 项目推荐")
    lines.append("  11:00  文章选题推荐")
    lines.append("  15:00  知识星球内容")
    lines.append("  17:00  今日复盘 ← 正在看")
    lines.append("")

    lines.append("---")
    lines.append("晚安老贾，明天见！🌙")

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
    print("生成每日复盘...")

    # 清理旧进度文件
    archived = cleanup_progress()
    print(f"归档：{len(archived)} 个")

    # 解析进度内容
    parsed = parse_progress()
    print(f"已完成：{len(parsed['done'])} 条")
    print(f"未完成：{len(parsed['undone'])} 条")
    print(f"下一步：{len(parsed['next'])} 条")

    # 生成建议
    suggestions = generate_suggestion(parsed)

    title, content = build_message(parsed, archived, suggestions)
    send_wechat(title, content)
    print("推送完成")


if __name__ == "__main__":
    main()