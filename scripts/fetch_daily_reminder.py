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


def parse_plan(text):
    """从「📊 数据统计」章的「10月待发排期」表里读今天该发哪集。

    这张表才是真正的排期来源（视频总表的发布状态会被改掉，不能当排期用）。
    表格形如： | 10/3 | 第17集 | Hindsight给AI配记忆 | ✅已出片 |
    """
    rows = []
    section = ""
    for line in text.splitlines():
        if line.startswith("### "):
            section = line[4:].strip()
        if "待发排期" not in section:
            continue
        if not line.startswith("| 10/") and not line.startswith("| 11/"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 4 or c[0] == "日期":
            continue
        rows.append(c)
    return rows


def parse_ledger(text):
    """扫视频总表：挑出「已排期但还没按新标准重做」的（发前必须做），和已发但缺数据的。

    只认已排期的集（发布日期列有具体日期），不把 20-26 这种还没排到日子的库存集算进来
    —— 那是候选池，不是待办，提醒里吵到没法用。
    """
    # 先拿到排期表里已排期的集号
    scheduled = {r[1] for r in parse_plan(text)}

    remake, need_data = [], []
    now = datetime.now(timezone(timedelta(hours=8)))
    for line in text.splitlines():
        if not line.startswith("| 第"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 11:
            continue
        ep, title, pub, status, views = c[0], c[1], c[4], c[5], c[6]
        if "已发" in status:
            pm = re.search(r"(\d+)月(\d+)日", pub)
            if views in ("-", "") and pm:
                d = datetime(now.year, int(pm.group(1)), int(pm.group(2)),
                             tzinfo=timezone(timedelta(hours=8)))
                if 0 <= (now - d).days <= 3:
                    need_data.append("%s·%s（%s 发的）" % (ep, title, pub))
            continue
        # 未发：只在「已排期到具体某天」且标着老标准/待制作 时才算待办
        if ep in scheduled and ("老标准" in status or "待做" in status or "🔨" in status):
            remake.append("%s·%s（%s 发）" % (ep, title, pub))
    return remake, need_data


def main():
    if not SENDKEY:
        print("no SENDKEY, skip")
        return
    now_cn = datetime.now(timezone(timedelta(hours=8)))
    title = "小叮当提醒：老贾，今天%d月%d日%s 开干！" % (now_cn.month, now_cn.day, WEEKDAYS[now_cn.weekday()])

    ledger = load_ledger()
    if not ledger:
        print("台账没读到：%s" % LEDGER)
        return

    today_md = "%d/%d" % (now_cn.month, now_cn.day)
    b = []

    # 1) 今天该发哪集
    b.append("【今天要发的】")
    hit = [r for r in parse_plan(ledger) if r[0] == today_md]
    if hit:
        for r in hit:
            b.append("· %s·%s（%s）" % (r[1], r[2], r[3]))
    else:
        b.append("· 台账排期表里今天没排集 → 你说一句，我马上挑一条")
        nxt = [r for r in parse_plan(ledger)
               if r[0] not in ("日期",) and r[0] > today_md]
        if nxt:
            b.append("  （下一集：%s %s·%s）" % (nxt[0][0], nxt[0][1], nxt[0][2]))

    # 2) 还没重做的
    remake, data = parse_ledger(ledger)
    if remake:
        b.append("")
        b.append("【还没按新标准重做（发前必须做）】")
        b += ["· " + x for x in remake]

    # 3) 已发但缺数据
    if data:
        b.append("")
        b.append("【已发但缺数据，发完找我要】")
        b += ["· " + x for x in data]

    # 4) 今天的日子 + 每天固定三件事
    b.append("")
    b.append("【今天 %d月%d日%s】" % (now_cn.month, now_cn.day, WEEKDAYS[now_cn.weekday()]))
    b.append("1. 早7:00 视频号发正片")
    b.append("2. 发完贴置顶：这集全程用的都是免费开源工具，一分钱没花。想跟老贾一样自己做的，评论区扣“工具”，我挨个回。")
    b.append("3. 星球每周至少1篇")
    b.append("")
    b.append("这条台账实时读，不用你记。台账改了明天这条就跟着变。")
    b.append("想拍视频就说一声，我上GitHub和资讯里挑，挑完跟判官一起打分，选最值得做的那条，直接给你成片。")

    resp = requests.post(
        "https://sctapi.ftqq.com/%s.send" % SENDKEY,
        data={"title": title, "desp": "\n".join(b)},
        timeout=30,
    )
    print(resp.status_code, resp.text[:200])
    print("--- 待发:%s 重做:%s 缺数据:%s" % (hit, remake, data))


if __name__ == "__main__":
    main()