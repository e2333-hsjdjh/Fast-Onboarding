"""Document templates and Word editing tools."""

from .resume_word_agent import (
    BUILTIN_ZSC_TABLE_RESUME_TEMPLATE_ID,
    DocxEditor,
    ResumeTemplate,
    ResumeWordAgent,
    TemplateRegistry,
    builtin_resume_templates,
    builtin_template_path,
    register_builtin_templates,
)

__all__ = [
    "BUILTIN_ZSC_TABLE_RESUME_TEMPLATE_ID",
    "DocxEditor",
    "ResumeTemplate",
    "ResumeWordAgent",
    "TemplateRegistry",
    "builtin_resume_templates",
    "builtin_template_path",
    "register_builtin_templates",
]
