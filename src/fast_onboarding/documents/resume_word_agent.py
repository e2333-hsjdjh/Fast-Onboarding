"""Resume template registry and DOCX editing agent."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import tempfile
import zipfile
from xml.sax.saxutils import escape

from fast_onboarding.integrations.deepseek_client import DeepSeekClient


BUILTIN_ZSC_TABLE_RESUME_TEMPLATE_ID = "zsc_table_resume"


@dataclass(frozen=True)
class ResumeTemplate:
    template_id: str
    name: str
    path: str
    tags: list[str]
    description: str = ""


class TemplateRegistry:
    """JSON-backed registry for resume templates."""

    def __init__(self, registry_path: str | Path = "data/templates/registry.json") -> None:
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, template: ResumeTemplate) -> None:
        templates = {item.template_id: item for item in self.list_templates()}
        templates[template.template_id] = template
        self._write(list(templates.values()))

    def get(self, template_id: str) -> ResumeTemplate:
        for template in self.list_templates():
            if template.template_id == template_id:
                return template
        raise KeyError(template_id)

    def list_templates(self, *, tag: str | None = None) -> list[ResumeTemplate]:
        if not self.registry_path.exists():
            return []
        raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
        templates = [ResumeTemplate(**item) for item in raw]
        if tag:
            return [template for template in templates if tag in template.tags]
        return templates

    def _write(self, templates: list[ResumeTemplate]) -> None:
        payload = [template.__dict__ for template in templates]
        self.registry_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def builtin_template_path(template_filename: str = "zsc_table_resume.docx") -> Path:
    """Return the path to a packaged Word resume template."""
    return Path(__file__).with_name("templates") / template_filename


def builtin_resume_templates() -> list[ResumeTemplate]:
    """Built-in resume templates that ship with the project."""
    return [
        ResumeTemplate(
            template_id=BUILTIN_ZSC_TABLE_RESUME_TEMPLATE_ID,
            name="朱思潮同款紧凑表格简历模板",
            path=str(builtin_template_path()),
            tags=["zh", "student", "media", "compact", "table"],
            description="基于用户提供的 Word 简历制作，保留单页高密度中文表格版式，并替换为通用占位符。",
        )
    ]


def register_builtin_templates(registry: TemplateRegistry | None = None) -> TemplateRegistry:
    """Register packaged templates into a JSON registry and return it."""
    target_registry = registry or TemplateRegistry()
    for template in builtin_resume_templates():
        target_registry.add(template)
    return target_registry


class DocxEditor:
    """Apply simple text replacements inside a DOCX package."""

    DOCUMENT_XML = "word/document.xml"

    def replace_text(self, source_docx: str | Path, output_docx: str | Path, replacements: dict[str, str]) -> Path:
        source = Path(source_docx)
        output = Path(output_docx)
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp_path = Path(tmp.name)
        try:
            with zipfile.ZipFile(source, "r") as src, zipfile.ZipFile(tmp_path, "w") as dst:
                for info in src.infolist():
                    data = src.read(info.filename)
                    if info.filename == self.DOCUMENT_XML:
                        xml = data.decode("utf-8")
                        for old, new in replacements.items():
                            xml = xml.replace(escape(old), escape(new))
                            xml = xml.replace(old, escape(new))
                        data = xml.encode("utf-8")
                    dst.writestr(info, data)
            shutil.move(str(tmp_path), output)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
        return output


class ResumeWordAgent:
    """Use DeepSeek to plan resume edits and apply them to Word templates."""

    def __init__(
        self,
        *,
        registry: TemplateRegistry | None = None,
        docx_editor: DocxEditor | None = None,
        deepseek_client: DeepSeekClient | None = None,
    ) -> None:
        self.registry = registry or TemplateRegistry()
        self.docx_editor = docx_editor or DocxEditor()
        self.deepseek_client = deepseek_client

    def plan_replacements(self, resume_facts: dict[str, object], target_role: str) -> dict[str, str]:
        if not self.deepseek_client:
            return {f"{{{{{key}}}}}": str(value) for key, value in resume_facts.items()}
        response = self.deepseek_client.complete_json(
            "你是简历 Word 模板编辑 agent。只输出 JSON 对象，key 是模板占位符，value 是替换文本。",
            f"目标岗位：{target_role}\n候选人素材：{json.dumps(resume_facts, ensure_ascii=False)}",
        )
        return {str(key): str(value) for key, value in response.items()}

    def render(
        self,
        *,
        template_id: str,
        output_docx: str | Path,
        resume_facts: dict[str, object],
        target_role: str,
    ) -> Path:
        template = self.registry.get(template_id)
        replacements = self.plan_replacements(resume_facts, target_role)
        return self.docx_editor.replace_text(template.path, output_docx, replacements)
