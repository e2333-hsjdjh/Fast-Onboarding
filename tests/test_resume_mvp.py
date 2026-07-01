import json
import tempfile
import unittest
from pathlib import Path

from utils.resume_mvp import (
    CandidateProfile,
    Experience,
    JDAnalyzer,
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

        self.assertIn("张三", resume)
        self.assertIn("AI 简历生成器产品负责人", resume)
        self.assertGreaterEqual(report["score"], 80)

    def test_jd_analyzer_extracts_pain_points(self):
        analysis = JDAnalyzer().analyze("负责增长分析，优化用户体验和转化效率。", target_role="增长产品经理")

        self.assertEqual(analysis.target_role, "增长产品经理")
        self.assertIn("增长", analysis.ats_keywords)
        self.assertTrue(analysis.pain_points)


if __name__ == "__main__":
    unittest.main()
