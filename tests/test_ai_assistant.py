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


if __name__ == "__main__":
    unittest.main()
