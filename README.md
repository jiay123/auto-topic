# auto-topic · 每天早上把该看的东西推到你微信

一个人做自媒体，最难的不是做内容，是**每天记得该干什么**。今天发第几集？昨天那条数据回了吗？台账里标着"发前必须重做"的是哪一集？星球这周发第几篇？

这个项目把这些琐事变成一条命令：**GitHub Actions 每天定时跑，把当天待办抓到 Server 酱，推到你微信**。你醒来打开手机就有一条消息，不用打开电脑、不用翻台账。

## 它做什么

**一天三次推送**，全部自动抓取 + 自动去重：

| 时间 | 推什么 | 脚本 |
|------|--------|------|
| 06:00 | **今日待办** — 实时读视频台账的「待发排期」表，告诉你今天发哪集、下一集是啥、哪集发前必须重做、哪集已发但缺数据 | `fetch_daily_reminder.py` |
| 07:00 | **AI 资讯头条** — 抓 AI 新闻源，挑出当天最值得看的一条 | `fetch_ai_news.py` |
| 09:00 | **GitHub 项目推荐** — 每天 3 个新项目，带星数、语言、用途 | `fetch_github_projects.py` |

> **诚实说明**：仓库里还有 `fetch_article_pick.py`（今日选题）、`fetch_evening_tip.py`（傍晚提示）、`fetch_daily_review.py`（数据回灌）、`fetch_planet_content.py`（星球草稿）四个脚本，**代码写完了但没有挂进 workflow，所以不会真的推送**。上面这张表只写实际在跑的。

### 06:00 那条是怎么算出待办的

它**不是写死的清单**，每次跑都重新读你的视频台账：

| 读台账哪里 | 得出什么 |
|---|---|
| 「📊 数据统计 › 10月待发排期」表 | 今天该发哪集；今天没排集就告诉你下一集是哪天哪集 |
| 「视频总表」里标着 `老标准`/`待做`/`🔨` 且已排到具体日期的 | 【发前必须重做】——只认已排期的，20-26 那种还没排到日子的候选池不进提醒，免得吵 |
| 「视频总表」里 `已发` 且播放是 `-`、且是 3 天内发的 | 【发完找我要数据】 |

**所以你改台账，这条推送当天就变。** 台账路径走 `LEDGER_PATH` 环境变量，默认指向 `D:\视频探索\视频台账\视频台账.md`。

**踩过的坑（别再犯）**：老版判定"今天要发"靠扫视频总表里的 `待发` 标记，但那一列状态会被改（第16集发完就变 `✅已发`），于是这条推送连续好几天都在报 9 月 25 号的旧内容，等于没推。现在改成读排期表这个唯一真源。

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

## 推送额度：你能用几次

[Server酱Turbo](https://sct.ftqq.com/) 注册即得免费会员，**每天最多 5 条推送**，0 元。另有每分钟 50 条、单 IP 每天 5000 次 API 的上限，正常用碰不到。

**免费版卡在三件事上：**

| | 免费版 | 订阅会员 |
|---|---|---|
| 每天条数 | **5** | 1000 次 API |
| 卡片显示 | **只有标题** | 标题+内容 |
| 推送保留 | **1 天** | 3 天 |

本项目默认三次推送，老贾试过觉得三次刚好（多了他也用不上），**剩下 2 条额度留着不花**。免费额度是白拿的，不用白不用，但也不必硬凑。

订阅是 8 元/月、39 元/年、180 元/5 年。**不建议买**——一天 5 条白拿，真要每天推更多内容，8 块钱买 1000 次也不亏，但那是量上来了再说的事。

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

**注意**：目录里 11 个脚本，但只有 3 个挂在 workflow 里实际运行（`fetch_daily_reminder` / `fetch_ai_news` / `fetch_github_projects`）。其余是写好待启用的，文件名前面没标状态，别照着目录数功能。

`fetch_daily_reminder.py` 的台账列映射（台账共 11 列，0 起算）：`c[0]` 集数 / `c[1]` 标题 / `c[4]` 发布日期 / `c[5]` 发布状态 / `c[6]` 播放。**改台账表格结构就要同步改这里，否则推送变哑。**

## 为什么用 GitHub Actions

对比一下常见做法：

| 方案 | 要不要服务器 | 要不要保持开机 | 成本 |
|------|------------|--------------|------|
| 本地定时任务 | 不要 | **要**（笔记本合盖就停） | 0 |
| 云函数 | 要 | 不要 | 几块钱/月 |
| **GitHub Actions** | 不要 | **不要** | 0（公开仓库免费额度够用） |

公开仓库的 Actions 免费额度是 2000 分钟/月，这个项目一天跑几十秒，用量在 0.5% 以内。

## 成本账

一天 5 次推送 + 三次 Actions 运行，**总共 0 元**：

| 花什么 | 多少钱 |
|--------|--------|
| GitHub Actions（公开仓库 2000 分钟/月免费额度） | 0 |
| Server酱 免费会员 5 条/天 | 0 |
| Python / Node / ffmpeg（都开源） | 0 |
| **合计** | **0** |

**整套东西没有服务器、不用开机、不用备案，一次订阅都不用买。** 这是"用 GitHub Actions 代替自建服务器"最实在的收益。

## License

MIT
