"""Persona skill routing for AI coaching."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


@dataclass(frozen=True)
class PersonaSkill:
    skill_id: str
    name: str
    source_url: str
    domains: list[str]
    keywords: list[str]
    guidance: str


BUSINESS_PERSONA_SKILLS: list[PersonaSkill] = [
    PersonaSkill(
        skill_id="steve_jobs",
        name="乔布斯.skill",
        source_url="https://github.com/alchaincyf/steve-jobs-skill",
        domains=["产品", "设计", "战略", "用户体验"],
        keywords=["产品", "设计", "体验", "用户", "原型", "战略", "创新", "审美"],
        guidance="从用户体验、产品取舍、端到端叙事和极简表达角度追问证据。",
    ),
    PersonaSkill(
        skill_id="elon_musk",
        name="马斯克.skill",
        source_url="https://github.com/alchaincyf/elon-musk-skill",
        domains=["工程", "成本", "自动化", "第一性原理"],
        keywords=["工程", "成本", "自动化", "效率", "系统", "技术", "架构", "第一性原理"],
        guidance="从第一性原理、约束拆解、成本效率和工程交付角度追问证据。",
    ),
    PersonaSkill(
        skill_id="zhang_yiming",
        name="张一鸣.skill",
        source_url="https://github.com/alchaincyf/zhang-yiming-skill",
        domains=["产品", "组织", "增长", "数据"],
        keywords=["增长", "数据", "推荐", "组织", "人才", "A/B", "指标", "实验", "全球化"],
        guidance="从数据驱动、目标拆解、组织协同和长期主义角度追问证据。",
    ),
    PersonaSkill(
        skill_id="buffett",
        name="巴菲特.skill",
        source_url="https://github.com/will2025btc/buffett-perspective",
        domains=["商业模式", "长期价值", "投资"],
        keywords=["商业模式", "现金流", "长期", "价值", "护城河", "投资", "客户留存"],
        guidance="从长期价值、商业质量、护城河和可持续结果角度追问证据。",
    ),
    PersonaSkill(
        skill_id="munger",
        name="芒格.skill",
        source_url="https://github.com/alchaincyf/munger-skill",
        domains=["多元思维", "逆向思考", "决策"],
        keywords=["决策", "判断", "风险", "逆向", "复盘", "模型", "认知"],
        guidance="从逆向思考、误判清单和多模型决策角度追问证据。",
    ),
    PersonaSkill(
        skill_id="naval",
        name="纳瓦尔.skill",
        source_url="https://github.com/alchaincyf/naval-skill",
        domains=["杠杆", "财富", "个人品牌", "自动化"],
        keywords=["杠杆", "复利", "自动化", "个人品牌", "内容", "规模化", "影响力"],
        guidance="从可复制杠杆、复利积累和规模化影响角度追问证据。",
    ),
    PersonaSkill(
        skill_id="taleb",
        name="塔勒布.skill",
        source_url="https://github.com/alchaincyf/taleb-skill",
        domains=["风险", "反脆弱", "不确定性"],
        keywords=["风险", "不确定", "抗压", "鲁棒", "反脆弱", "波动", "容错"],
        guidance="从风险暴露、冗余设计、反脆弱收益和失败成本角度追问证据。",
    ),
    PersonaSkill(
        skill_id="trump",
        name="特朗普.skill",
        source_url="https://github.com/alchaincyf/trump-skill",
        domains=["谈判", "传播", "权力"],
        keywords=["谈判", "传播", "影响", "公关", "销售", "商务", "说服", "成交"],
        guidance="从谈判筹码、传播角度、受众心理和结果转化角度追问证据。",
    ),
]


class PersonaSkillRouter:
    """Select business-thinking persona skills from workspace context."""

    def __init__(self, skills: list[PersonaSkill] | None = None) -> None:
        self.skills = skills or BUSINESS_PERSONA_SKILLS

    def select(self, context: dict[str, Any], message: str = "", *, limit: int = 3) -> list[PersonaSkill]:
        text = self._normalize_text(context, message)
        scored: list[tuple[int, PersonaSkill]] = []
        for skill in self.skills:
            score = sum(1 for keyword in skill.keywords if keyword.lower() in text)
            score += sum(1 for domain in skill.domains if domain.lower() in text)
            if score:
                scored.append((score, skill))
        scored.sort(key=lambda item: (-item[0], item[1].skill_id))
        if scored:
            return [skill for _, skill in scored[:limit]]
        return self._default_skills(limit)

    def serialize(self, skills: list[PersonaSkill]) -> list[dict[str, Any]]:
        return [
            {
                "skill_id": skill.skill_id,
                "name": skill.name,
                "source_url": skill.source_url,
                "domains": skill.domains,
                "guidance": skill.guidance,
            }
            for skill in skills
        ]

    def prompt_context(self, skills: list[PersonaSkill]) -> str:
        return "\n".join(f"- {skill.name}: {skill.guidance}" for skill in skills)

    def _default_skills(self, limit: int) -> list[PersonaSkill]:
        defaults = ["steve_jobs", "zhang_yiming", "munger"]
        by_id = {skill.skill_id: skill for skill in self.skills}
        return [by_id[skill_id] for skill_id in defaults[:limit] if skill_id in by_id]

    def _normalize_text(self, context: dict[str, Any], message: str) -> str:
        return (json.dumps(context, ensure_ascii=False) + " " + message).lower()
