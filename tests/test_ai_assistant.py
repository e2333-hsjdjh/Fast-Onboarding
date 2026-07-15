import unittest

from fast_onboarding.web.ai_assistant import AUTHENTICITY_NOTICE, WorkspaceAIAssistant


class WorkspaceAIAssistantTest(unittest.TestCase):
    def test_autofill_uses_existing_evidence_and_marks_missing_metrics(self):
        assistant = WorkspaceAIAssistant()

        result = assistant.autofill(
            {
                "experience": {
                    "title": "AI 简历生成器",
                    "organization": "个人项目",
                    "bullets": ["负责 DeepSeek 驱动的简历改写 agent"],
                    "metrics": [],
                }
            },
            target="experience",
        )

        self.assertIn("负责 DeepSeek 驱动的简历改写 agent", result["suggested_fields"]["bullets"])
        self.assertIn("量化结果", result["missing_information"])
        self.assertIn("DeepSeek", result["suggested_fields"]["skills"])
        self.assertEqual(result["authenticity_notice"], AUTHENTICITY_NOTICE)

    def test_chat_gives_questions_instead_of_inventing_facts(self):
        assistant = WorkspaceAIAssistant()

        result = assistant.chat({"experience": {"bullets": ["负责项目"]}}, "怎么写得更好？")

        self.assertTrue(result["suggestions"])
        self.assertTrue(result["questions"])
        self.assertTrue(result["selected_skills"])
        self.assertIn("不得编造", result["authenticity_notice"])

    def test_string_suggestions_are_not_split_into_characters(self):
        assistant = WorkspaceAIAssistant()

        result = assistant._coerce_list("请补充真实数字")

        self.assertEqual(result, ["请补充真实数字"])

    def test_chat_stream_emits_start_delta_and_final_events(self):
        assistant = WorkspaceAIAssistant()

        events = list(assistant.chat_stream({"experience": {"bullets": ["负责项目"]}}, "怎么写？"))

        self.assertEqual(events[0]["type"], "start")
        self.assertTrue(any(event["type"] == "delta" for event in events))
        self.assertEqual(events[-1]["type"], "final")
        self.assertIn("ai", events[-1])

    def test_sanitizes_invented_example_numbers(self):
        assistant = WorkspaceAIAssistant()

        result = assistant._sanitize_chat_payload(
            {"experience": {"bullets": ["负责项目"]}},
            {
                "reply": "ok",
                "suggestions": ["例如：把效率提升 30% 写进去。"],
                "questions": [],
            },
        )

        self.assertEqual(result["suggestions"], ["建议补充真实可核实数字，但不要使用 AI 示例百分比、数量或结果。"])

    def test_polish_returns_reviewable_existing_facts_only(self):
        assistant = WorkspaceAIAssistant()

        result = assistant.polish_experience(
            {
                "experience": {
                    "bullets": ["使用 SQL 分析用户漏斗", "完成周度复盘报告"],
                    "metrics": [],
                }
            }
        )

        self.assertEqual(result["polished_bullets"], ["使用 SQL 分析用户漏斗", "完成周度复盘报告"])
        self.assertTrue(result["requires_confirmation"])
        self.assertTrue(result["questions"])
        self.assertEqual(result["authenticity_notice"], AUTHENTICITY_NOTICE)

    def test_polish_does_not_create_content_when_no_facts_exist(self):
        assistant = WorkspaceAIAssistant()

        result = assistant.polish_experience({"experience": {}})

        self.assertEqual(result["polished_bullets"], [])
        self.assertTrue(result["questions"])

    def test_polish_rejects_unsupported_stronger_claims(self):
        assistant = WorkspaceAIAssistant()

        result = assistant._sanitize_polish_payload(
            {"experience": {"bullets": ["负责 SQL 数据分析"]}},
            {
                "summary": "主导分析并显著提升业务效率",
                "polished_bullets": ["主导 SQL 数据分析，显著提升业务效率"],
            },
        )

        self.assertEqual(result["polished_bullets"], ["负责 SQL 数据分析"])
        self.assertEqual(result["summary"], "以下建议稿只整理你已填写的事实，请核对后再采纳。")


if __name__ == "__main__":
    unittest.main()
