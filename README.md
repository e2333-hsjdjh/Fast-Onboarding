# 简历生成器 MVP

这个项目的目标不是只做一个“把文字塞进模板”的工具，而是做一个面向求职全过程的简历生成系统：从用户素材、岗位 JD、公司与行业情报，到简历生成、ATS 检查、Word/PDF 输出和面试准备，逐步形成闭环。

核心原则：简历生成的内容优先级高于格式。系统应先做好岗位匹配、真实证据、业务痛点回应、量化结果和项目表达，再把内容压入 Markdown、Word 或 PDF 模板。模板不能反过来决定该删掉哪些高价值内容。

## 当前 MVP

MVP 先完成最短可用链路：

1. 用户维护一份结构化、可验证的经历素材库。
2. AI 提取已填事实，识别缺失信息并提出追问。
3. AI 基于用户确认的事实生成待采纳的润色建议稿，不直接覆盖原文。
4. 用户粘贴或导入目标岗位 JD。
5. 系统分析 JD 中的岗位关键词、职责、业务痛点和 ATS 关键词。
6. 系统从用户经历和项目中选择最相关内容。
7. 按内容优先策略生成针对岗位的 Markdown 简历初稿。
8. 输出内容质量报告，提示缺少的真实证据、关键词覆盖和量化结果。
9. 输出 ATS 检查报告，提示缺失关键词和基础风险。
10. 可接入 Word 模板 agent 导出 `.docx`。

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
- `content_report.json`: 内容质量报告，优先检查岗位匹配、真实证据、业务痛点和量化结果。
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

- `users`: 多账号基础信息、头像、目标岗位、语言/时区、偏好、最后登录与活跃时间。
- `user_sessions`: 30 天持久登录会话；同一浏览器会自动恢复账号，不需要反复输入账号密码。
- `resume_material_templates`: 详细素材采集模板，定义每类经历的必填项、证据和量化提示。
- `resume_materials`: 用户长期维护的结构化经历素材，包括原始事实、工具、结果、量化信息和证明材料。
- `application_projects`: 每一份可编辑简历，包括公司、岗位、JD、状态、模板、语言、可见性、已选素材、正文、编辑偏好和导出设置。
- `resume_versions`: 每份简历最近 3 个可恢复正文快照，默认保留 30 天；恢复旧版会产生一个新的当前版本。
- `ai_interactions`: AI 填充、润色、追问和用户采纳状态的审计记录结构。
- `export_jobs`: Word/PDF/分享导出任务、选项、文件路径和完成状态的记录结构。
- `profile_snapshots`: 每次生成时的用户素材快照。
- `job_descriptions`: 每次输入的 JD、目标岗位和 JD 分析结果。
- `resume_generations`: 生成的简历 Markdown、ATS 报告和输出文件路径。

相关 API：

- `POST /api/generate`: 生成简历并保存用户、JD、素材快照和生成记录。
- `POST /api/auth/register`: 注册正式账号并创建会话。
- `POST /api/auth/login`: 登录并创建 30 天会话。
- `GET /api/auth/session/{token}`: 恢复已保存会话。
- `POST /api/auth/test-session`: 进入内置 `test` 测试账号。
- `POST /api/auth/test-reset`: 清空并恢复 `test` 账号的演示数据。
- `GET /api/users/{user_id}`: 查询用户基础信息。
- `POST /api/users/{user_id}/experiences`: 保存一条用户经历。
- `GET /api/users/{user_id}/experiences`: 查询用户经历库。
- `POST /api/users/{user_id}/projects`: 保存一个公司岗位求职项目。
- `GET /api/users/{user_id}/projects`: 查询用户的岗位项目列表。
- `GET /api/users/{user_id}/projects/{project_id}/versions`: 查询当前简历的可恢复版本。
- `POST /api/users/{user_id}/projects/{project_id}/restore`: 恢复指定版本。
- `POST /api/ai/autofill`: 基于用户已输入内容补全经历或岗位项目表单。
- `POST /api/ai/polish-experience`: 仅基于当前经历事实生成待确认的润色建议稿。
- `POST /api/ai/chat`: 基于当前工作区内容给出填写建议、真实性提醒和追问问题。
- `POST /api/ai/chat/stream`: 以 NDJSON 流式返回 AI 回复，前端可边生成边显示。
- `GET /api/users/{user_id}/generations`: 查询用户最近生成历史。

