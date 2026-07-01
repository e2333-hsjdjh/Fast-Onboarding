import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from fast_onboarding.documents.resume_word_agent import ResumeTemplate, ResumeWordAgent, TemplateRegistry


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


if __name__ == "__main__":
    unittest.main()
