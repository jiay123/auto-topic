"""
06:00 北京时间 每日动作提醒（Server酱推送）
内容：今天要干的3件事 + 从 today_plan.txt 读当日具体安排（可选）
"""
import os
import requests
from datetime import datetime, timedelta, timezone

SENDKEY = os.environ.get("SENDKEY", "")
if not SENDKEY:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(base, ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("SENDKEY="):
                    SENDKEY = line.strip().split("=", 1)[1]
                    break

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def load_today_plan():
    path = os.path.join(BASE_DIR, "today_plan.txt")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    return ""


def main():
    if not SENDKEY:
        print("no SENDKEY, skip")
        return
    now_cn = datetime.now(timezone(timedelta(hours=8)))
    plan = load_today_plan()
    weekday_ch = WEEKDAYS[now_cn.weekday()]
    title = "小叮当提醒：老贾，今天%d月%d日%s 开干！" % (now_cn.month, now_cn.day, weekday_ch)

    body_lines = []
    if plan:
        body_lines.append(plan)
        body_lines.append("")
        body_lines.append("-----")
        body_lines.append("")
    body_lines.append("【每天3件事】")
    body_lines.append("1. 发视频：今天发哪集，问小叮当要")
    body_lines.append("2. 发星球：今天发哪篇，问小叮当要")
    body_lines.append("3. 评论区置顶：这集全程用的都是免费开源工具，一分钱没花。想跟老贾一样自己做的，评论区扣“工具”，我挨个回。翻我往期也全是0成本玩法。")
    body_lines.append("")
    body_lines.append("发完找小叮当报播放数据，我更新台账。")
    body = "\n".join(body_lines)

    resp = requests.post(
        "https://sctapi.ftqq.com/%s.send" % SENDKEY,
        data={"title": title, "desp": body},
        timeout=30,
    )
    print(resp.status_code, resp.text[:300])


if __name__ == "__main__":
    main()