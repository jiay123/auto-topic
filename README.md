# auto-topic · 每天早上把该看的东西推到你微信

一个人做自媒体，最难的不是做内容，是**每天记得该干什么**。今天发第几集？昨天那条数据回了吗？台账里标着"发前必须重做"的是哪一集？星球这周发第几篇？

这个项目把这些琐事变成一条命令：**GitHub Actions 每天定时跑，把当天待办抓到 Server 酱，推到你微信**。你醒来打开手机就有一条消息，不用打开电脑、不用翻台账。

## 它做什么

一天六个时间点，每个时间点推一条内容，全部自动抓取 + 自动去重：

| 时间 | 推什么 | 脚本 |
|------|--------|------|
| 06:00 | **今日待办** — 扫视频台账自动得出今天该发哪集、哪集要重做、哪集等数据 | `fetch_daily_reminder.py` |
| 07:00 | **AI 资讯头条** — 抓 AI 新闻源，挑出当天最值得看的一条 | `fetch_ai_news.py` |
| 09:00 | **GitHub 项目推荐** — 每天 3 个新项目，带星数、语言、用途 | `fetch_github_projects.py` |
| 11:00 | **今日选题** — 从候选池里挑一个，并记录轮换避免重复 | `fetch_article_pick.py` |
| 15:00 | **傍晚提示** — 当天剩余时间够做多少事 | `fetch_evening_tip.py` |
| 17:00 | **数据回灌** — 提醒把昨天视频的播放/点赞数据填回台账 | `fetch_daily_review.py` |
| — | **星球内容草稿** — 从素材库抓素材，供知识星球日更 | `fetch_planet_content.py` |

推送走 [Server 酱](https://sct.ftqq.com/) 的微信服务号，零成本、不占手机内存、不用装 App。

## 特点

- **纯 Python 标准库 + requests**，无数据库、无云服务、无前端
- **状态文件即去重**：`state_*.json` 存已推过的 id，GitHub Actions 每次跑完自动 commit 回去，所以同一条资讯不会连着推三天
- **GitHub Actions 原生 cron**，不用自己的服务器、不用开机
- **可手动触发**：Actions 页面点 Run workflow 立刻补推

## 上手

### 1. Fork 这个仓库

### 2. 配 Secrets

仓库 Settings → Secrets and variables → Actions，加两个：

| 名字 | 值 |
|------|-----|
| `SENDKEY` | Server 酱的 SendKey（sct.ftqq.com 微信绑定后拿） |
| `GH_TOKEN` | GitHub token，权限勾 `public_repo`，用来读更多项目数据 |
| `GITHUB_TOKEN` | Actions 自动提供，不用管——但 job 需要 `contents: write` 权限回写状态文件 |

### 3. 启用 workflow

Actions → Daily Push → Enable。cron 是 UTC 时间，workflow 里已经写好换算，直接启用即可。

### 4. 手动验证

Actions 页面点 **Run workflow**，几秒后微信就该收到 06:00 的待办。

## 本地跑

```bash
pip install requests
# SendKey 放 .env 或环境变量
python scripts/fetch_daily_reminder.py
```

`fetch_daily_reminder.py` 会去读本地视频台账。用 `LEDGER_PATH` 环境变量指定路径：

```bash
LEDGER_PATH="/path/to/视频台账.md" python scripts/fetch_daily_reminder.py
```

路径不存在时脚本静默跳过、不会崩——CI 上没有本地台账是正常的。

Windows 上还有 `run-*.bat` 快捷脚本（不进仓库，只在本机用）。

## 目录结构

```
auto-topic/
├── .github/workflows/daily-push.yml   # 定时任务定义（cron + 各 job）
├── scripts/
│   ├── fetch_daily_reminder.py        # 06:00 今日待办
│   ├── fetch_ai_news.py               # 07:00 AI 资讯
│   ├── fetch_github_projects.py       # 09:00 GitHub 项目
│   ├── fetch_article_pick.py          # 11:00 今日选题
│   ├── fetch_evening_tip.py           # 15:00 傍晚提示
│   ├── fetch_daily_review.py          # 17:00 数据回灌
│   ├── fetch_planet_content.py        # 星球内容草稿
│   ├── fetch_planet_material.py       # 星球素材
│   ├── fetch_headline_pick.py
│   └── fetch_topics.py
├── state_*.json                        # 去重状态（Actions 自动回写）
├── today_plan.txt                      # 今日计划缓存
└── article_data.json
```

## 为什么用 GitHub Actions

对比一下常见做法：

| 方案 | 要不要服务器 | 要不要保持开机 | 成本 |
|------|------------|--------------|------|
| 本地定时任务 | 不要 | **要**（笔记本合盖就停） | 0 |
| 云函数 | 要 | 不要 | 几块钱/月 |
| **GitHub Actions** | 不要 | **不要** | 0（公开仓库免费额度够用） |

公开仓库的 Actions 免费额度是 2000 分钟/月，这个项目一天跑几十秒，用量在 0.5% 以内。

## License

MIT
