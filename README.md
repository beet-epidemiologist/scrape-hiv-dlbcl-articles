# HIV / DLBCL 每日自动文献监测器（API 增量版）

这是一个面向科研监测场景的 **医学文献增量监测项目**，不是普通网页爬虫。项目每天自动运行（也支持手动触发），从官方 API 获取 HIV 相关 DLBCL 最新文献，做去重、评分、分层，并生成日报。

> 重要说明：
> - 本项目主要抓取 **文献元数据 + 摘要**，不抓全文。
> - PubMed 主要提供 citation / abstract，并不等于全文数据库。
> - 正式全文通常需要跳转到 PMC 或出版社页面查看。

---

## 1. 项目简介

项目目标：
- 每日自动监测 HIV 相关 DLBCL 最新文献；
- 仅输出“历史未见过”的新记录；
- 自动生成 `Markdown + CSV` 日报；
- 可选邮件通知；
- 便于后续扩展到其他疾病主题。

数据来源（官方 API）：
- PubMed（NCBI E-utilities，主来源）
- Europe PMC REST API
- Crossref REST API（补充来源，带 `mailto`）
- medRxiv / bioRxiv API（预印本来源）

---

## 2. 医学文献监测模式（不是普通关键词检索）

本项目采用“监测模式”：
1. PubMed 以 `Create Date [crdt]` 为主。
2. 默认核心窗口为最近 14 天（部分补强查询 30/180 天）。
3. 只输出历史未见的新记录。
4. 双层检索策略：
   - 第一层：Title/Abstract 敏感检索（优先发现最新）
   - 第二层：MeSH / 主题词 + 综述/指南补强（提高精准性）
5. 所有记录统一计算 `relevance_score` 并排序。

---

## 3. 为什么用 `[crdt]`

在“每日/每周滚动监测”中，`[crdt]` 更适合发现 **最近新增到 PubMed 的可见记录**：
- `[crdt]` 反映“进入数据库的时间”；
- 如果只用 `[dp]`（发表日期），可能漏掉“较早发表，但最近才被收录”的条目；
- 因此监测新增文献时 `[crdt]` 更稳妥。

---

## 4. 为什么不能只依赖 MeSH / Publication Type

新文献在刚进入数据库时，可能还没有完成：
- MeSH 索引；
- Publication Type 标注。

若只依赖 MeSH/PT，容易漏掉最新记录。因此本项目采用：
- Title/Abstract 敏感检索（抓新）；
- MeSH/PT 精准补强（提质）。

---

## 5. 项目结构

```text
.
├── .github/workflows/daily-literature-monitor.yml
├── config/
│   ├── queries.yaml
│   └── search_terms.yaml
├── data/seen_ids.json
├── reports/
├── src/
│   ├── main.py
│   ├── config.py
│   ├── dedupe.py
│   ├── models.py
│   ├── monitoring_mode.py
│   ├── notifier.py
│   ├── reporters.py
│   ├── utils.py
│   └── sources/
│       ├── pubmed.py
│       ├── europe_pmc.py
│       ├── crossref.py
│       └── rxiv.py
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

---

## 6. 快速开始

### 6.1 环境准备

- Python 3.11

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 6.2 配置环境变量

```bash
cp .env.example .env
```

`.env` 最少可配置：
- `MONITOR_LOOKBACK_DAYS=14`（统一监测窗口，Europe PMC / Crossref / Rxiv 共用）
- `CROSSREF_MAILTO=you@example.com`（建议填写，Crossref 补充源会使用）
- 邮件通知相关（可不填，不填会自动跳过）：
  - `EMAIL_HOST`
  - `EMAIL_PORT`
  - `EMAIL_USER`
  - `EMAIL_PASSWORD`
  - `EMAIL_TO`

### 6.3 手动运行

```bash
python -m src.main
```

运行后会生成：
- `reports/daily_YYYY-MM-DD.md`
- `reports/daily_YYYY-MM-DD.csv`

并更新去重记录：
- `data/seen_ids.json`

---

## 7. 输出说明

每次日报按以下结构组织：
1. 正式发表论文
2. 预印本（medRxiv / bioRxiv）

每个分区再按相关性分层：
- 高相关（score >= 8）
- 中相关（score 5-7）
- 低相关（score < 5）

每篇文献包含：
- title
- authors
- journal/source
- publication date
- DOI
- PMID/PMCID（如有）
- abstract（尽量获取）
- url
- source database
- relevance_score
- tags

单一数据源失败不会导致整体任务失败，失败源会在日报中标注。

---

## 8. GitHub Actions 自动运行说明

工作流：`.github/workflows/daily-literature-monitor.yml`

特性：
- 支持 `workflow_dispatch` 手动触发
- 每天自动运行（Cron 使用 UTC 01:00，对应 Asia/Taipei 09:00）
- 上传 `reports/` 为 artifact（保留 7 天）
- 如果 `reports/` 或 `data/seen_ids.json` 有变化，自动提交回仓库
- 使用 `concurrency` 避免重复运行

---

## 9. 环境变量说明

| 变量名 | 是否必填 | 说明 |
|---|---|---|
| `CROSSREF_MAILTO` | 建议 | Crossref API 联系参数 |
| `EMAIL_HOST` | 可选 | SMTP 主机 |
| `EMAIL_PORT` | 可选 | SMTP 端口 |
| `EMAIL_USER` | 可选 | SMTP 用户 |
| `EMAIL_PASSWORD` | 可选 | SMTP 密码 |
| `EMAIL_TO` | 可选 | 收件人 |

未配置完整邮件参数时，程序会直接跳过邮件发送，不报错。

---

## 10. 注意事项

- 建议优先把本项目作为“最新文献线索监测器”，再对高分条目人工复核。
- API 返回的摘要完整性受来源限制，可能存在缺失。
- 去重优先级为 DOI > PMID/PMCID > 规范化标题匹配。
- 这是 MVP 版本，强调稳定可运行与可维护。

---

## 后续可扩展方向

- 增加更多疾病模板（仅替换 `config/search_terms.yaml` + 查询模板即可）
- 加入 Slack / Teams / 企业微信通知
- 引入更细颗粒度的“证据等级”规则
- 加入多天趋势统计（周报 / 月报）
