import unittest

from fast_onboarding.web.persona_skills import PersonaSkillRouter


class PersonaSkillRouterTest(unittest.TestCase):
    def test_selects_growth_and_product_skills_from_context(self):
        router = PersonaSkillRouter()

        selected = router.select(
            {"project": {"role_title": "增长产品经理", "jd_text": "负责 A/B 实验、用户增长和数据指标"}},
            "请帮我检查商业思维",
        )

        self.assertEqual(selected[0].skill_id, "zhang_yiming")

    def test_selects_engineering_skill_from_automation_context(self):
        router = PersonaSkillRouter()

        selected = router.select({"experience": {"bullets": ["搭建自动化系统，降低成本"]}}, "")

        self.assertEqual(selected[0].skill_id, "elon_musk")


if __name__ == "__main__":
    unittest.main()