如果部署在 `/resume` 子路径下，API 前缀也对应变为 `/resume/api/...`。

### test 测试账号

开发环境默认提供 `test` 账号，密码为 `test123`。首次打开工作区会自动进入该账号，后续由会话自动恢复，不需要重复登录。顶栏的“重置 test 数据”会清空该账号素材、简历、版本和记录，并创建一份新的演示简历；正式注册账号不会受到影响。

## Word 简历模板

项目内置了一个基于用户提供的 `朱思潮-简历.docx` 制作的中文紧凑表格模板：

```text
src/fast_onboarding/documents/templates/zsc_table_resume.docx
```

模板特点：

- 单页高密度中文表格版式，适合学生、校园经历、媒体/传播/运营方向。
- 保留参考简历的 9 列表格结构、紧凑页边距和分区节奏。
- 已将个人信息和经历内容替换为稳定占位符，例如 `{{name}}`、`{{phone}}`、`{{school}}`、`{{exp1_desc}}`、`{{content}}`。
- 可通过 `register_builtin_templates()` 注册到模板库，再由 `ResumeWordAgent.render()` 写入用户素材。

示例：

```python
from fast_onboarding.documents import (
    BUILTIN_ZSC_TABLE_RESUME_TEMPLATE_ID,
    ResumeWordAgent,
    TemplateRegistry,
    register_builtin_templates,
)

registry = register_builtin_templates(TemplateRegistry("data/templates/registry.json"))
agent = ResumeWordAgent(registry=registry)
agent.render(
    template_id=BUILTIN_ZSC_TABLE_RESUME_TEMPLATE_ID,
    output_docx="workspace/output/resume.docx",
    resume_facts={
        "name": "张三",
        "phone": "13800000000",
        "email": "zhangsan@example.com",
        "role": "新媒体运营",
        "exp1_desc": "负责账号内容策划，单月阅读量提升 35%。",
    },
    target_role="新媒体运营",
)
```

## 功能优先级

### 1. 用户素材库

维护一份长期复用的职业履历数据库，包括基础信息、教育背景、工作经历、项目经历、技能、证书、作品链接和可量化成果。用户不需要每次重写简历，而是持续维护素材。

### 2. 公司岗位项目

用户可以把一个公司的一个岗位设定为一个项目，在项目下保存 JD、状态、备注、生成历史和后续投递反馈。一个用户可以同时维护多个岗位项目。

### 3. JD 解析器

输入岗位 JD，自动提取岗位标题、必备技能、加分项、业务场景、岗位职责、真实业务痛点和 ATS 关键词。

### 4. 简历匹配引擎

根据 JD 和素材库，选择最相关经历，重排内容顺序，突出岗位关键词，并弱化低相关内容。排序规则以内容质量为先：岗位必需关键词、职责/痛点匹配、量化结果和可验证项目证据的权重高于格式长度。

### 5. 简历生成器

生成针对岗位的简历初稿。当前 MVP 输出 Markdown，后续扩展为 Word 和 PDF。生成逻辑先保证内容完整和有说服力，再进入模板压缩和版式优化。

### 6. 内容质量检查

检查简历是否真正回应 JD，包括必需关键词是否有素材支撑、是否有量化结果、是否能回应业务痛点、是否存在只有格式但缺少证据的空表达。

### 7. 真实性优先 AI 助手

这是一个 AI 辅助填充与润色的简历系统，而不是让 AI 代替用户编写人生经历。AI 可以根据用户已经输入的内容提取事实、补全字段结构、生成待确认的润色建议稿，也可以作为聊天机器人提出改进意见和追问问题。

经历弹窗内的 AI 工作流为：先填写真实素材，再点击“AI 提取已填事实”整理已有内容；随后点击“AI 生成润色建议稿”，逐条核对后再点击“采纳润色稿”。建议稿不会静默覆盖原文，也不会直接保存到数据库。

