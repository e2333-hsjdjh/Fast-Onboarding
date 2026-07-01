# 简历生成器 MVP

这个项目的目标不是只做一个“把文字塞进模板”的工具，而是做一个面向求职全过程的简历生成系统：从用户素材、岗位 JD、公司与行业情报，到简历生成、ATS 检查、Word/PDF 输出和面试准备，逐步形成闭环。

## 当前 MVP

MVP 先完成最短可用链路：

1. 用户维护一份结构化素材库。
2. 粘贴或导入目标岗位 JD。
3. 系统分析 JD 中的岗位关键词、职责、业务痛点和 ATS 关键词。
4. 系统从用户经历和项目中选择最相关内容。
5. 生成针对岗位的 Markdown 简历初稿。
6. 输出 ATS 检查报告，提示缺失关键词和基础风险。
7. 后续可接入 Word 模板 agent 导出 `.docx`。

运行示例：

```bash
python3 scripts/resume_mvp.py \
  --profile examples/profile.sample.json \
  --jd examples/jd.sample.txt \
  --output-dir workspace/mvp-output \
  --target-role "AI 产品经理"
```

如果已经安装为包，或在开发环境中设置了 `PYTHONPATH=src`，也可以使用包内 CLI：

```bash
PYTHONPATH=src python3 -m fast_onboarding.cli.resume_mvp \
  --profile examples/profile.sample.json \
  --jd examples/jd.sample.txt \
  --output-dir workspace/mvp-output \
  --target-role "AI 产品经理"
```

输出文件：

- `resume.md`: 针对岗位生成的简历初稿。
- `jd_analysis.json`: JD 结构化分析结果。
- `ats_report.json`: ATS 关键词覆盖和格式风险报告。

## Web UI

项目提供一个无前端构建依赖的原生 Web UI，适合直接放在服务器上由 nginx 反向代理。

本地启动：

```bash
python3 scripts/serve_web.py --host 127.0.0.1 --port 8787
```

访问：

```text
http://127.0.0.1:8787/
```

nginx 子路径反代启动方式：

```bash
PYTHONPATH=src python3 -m fast_onboarding.cli.web \
  --host 127.0.0.1 \
  --port 8787 \
  --base-path /resume
```

nginx 示例配置在：

```text
deploy/nginx/fast-onboarding.conf
```

关键兼容点：

- 应用默认绑定 `127.0.0.1`，适合只暴露给 nginx。
- `--base-path /resume` 支持部署在网站子路径下。
- 前端资源和 API 使用相同 base path，不依赖根路径 `/`。
- 后端读取 `X-Forwarded-Proto`、`X-Forwarded-Host`、`X-Forwarded-Prefix`，便于后续生成外部链接。
- 健康检查接口：`/api/health`，子路径部署时为 `/resume/api/health`。

## 用户数据库

Web UI 默认使用 SQLite 保存用户相关数据：

```text
data/fast_onboarding.sqlite3
```

可在启动时指定数据库位置：

```bash
python3 scripts/serve_web.py \
  --host 127.0.0.1 \
  --port 8787 \
  --base-path /resume \
  --database data/fast_onboarding.sqlite3
```

当前保存的数据：

- `users`: 用户基础信息，包括姓名、邮箱、电话、城市、目标岗位。
- `profile_snapshots`: 每次生成时的用户素材快照。
- `job_descriptions`: 每次输入的 JD、目标岗位和 JD 分析结果。
- `resume_generations`: 生成的简历 Markdown、ATS 报告和输出文件路径。

相关 API：

- `POST /api/generate`: 生成简历并保存用户、JD、素材快照和生成记录。
- `GET /api/users/{user_id}`: 查询用户基础信息。
- `GET /api/users/{user_id}/generations`: 查询用户最近生成历史。

如果部署在 `/resume` 子路径下，API 前缀也对应变为 `/resume/api/...`。

## 功能优先级

### 1. 用户素材库

维护一份长期复用的职业履历数据库，包括基础信息、教育背景、工作经历、项目经历、技能、证书、作品链接和可量化成果。用户不需要每次重写简历，而是持续维护素材。

### 2. JD 解析器

输入岗位 JD，自动提取岗位标题、必备技能、加分项、业务场景、岗位职责、真实业务痛点和 ATS 关键词。

### 3. 简历匹配引擎

根据 JD 和素材库，选择最相关经历，重排内容顺序，突出岗位关键词，并弱化低相关内容。

