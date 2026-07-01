# Project Structure Refactor

## Request

用户希望重构项目结构，让简历生成器项目更加规范化。

## Architecture Snapshot

- Entry points: 重构前主要入口为 `scripts/resume_mvp.py`，业务模块平铺在 `utils/`。
- Relevant modules: `utils` 同时包含配置、DeepSeek 客户端、公司搜索、GitHub 项目归档、行业监控、用户用量控制、Word 模板编辑和 MVP workflow。
- Data/control flow: CLI 读取 profile JSON 和 JD 文本，调用 MVP workflow，输出简历、JD 分析和 ATS 报告。
- Dependencies or integration points: 当前仍以标准库为主，DeepSeek/GitHub/搜索能力通过可注入客户端隔离。
- Risks or unknowns: 直接移动模块会破坏旧导入，因此需要兼容层。

## Execution Plan

1. 建立标准 `src/fast_onboarding` 包结构。
2. 按职责拆分为 `core`、`integrations`、`intelligence`、`documents`、`cli`。
3. 更新模块间导入、CLI 入口和 `pyproject.toml`。
4. 保留 `utils/` 作为旧导入兼容层。
5. 更新 README 和测试导入。
6. 运行单元测试、脚本 CLI 和包内 CLI 验证。

## Changes Applied

- `src/fast_onboarding/core/`: 放置配置和用户用量控制。
- `src/fast_onboarding/integrations/`: 放置 DeepSeek 客户端。
- `src/fast_onboarding/intelligence/`: 放置公司搜索、GitHub 项目归档和行业监控。
- `src/fast_onboarding/documents/`: 放置 Word 模板和文档编辑 agent。
- `src/fast_onboarding/cli/`: 放置包内 CLI。
- `src/fast_onboarding/resume_mvp.py`: 保留 MVP 主 workflow。
- `utils/`: 改为兼容导入层，旧代码仍可导入 `utils.*`。
- `scripts/resume_mvp.py`: 改为 CLI 兼容 wrapper。
- `pyproject.toml`: 更新项目名、构建配置、包发现和 console script。
- `README.md`: 更新项目结构和运行方式。
- `tests/`: 改为优先测试 `fast_onboarding.*` 新路径，并补充兼容层测试。

## Verification

- 已运行：`python3 -m unittest discover -s tests`
- 结果：10 个单元测试全部通过。
- 已运行：`python3 scripts/resume_mvp.py --profile examples/profile.sample.json --jd examples/jd.sample.txt --output-dir workspace/mvp-output --target-role "AI 产品经理"`
- 结果：成功生成示例简历、JD 分析和 ATS 报告，示例 ATS 分数为 92。
- 已运行：`PYTHONPATH=src python3 -m fast_onboarding.cli.resume_mvp --profile examples/profile.sample.json --jd examples/jd.sample.txt --output-dir workspace/mvp-output-module --target-role "AI 产品经理"`
- 结果：包内 CLI 成功运行。

## Remaining Risks

- `utils/` 兼容层后续可以在外部调用方完成迁移后删除。
- 当前未引入格式化和静态检查工具，后续可补 `ruff`、`mypy` 或 CI。
