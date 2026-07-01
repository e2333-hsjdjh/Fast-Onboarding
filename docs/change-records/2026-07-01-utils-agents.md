# Utils Agents

## Request

为简历生成器新建 `utils` 文件夹，加入四类工具：自动化收集并归档 GitHub 好项目、全网挖掘特定公司信息的统一搜索、用户使用量控制、简历模板与 Word 编辑 agent。统一使用 DeepSeek API，并参考 GitHub 上项目收集方法完成细化、实现与测试。

## Architecture Snapshot

- Entry points: 当前仓库没有业务代码入口，是一个空 Git 仓库；本次新增 Python `utils` 包作为可导入工具入口。
- Relevant modules: `utils.config` 统一 DeepSeek 配置；`utils.deepseek_client` 封装 OpenAI 兼容 chat completions；四个工具模块分别负责 GitHub 归档、公司搜索、用量控制、模板/Word 编辑。
- Data/control flow: 调用方创建共享 `DeepSeekClient`，传入需要 LLM 总结或编辑计划的工具；联网工具支持注入 HTTP 函数，测试中不访问真实网络。
- Dependencies or integration points: DeepSeek API、GitHub REST Search API、DuckDuckGo HTML 搜索、SQLite、DOCX zip/xml 结构。源码不硬编码真实 API key，统一读取 `DEEPSEEK_API_KEY`。
- Risks or unknowns: 公司“全网搜索”默认 provider 是轻量 HTML 搜索，生产环境可替换为 Bing/Brave/SerpAPI；DOCX 编辑支持简单占位符替换，复杂 Word 样式编辑需要后续引入更强的文档处理层。

## Execution Plan

1. 确认仓库为空，采用独立 Python 工具包结构。
2. 新增 DeepSeek 配置和标准库 HTTP 客户端。
3. 实现 GitHub 项目搜索、评分、归档。
4. 实现公司信息统一搜索、DeepSeek 汇总和归档。
5. 实现 SQLite 用户日用量限制。
6. 实现模板注册和 DOCX 占位符替换 agent。
7. 为每个模块补充离线单元测试。

## Changes Applied

- `utils/config.py`: 统一读取 DeepSeek API key、base URL、模型和超时配置。
- `utils/deepseek_client.py`: 新增 DeepSeek chat completions 客户端。
- `utils/github_project_archiver.py`: 新增 GitHub 项目收集、评分、JSON/JSONL/README 归档。
- `utils/company_search.py`: 新增公司信息搜索、DeepSeek 汇总、JSON 归档。
- `utils/usage_limiter.py`: 新增 SQLite 用量控制与 quota 检查。
- `utils/resume_word_agent.py`: 新增模板注册、DOCX 文本替换和 DeepSeek 替换计划 agent。
- `tests/`: 覆盖核心模块的离线单元测试。
- `.env.example`: 记录本地环境变量配置方式，不写入真实密钥。

## Verification

- 已运行：`python3 -m unittest discover -s tests`
- 结果：5 个单元测试全部通过。

## Remaining Risks

- 真实 DeepSeek/GitHub/搜索请求未在单元测试中调用，需在配置环境变量后做集成 smoke test。
- 当前 Word agent 面向模板占位符替换，若要编辑复杂段落、表格、页眉页脚，应升级为基于 `python-docx` 或专用文档服务的实现。
