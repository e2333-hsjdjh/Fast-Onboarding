"""Authenticity-first AI helper for workspace form filling and coaching."""

from __future__ import annotations

import json
import re
from typing import Any

from fast_onboarding.integrations.deepseek_client import DeepSeekClient
from fast_onboarding.web.persona_skills import PersonaSkillRouter


AUTHENTICITY_NOTICE = "AI 只能基于用户已输入的信息整理、补全结构和提出问题；不得编造公司、学校、数字、结果或经历。"


class WorkspaceAIAssistant:
    """Suggest form fields and coaching without inventing resume facts."""

    def __init__(self, deepseek_client: DeepSeekClient | None = None, skill_router: PersonaSkillRouter | None = None) -> None:
        self.deepseek_client = deepseek_client
        self.skill_router = skill_router or PersonaSkillRouter()

    def autofill(self, context: dict[str, Any], *, target: str) -> dict[str, Any]:
        if self.deepseek_client:
            try:
                return self._deepseek_autofill(context, target=target)
            except Exception:
                return self._fallback_autofill(context, target=target)
        return self._fallback_autofill(context, target=target)

    def chat(self, context: dict[str, Any], message: str) -> dict[str, Any]:
        selected_skills = self.skill_router.select(context, message)
        if self.deepseek_client:
            try:
                return self._deepseek_chat(context, message, selected_skills=selected_skills)
            except Exception:
                return self._fallback_chat(context, message, selected_skills=selected_skills)
        return self._fallback_chat(context, message, selected_skills=selected_skills)

    def polish_experience(self, context: dict[str, Any]) -> dict[str, Any]:
        """Create a reviewable rewrite from supplied experience facts only."""
        if self.deepseek_client:
            try:
                return self._deepseek_polish_experience(context)
            except Exception:
                return self._fallback_polish_experience(context)
        return self._fallback_polish_experience(context)

    def chat_stream(self, context: dict[str, Any], message: str):
        """Yield NDJSON-friendly chat events for incremental UI rendering."""
        result = self.chat(context, message)
        reply = result.get("reply") or result.get("authenticity_notice") or ""
        yield {"type": "start", "authenticity_notice": AUTHENTICITY_NOTICE}
        for chunk in self._chunk_text(reply):
            yield {"type": "delta", "text": chunk}
        yield {"type": "final", "ai": result}

    def _deepseek_autofill(self, context: dict[str, Any], *, target: str) -> dict[str, Any]:
        result = self.deepseek_client.complete_json(
            (
                "你是简历工作区 AI 助手。只输出 JSON。严格遵守真实性：只能根据用户已经输入的内容"
                "进行结构化整理、字段补全和追问；不能编造公司、学校、数字、岗位结果、项目成果。"
                "缺失信息必须放入 missing_information 或 questions。不要提供虚构示例，不要生成示例数字。"
            ),
            json.dumps({"target": target, "context": context}, ensure_ascii=False),
        )
        return self._sanitize_autofill_payload(context, self._normalize_ai_payload(result))

    def _deepseek_chat(self, context: dict[str, Any], message: str, *, selected_skills) -> dict[str, Any]:
        result = self.deepseek_client.complete_json(
            (
                "你是简历填写教练。只输出 JSON，字段为 reply, suggestions, questions, authenticity_notice。"
                "严格遵守真实性：只能根据用户输入指出问题、追问证据、建议表达，不得编造事实或数字。"
                "不要提供带虚构公司、项目、技术栈、百分比或数量的示例句。"
                "你可以参考以下商业思维 persona skill 作为追问视角，但不能模仿夸张风格，不能编造事实：\n"
                f"{self.skill_router.prompt_context(selected_skills)}"
            ),
            json.dumps({"message": message, "context": context}, ensure_ascii=False),
        )
        payload = self._sanitize_chat_payload(context, {
            "reply": str(result.get("reply", "")),
            "suggestions": self._coerce_list(result.get("suggestions", [])),
            "questions": self._coerce_list(result.get("questions", [])),
            "authenticity_notice": AUTHENTICITY_NOTICE,
        })
        payload["selected_skills"] = self.skill_router.serialize(selected_skills)
        return payload

    def _deepseek_polish_experience(self, context: dict[str, Any]) -> dict[str, Any]:
        result = self.deepseek_client.complete_json(
            (
                "你是简历经历润色助手。只输出 JSON，字段为 summary, polished_bullets, questions, "
                "evidence_warnings, authenticity_notice。严格遵守真实性：只能重组、压缩和润色用户已输入的事实；"
                "不得新增公司、岗位、工具、数字、结果、奖项、时间或未经输入的结论。"
                "polished_bullets 每条都必须能在原始材料中找到对应事实；信息不足时不要凑句子，改为 questions。"
                "不要使用任何示例数字或虚构示例。"
            ),
            json.dumps({"experience": dict(context.get("experience") or {})}, ensure_ascii=False),
        )
        return self._sanitize_polish_payload(context, result)

    def _fallback_autofill(self, context: dict[str, Any], *, target: str) -> dict[str, Any]:
        source = self._source_text(context)
        suggestions: dict[str, Any] = {}
        missing: list[str] = []
        questions: list[str] = []
        if target == "experience":
            experience = dict(context.get("experience") or {})
            bullets = self._lines(experience.get("bullets") or source)
            metrics = self._metric_lines(experience.get("metrics") or source)
            if bullets:
                suggestions["bullets"] = bullets
            else:
                missing.append("行动与职责")
                questions.append("你具体做了哪 2-3 个动作？例如调研、设计、开发、协调或复盘。")
            if metrics:
                suggestions["metrics"] = metrics
            else:
                missing.append("量化结果")
                questions.append("这段经历有没有真实数字？例如耗时、人数、增长率、播放量、交付数量。")
            skills = self._skills_from_text(" ".join([source, " ".join(bullets)]))
            if skills:
                suggestions["skills"] = skills
            else:
                questions.append("这段经历使用了哪些工具、方法或能力关键词？")
        elif target == "project":
            project = dict(context.get("project") or {})
            jd_text = str(project.get("jd_text") or context.get("jd_text") or "")
            role = str(project.get("role_title") or context.get("target_title") or "")
            if role:
                suggestions["role_title"] = role
            if jd_text:
                suggestions["jd_text"] = jd_text
                suggestions["notes"] = "已根据当前输入保留 JD。请补充投递渠道、目标版本或公司研究结论。"
            else:
                missing.append("岗位 JD")
                questions.append("请粘贴目标岗位 JD，AI 才能基于真实招聘要求分析。")
            if not str(project.get("company_name") or "").strip():
                missing.append("公司名称")
                questions.append("这个项目对应哪家公司？不要用猜测公司名。")
        else:
            questions.append("请选择要补全的是个人经历还是岗位项目。")
        return self._normalize_ai_payload(
            {
                "suggested_fields": suggestions,
                "missing_information": missing,
                "questions": questions,
                "evidence_warnings": self._evidence_warnings(source),
                "confidence": "medium" if suggestions else "low",
            }
        )

    def _fallback_chat(self, context: dict[str, Any], message: str, *, selected_skills=None) -> dict[str, Any]:
        selected_skills = selected_skills or self.skill_router.select(context, message)
        source = self._source_text(context)
        suggestions = []
        questions = []
        if not self._metric_lines(source):
            suggestions.append("当前内容缺少真实量化结果，建议补充时间、人数、效率、增长率或交付数量。")
            questions.append("这段经历有没有可以核实的数字？")
        if len(self._lines(source)) < 2:
            suggestions.append("经历动作还不够细，建议拆成背景、行动、工具、结果四块。")
            questions.append("当时的问题是什么，你具体做了哪些动作？")
        if "负责" in source and not any(word in source for word in ["设计", "分析", "搭建", "优化", "协调", "交付"]):
            suggestions.append("只有“负责”会显得空，建议补充更具体的动词。")
        if not suggestions:
            suggestions.append("这段内容已经有基础事实，可以继续补充证据链接、业务背景和可迁移能力。")
        for skill in selected_skills:
            suggestions.append(f"可用「{skill.name}」视角检查：{skill.guidance}")
        reply = "我会优先帮你保护真实性：先找事实缺口，再建议怎么写。"
        if message.strip():
            reply += f" 针对你的问题“{message.strip()}”，建议先补齐可验证证据，再做表达优化。"
        return {
            "reply": reply,
            "suggestions": suggestions,
            "questions": questions,
            "selected_skills": self.skill_router.serialize(selected_skills),
            "authenticity_notice": AUTHENTICITY_NOTICE,
        }

    def _fallback_polish_experience(self, context: dict[str, Any]) -> dict[str, Any]:
        experience = dict(context.get("experience") or {})
        bullets = self._lines(experience.get("bullets") or [])
        if not bullets:
            bullets = self._lines(experience.get("template_data") or [])
        questions = []
        if not bullets:
            questions.append("请先填写这段经历中你亲自完成的动作、工具或交付物，AI 才能进行润色。")
        if not self._metric_lines(experience.get("metrics") or experience.get("template_data") or []):
            questions.append("如有真实可核实的结果，请补充时间、数量、比例、规模或链接；没有数字也可以说明实际产出。")
        return self._sanitize_polish_payload(context, {
            "summary": "以下建议稿只整理你已填写的事实，请核对后再采纳。",
            "polished_bullets": bullets,
            "questions": questions,
            "evidence_warnings": self._evidence_warnings(self._source_text(context)),
        })

    def _normalize_ai_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "suggested_fields": dict(payload.get("suggested_fields") or {}),
            "missing_information": self._coerce_list(payload.get("missing_information") or []),
            "questions": self._coerce_list(payload.get("questions") or []),
            "evidence_warnings": self._coerce_list(payload.get("evidence_warnings") or []),
            "confidence": str(payload.get("confidence") or "low"),
            "authenticity_notice": AUTHENTICITY_NOTICE,
        }

    def _coerce_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str):
            return [value] if value.strip() else []
        if value:
            return [str(value)]
        return []

    def _sanitize_chat_payload(self, context: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        source = self._source_text(context)
        suggestions = []
        for item in self._coerce_list(payload.get("suggestions", [])):
            replacement = self._truth_safe_replacement(item, source)
            if replacement and replacement not in suggestions:
                suggestions.append(replacement)
        payload["suggestions"] = suggestions
        payload["questions"] = self._coerce_list(payload.get("questions", []))
        payload["authenticity_notice"] = AUTHENTICITY_NOTICE
        return payload

    def _sanitize_autofill_payload(self, context: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        source = self._source_text(context)
        fields = {}
        for key, value in dict(payload.get("suggested_fields") or {}).items():
            if isinstance(value, list):
                safe_items = [item for item in value if not self._looks_invented(str(item), source)]
                if safe_items:
                    fields[key] = safe_items
            elif not self._looks_invented(str(value), source):
                fields[key] = value
        payload["suggested_fields"] = fields
        return payload

    def _sanitize_polish_payload(self, context: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        source = self._source_text(context)
        bullets = []
        for item in self._coerce_list(payload.get("polished_bullets") or []):
            if self._has_unsupported_claim(item, source):
                continue
            safe_item = self._truth_safe_replacement(item, source)
            if safe_item and safe_item not in bullets:
                bullets.append(safe_item)
        if not bullets:
            bullets = self._lines((context.get("experience") or {}).get("bullets") or [])
        summary = str(payload.get("summary") or "")
        if not summary or self._has_unsupported_claim(summary, source):
            summary = "以下建议稿只整理你已填写的事实，请核对后再采纳。"
        return {
            "summary": summary,
            "polished_bullets": bullets,
            "questions": self._coerce_list(payload.get("questions") or []),
            "evidence_warnings": self._coerce_list(payload.get("evidence_warnings") or self._evidence_warnings(source)),
            "authenticity_notice": AUTHENTICITY_NOTICE,
            "requires_confirmation": True,
        }

    def _truth_safe_replacement(self, text: str, source: str) -> str:
        if self._looks_invented(text, source):
            if self._has_unseen_number(text, source):
                return "建议补充真实可核实数字，但不要使用 AI 示例百分比、数量或结果。"
            return "建议补充真实项目名称、角色、工具和结果；不要直接采用 AI 虚构示例。"
        return text

    def _looks_invented(self, text: str, source: str) -> bool:
        if self._has_unseen_number(text, source):
            return True
        example_markers = ["例如", "比如", "示例"]
        if any(marker in text for marker in example_markers):
            return True
        return False

    def _has_unseen_number(self, text: str, source: str) -> bool:
        numbers = re.findall(r"\d+(?:\.\d+)?%?％?", text)
        return any(number and number not in source for number in numbers)

    def _has_unsupported_claim(self, text: str, source: str) -> bool:
        """Reject stronger role or impact claims that were not supplied as facts."""
        risky_claims = ["主导", "独立", "显著", "大幅", "全面", "成功", "行业领先", "最佳", "第一", "从0到1"]
        return any(claim in text and claim not in source for claim in risky_claims)

    def _chunk_text(self, text: str, *, size: int = 18) -> list[str]:
        if not text:
            return []
        return [text[index : index + size] for index in range(0, len(text), size)]

    def _source_text(self, context: dict[str, Any]) -> str:
        return json.dumps(context, ensure_ascii=False)

    def _lines(self, value: Any) -> list[str]:
        if isinstance(value, list):
            raw_lines = [str(item) for item in value]
        else:
            raw_lines = str(value or "").splitlines()
        return [line.strip(" -•\t") for line in raw_lines if line.strip(" -•\t")]

    def _metric_lines(self, value: Any) -> list[str]:
        return [line for line in self._lines(value) if re.search(r"\d+|%|％|提升|降低|增长|压缩|减少|增加|人次|播放量|分钟|小时|天", line)]

    def _skills_from_text(self, text: str) -> list[str]:
        known = ["DeepSeek", "AI", "LLM", "SQL", "Python", "用户研究", "项目管理", "ATS", "Word", "GitHub", "nginx", "SQLite"]
        normalized = text.lower()
        return [skill for skill in known if skill.lower() in normalized]

    def _evidence_warnings(self, text: str) -> list[str]:
        warnings = []
        risky = ["大幅", "显著", "极大", "行业领先", "最佳", "第一"]
        if any(word in text for word in risky) and not self._metric_lines(text):
            warnings.append("存在强结论但缺少真实数字支撑。")
        return warnings
