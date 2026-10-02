"""06:00 每日动作提醒（Server酱推微信）
内容全部自动生成，不再依赖手工维护的 today_plan.txt（那是过期推送的根源）：
  1. 今天该发哪一集（读 视频台账.md 的发布日）
  2. 哪些集还没按新标准重做（读台账标准状态表）
  3. 哪些已发的集还缺数据（催老贾报播放）
  4. 固定三条每日动作
"""
import os
import re
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
# 视频台账路径。GitHub Actions 上跑时用 LEDGER_PATH 注入；
# 本地默认指向老贾机器上的台账，路径不存在就静默跳过（不会让推送失败）。
LEDGER = os.environ.get("LEDGER_PATH", r"D:\视频探索\视频台账\视频台账.md")
WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def load_ledger():
    if os.path.exists(LEDGER):
        with open(LEDGER, encoding="utf-8") as f:
            return f.read()
    return ""


def parse(text):
    today = datetime.now(timezone(timedelta(hours=8)))
    md = "%d月%d日" % (today.month, today.day)
    due_today, need_remake, need_data = [], [], []
    for line in text.splitlines():
        if not line.startswith("| 第"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 11:
            continue
        ep, title, pub, status, views = c[0], c[1], c[4], c[5], c[6]
        if "待发" in status and md in pub:
            due_today.append("%s·%s" % (ep, title))
        if "⚠️" in status or "老标准" in status:
            need_remake.append("%s·%s" % (ep, title))
        pm = re.search(r"(\d+)月(\d+)日", pub)
        if "已发" in status and (views == "-" or views == "") and pm:
            d = datetime(now.year, int(pm.group(1)), int(pm.group(2)), tzinfo=timezone(timedelta(hours=8)))
            if (now - d).days <= 7:
                need_data.append("%s·%s" % (ep, title))
    return due_today, need_remake, need_data


def main():
    if not SENDKEY:
        print("no SENDKEY, skip")
        return
    now_cn = datetime.now(timezone(timedelta(hours=8)))
    title = "小叮当提醒：老贾，今天%d月%d日%s 开干！" % (now_cn.month, now_cn.day, WEEKDAYS[now_cn.weekday()])

    due, remake, data = parse(load_ledger())
    b = []
    if due:
        b.append("【今天要发的】")
        b += ["· " + x for x in due]
    else:
        b.append("【今天要发的】台账里今天没有排集 → 问我，我马上选一条")
    if remake:
        b.append("")
        b.append("【还没按新标准重做（发前必须做）】")
        b += ["· " + x for x in remake]
    if data:
        b.append("")
        b.append("【已发但缺数据，发完找我要】")
        b += ["· " + x for x in data]
    b.append("")
    b.append("【每天3件事】")
    b.append("1. 早7:00 视频号发正片")
    b.append("2. 发完贴置顶：这集全程用的都是免费开源工具，一分钱没花。想跟老贾一样自己做的，评论区扣“工具”，我挨个回。")
    b.append("3. 星球每周至少1篇")
    b.append("")
    b.append("每天6点这条、7点当天AI资讯、9点最新GitHub开源项目，我自动推给你。")
    b.append("想拍视频就说一声，我上GitHub和资讯里挑，挑完跟判官一起打分，选最值得做的那条，直接给你成片。")

    resp = requests.post(
        "https://sctapi.ftqq.com/%s.send" % SENDKEY,
        data={"title": title, "desp": "\n".join(b)},
        timeout=30,
    )
    print(resp.status_code, resp.text[:200])
    print("--- 待发:%s 重做:%s 缺数据:%s" % (due, remake, data))


if __name__ == "__main__":
    main()