# Resume MVP

## Request

生成一个简历生成器 MVP，把上一轮建议的扩展方向写入 README，并按建议顺序排序。同时补充每日自动搜索公司 JD、理解行业真实痛点、结合 GitHub 项目了解行业动态并作为简历加分项的产品想法。

## Architecture Snapshot

- Entry points: 当前主要入口是 Python 模块和新增 CLI `scripts/resume_mvp.py`。
- Relevant modules: `utils.resume_mvp` 负责素材库、JD 分析、简历生成和 ATS 检查；`utils.industry_monitor` 负责每日 JD 与 GitHub 行业信号汇总；已有 `company_search` 和 `github_project_archiver` 被复用为情报来源。
- Data/control flow: 用户素材 JSON 与 JD 文本输入 CLI，经过 JD 分析、素材匹配、Markdown 简历生成、ATS 检查，输出到指定目录。行业监控按行业、公司、GitHub 查询收集信号，再归档 JSON 报告。
- Dependencies or integration points: 规则模式不依赖网络；接入 DeepSeek 后可增强 JD 解析、简历润色和行业总结；真实搜索源可替换为更稳定的招聘网站/API provider。
- Risks or unknowns: MVP 先输出 Markdown，Word/PDF 导出仍需接入模板 agent；每日自动化调度尚未加入系统级定时任务。

## Execution Plan

1. 新增 MVP 数据模型、素材库、JD 分析器、简历生成器和 ATS 检查器。
2. 新增每日行业监控模块，复用公司搜索与 GitHub 归档能力。
3. 新增 CLI 示例入口与样例 profile/JD。
4. 编写 README，按产品建设优先级整理功能路线。
5. 补充单元测试和端到端 smoke test。

## Changes Applied

- `utils/resume_mvp.py`: 新增 MVP 简历生成链路。
- `utils/industry_monitor.py`: 新增每日 JD 与 GitHub 行业信号汇总模块。
- `scripts/resume_mvp.py`: 新增命令行入口。
- `examples/profile.sample.json`: 新增候选人素材样例。
- `examples/jd.sample.txt`: 新增 JD 样例。
- `README.md`: 新增产品说明、MVP 使用方式、功能优先级和行业情报设计。
- `tests/test_resume_mvp.py`: 覆盖 MVP 生成链路和 JD 痛点提取。
- `tests/test_industry_monitor.py`: 覆盖行业信号收集和归档。

## Verification

- 已运行：`python3 -m unittest discover -s tests`
- 结果：8 个单元测试全部通过。
- 已运行：`python3 scripts/resume_mvp.py --profile examples/profile.sample.json --jd examples/jd.sample.txt --output-dir workspace/mvp-output --target-role "AI 产品经理"`
- 结果：成功生成 `resume.md`、`jd_analysis.json`、`ats_report.json`，示例 ATS 分数为 92。

## Remaining Risks

- 真实每日自动搜索需要后续增加调度器、招聘源适配器和去重策略。
- GitHub 项目只能作为学习、作品集和表达借鉴，不能替代用户真实经历。
