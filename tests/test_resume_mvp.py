import json
import tempfile
import unittest
from pathlib import Path

from fast_onboarding.resume_mvp import (
    CandidateProfile,
    ContentQualityChecker,
    Experience,
    JDAnalyzer,
    JDAnalysis,
    ResumeGenerator,
    ResumeMVPWorkflow,
)


class ResumeMVPTest(unittest.TestCase):
    def test_generates_targeted_resume_and_reports(self):
        profile = CandidateProfile(
            name="张三",
            email="zhangsan@example.com",
            target_title="AI 产品经理",
            skills=["AI", "LLM", "SQL", "用户研究"],
            experiences=[
                Experience(
                    title="AI 简历生成器产品负责人",
                    organization="个人项目",
                    bullets=["负责 JD 解析、ATS 检查和 Word 模板生成"],
                    skills=["AI", "LLM", "ATS"],
                    metrics=["生成效率提升 80%"],
                )
            ],
            projects=[
                Experience(
                    title="GitHub 项目雷达",
                    organization="个人项目",
                    bullets=["自动化归档 GitHub 高星项目"],
                    skills=["GitHub", "自动化"],
                )
            ],
            education=["某大学 本科"],
        )
        jd = "AI 产品经理\n负责 LLM 产品、用户研究、SQL 数据分析和 ATS 优化。"

        with tempfile.TemporaryDirectory() as tmp:
            result = ResumeMVPWorkflow().run(profile=profile, jd_text=jd, output_dir=tmp)
            resume = Path(result["resume_path"]).read_text(encoding="utf-8")
            report = json.loads(Path(result["ats_report_path"]).read_text(encoding="utf-8"))
            content = json.loads(Path(result["content_report_path"]).read_text(encoding="utf-8"))

        self.assertIn("张三", resume)
        self.assertIn("AI 简历生成器产品负责人", resume)
        self.assertGreaterEqual(report["score"], 80)
        self.assertEqual(content["priority"], "content_first")
        self.assertIn("AI 简历生成器产品负责人", content["metric_backed_items"])

    def test_jd_analyzer_extracts_pain_points(self):
        analysis = JDAnalyzer().analyze("负责增长分析，优化用户体验和转化效率。", target_role="增长产品经理")

        self.assertEqual(analysis.target_role, "增长产品经理")
        self.assertIn("增长", analysis.ats_keywords)
        self.assertTrue(analysis.pain_points)

    def test_content_first_selection_prioritizes_evidence_over_format(self):
        profile = CandidateProfile(
            name="李四",
            skills=["增长", "用户研究", "SQL"],
            experiences=[
                Experience(
                    title="格式规范项目",
                    organization="个人项目",
                    bullets=["整理 Word 模板和页面样式"],
                    skills=["Word"],
                ),
                Experience(
                    title="增长实验平台",
                    organization="实习项目",
                    bullets=["分析转化漏斗，定位新用户留存问题"],
                    skills=["增长", "用户研究", "SQL"],
                    metrics=["转化率提升 18%，分析周期从 3 天压缩到 1 天"],
                ),
            ],
        )
        analysis = JDAnalysis(
            target_role="增长产品经理",
            required_keywords=["增长", "用户研究", "SQL"],
            preferred_keywords=[],
            responsibilities=["分析转化漏斗，优化用户增长"],
            pain_points=["留存问题", "转化效率"],
            ats_keywords=["增长", "SQL"],
        )

        resume = ResumeGenerator().generate_markdown(profile, analysis)

        self.assertIn("增长实验平台", resume)
        self.assertNotIn("格式规范项目", resume)
        self.assertIn("转化率提升 18%", resume)

    def test_content_quality_checker_reports_content_gaps(self):
        profile = CandidateProfile(
            name="王五",
            experiences=[Experience(title="文档排版", organization="个人项目", bullets=["调整模板样式"])],
        )
        analysis = JDAnalysis(
            target_role="AI 产品经理",
            required_keywords=["LLM", "用户研究"],
            preferred_keywords=[],
            responsibilities=[],
            pain_points=["转化效率"],
            ats_keywords=["LLM"],
        )

        report = ContentQualityChecker().check(profile, analysis, "# 王五\n\n模板样式")

        self.assertEqual(report["priority"], "content_first")
        self.assertIn("LLM", report["missing_required_keywords"])
        self.assertTrue(report["content_gaps"])


if __name__ == "__main__":
    unittest.main()
