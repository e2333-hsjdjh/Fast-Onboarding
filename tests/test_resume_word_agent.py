import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from fast_onboarding.documents.resume_word_agent import (
    BUILTIN_ZSC_TABLE_RESUME_TEMPLATE_ID,
    ResumeTemplate,
    ResumeWordAgent,
    TemplateRegistry,
    builtin_template_path,
    register_builtin_templates,
)


class ResumeWordAgentTest(unittest.TestCase):
    def test_registers_template_and_replaces_docx_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "template.docx"
            with zipfile.ZipFile(source, "w") as archive:
                archive.writestr("word/document.xml", "<w:document>{{name}} - {{summary}}</w:document>")

            registry = TemplateRegistry(tmp_path / "registry.json")
            registry.add(
                ResumeTemplate(
                    template_id="basic",
                    name="Basic",
                    path=str(source),
                    tags=["pm"],
                )
            )
            agent = ResumeWordAgent(registry=registry)
            output = agent.render(
                template_id="basic",
                output_docx=tmp_path / "out.docx",
                resume_facts={"name": "Alice", "summary": "Product manager"},
                target_role="PM",
            )

            self.assertTrue(output.exists())
            with zipfile.ZipFile(output) as archive:
                xml = archive.read("word/document.xml").decode("utf-8")
            self.assertIn("Alice - Product manager", xml)
            payload = json.loads((tmp_path / "registry.json").read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["template_id"], "basic")

    def test_registers_and_renders_builtin_zsc_table_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            registry = register_builtin_templates(TemplateRegistry(tmp_path / "registry.json"))
            template = registry.get(BUILTIN_ZSC_TABLE_RESUME_TEMPLATE_ID)
            self.assertEqual(Path(template.path), builtin_template_path())
            self.assertTrue(Path(template.path).exists())

            output = ResumeWordAgent(registry=registry).render(
                template_id=BUILTIN_ZSC_TABLE_RESUME_TEMPLATE_ID,
                output_docx=tmp_path / "zsc-rendered.docx",
                resume_facts={
                    "name": "张三",
                    "phone": "13800000000",
                    "email": "zhangsan@example.com",
                    "city": "上海",
                    "role": "新媒体运营",
                    "school": "某某大学",
                    "exp1_desc": "负责账号内容策划，单月阅读量提升 35%。",
                    "content": "熟悉公众号、短视频和活动稿件写作。",
                },
                target_role="新媒体运营",
            )

            with zipfile.ZipFile(output) as archive:
                xml = archive.read("word/document.xml").decode("utf-8")
            self.assertIn("张三", xml)
            self.assertIn("zhangsan@example.com", xml)
            self.assertIn("新媒体运营", xml)
            self.assertNotIn("{{name}}", xml)


if __name__ == "__main__":
    unittest.main()