聊天接口支持流式显示，AI 会先逐步返回回复正文，最后返回结构化建议、追问和真实性提醒。

AI 助手内置商业思维 persona skill 路由，来源参考 `tmstack/awesome-persona-skills` 的“商业思维”分类。当前索引包括乔布斯、马斯克、张一鸣、巴菲特、芒格、纳瓦尔、塔勒布、特朗普等视角。系统会根据当前岗位、JD、经历和用户问题自动匹配合适 skill，例如：

- 产品、体验、设计：偏乔布斯视角。
- 工程、成本、自动化：偏马斯克视角。
- 增长、数据、A/B 实验：偏张一鸣视角。
- 商业模式、长期价值：偏巴菲特视角。
- 风险、不确定性、反脆弱：偏塔勒布视角。

这些 skill 只作为“追问和思考框架”，不能覆盖真实性规则，也不能生成未经用户确认的事实。

真实性是硬约束：

- AI 只能整理、结构化、改写或追问用户已经提供的信息。
- AI 不得编造公司、学校、岗位、数字、结果、奖项或经历。
- 缺少信息时必须标记为待补充，或提出问题让用户确认。
- 自动补全不会替用户静默保存事实，用户确认后才进入数据库。

### 8. ATS 友好检查

检查关键词覆盖、联系方式、长度、格式风险和可解析性，给出修改建议。

### 9. 模板库与 Word 编辑 Agent

维护不同岗位的模板，例如产品经理、数据分析、软件工程师、运营、市场、金融、留学申请和学术 CV。Word 编辑 agent 负责把生成内容写入模板。

当前已提供 `zsc_table_resume` 内置模板，后续可以继续扩展为不同角色和行业的模板库。

### 10. 公司研究 Agent

针对目标公司搜索业务、产品线、近期新闻、招聘偏好、文化价值观和面试准备点，让简历表达贴近公司语境。

### 11. 每日 JD 行业痛点雷达

每天自动搜索目标公司发布的 JD，按行业归档和汇总，提炼真实业务痛点，例如效率、增长、风控、成本、转化、用户体验、自动化和 AI 落地。

这个模块的价值是让简历不只“像简历”，而是能反映行业正在招什么、公司真正缺什么、候选人应该强调什么。

### 12. GitHub 行业项目雷达

每天收集 GitHub 上与目标行业、岗位和技术方向相关的高质量项目，归档项目说明、星标、语言、主题和可借鉴点。

这些项目不能被编造成用户经历，但可以用于三类合法加分：

- 作为学习和作品集方向，帮助用户做真实项目。
- 作为简历项目的架构借鉴，优化已有项目表达。
- 作为面试谈资，说明用户理解行业技术趋势。

### 13. 行业情报汇总

把每日 JD 痛点和 GitHub 项目趋势合并，输出行业报告：

- 行业高频痛点
- 高频岗位关键词
- 技术趋势
- 可做的作品集项目
- 简历中应该强化的能力
- 面试中可能被追问的问题

### 14. 中英文简历

同一份素材输出中文和英文简历，不做机械翻译，而是按中英文简历表达习惯分别生成。

### 15. 多版本 A/B 生成

同一个岗位生成不同版本，例如稳健专业版、数据结果版、业务影响版、技术深度版，方便用户对比选择。

### 16. 投递记录管理

记录公司、岗位、JD、简历版本、投递时间、反馈状态和面试结果，后续可以反向优化简历。

### 17. 面试准备包

基于 JD 和最终简历生成自我介绍、项目追问、行为面试题、技术或业务问题，以及反问面试官的问题。

### 18. Web UI

当前 Web UI 已调整为门户 + 工作区结构：

- 门户：简洁展示产品定位，并进入工作区。
- 工作区左侧：用户素材和个人经历库。
- 工作区中间：公司岗位项目、JD 和生成操作。
- AI 助手页：根据当前输入补全结构、提出追问和改进建议。
- 结果页：内容分、ATS 分、内容缺口、最近生成和简历预览。

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
- `fast_onboarding.resume_mvp`: MVP 简历生成链路，包括内容优先的经历排序、内容质量报告和 ATS 检查。

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