### 4. 简历生成器

生成针对岗位的简历初稿。当前 MVP 输出 Markdown，后续扩展为 Word 和 PDF。

### 5. ATS 友好检查

检查关键词覆盖、联系方式、长度、格式风险和可解析性，给出修改建议。

### 6. 模板库与 Word 编辑 Agent

维护不同岗位的模板，例如产品经理、数据分析、软件工程师、运营、市场、金融、留学申请和学术 CV。Word 编辑 agent 负责把生成内容写入模板。

### 7. 公司研究 Agent

针对目标公司搜索业务、产品线、近期新闻、招聘偏好、文化价值观和面试准备点，让简历表达贴近公司语境。

### 8. 每日 JD 行业痛点雷达

每天自动搜索目标公司发布的 JD，按行业归档和汇总，提炼真实业务痛点，例如效率、增长、风控、成本、转化、用户体验、自动化和 AI 落地。

这个模块的价值是让简历不只“像简历”，而是能反映行业正在招什么、公司真正缺什么、候选人应该强调什么。

### 9. GitHub 行业项目雷达

每天收集 GitHub 上与目标行业、岗位和技术方向相关的高质量项目，归档项目说明、星标、语言、主题和可借鉴点。

这些项目不能被编造成用户经历，但可以用于三类合法加分：

- 作为学习和作品集方向，帮助用户做真实项目。
- 作为简历项目的架构借鉴，优化已有项目表达。
- 作为面试谈资，说明用户理解行业技术趋势。

### 10. 行业情报汇总

把每日 JD 痛点和 GitHub 项目趋势合并，输出行业报告：

- 行业高频痛点
- 高频岗位关键词
- 技术趋势
- 可做的作品集项目
- 简历中应该强化的能力
- 面试中可能被追问的问题

### 11. 中英文简历

同一份素材输出中文和英文简历，不做机械翻译，而是按中英文简历表达习惯分别生成。

### 12. 多版本 A/B 生成

同一个岗位生成不同版本，例如稳健专业版、数据结果版、业务影响版、技术深度版，方便用户对比选择。

### 13. 投递记录管理

记录公司、岗位、JD、简历版本、投递时间、反馈状态和面试结果，后续可以反向优化简历。

### 14. 面试准备包

基于 JD 和最终简历生成自我介绍、项目追问、行为面试题、技术或业务问题，以及反问面试官的问题。

### 15. Web UI

最终产品形态建议是一个工作台：

- 左侧：素材库和历史版本。
- 中间：JD、公司信息和行业情报。
- 右侧：简历预览、ATS 分数和导出按钮。

## 项目结构

项目使用标准 `src` layout，核心包名为 `fast_onboarding`：

```text
src/fast_onboarding/
  core/              # 配置、用户用量控制等基础能力
  integrations/      # DeepSeek 等外部服务客户端
  intelligence/      # 公司搜索、GitHub 项目归档、行业趋势监控
  documents/         # Word 模板和文档编辑能力
  web/               # 原生 Web UI 与 JSON API
  cli/               # 命令行入口
  resume_mvp.py      # MVP 简历生成主 workflow
```

主要模块：

- `fast_onboarding.core.config`: 统一 DeepSeek API 配置。
- `fast_onboarding.core.user_database`: 用户、JD、生成历史的 SQLite 持久化。
- `fast_onboarding.core.usage_limiter`: 用户用量控制。
- `fast_onboarding.integrations.deepseek_client`: DeepSeek API 客户端。
- `fast_onboarding.intelligence.github_project_archiver`: GitHub 项目收集和归档。
- `fast_onboarding.intelligence.company_search`: 公司信息统一搜索。
- `fast_onboarding.intelligence.industry_monitor`: 每日 JD 和 GitHub 行业趋势监控。
- `fast_onboarding.documents.resume_word_agent`: 模板注册和 Word 占位符替换。
- `fast_onboarding.web.server`: Web UI server 和 JSON API。
- `fast_onboarding.resume_mvp`: MVP 简历生成链路。

`utils/` 目前保留为兼容层，旧代码仍可继续导入 `utils.resume_mvp` 等模块；新代码建议直接使用 `fast_onboarding.*`。

## 配置

真实 API key 不写入源码。使用环境变量：

```bash
export DEEPSEEK_API_KEY="你的 DeepSeek API Key"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export DEEPSEEK_MODEL="deepseek-chat"
```

## 测试

```bash
python3 -m unittest discover -s tests
```
