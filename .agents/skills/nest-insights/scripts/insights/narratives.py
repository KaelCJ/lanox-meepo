from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from .contracts import cache_path
from .facet_runner import ModelCallError, run_section


SECTION_SPECS = {
    "project_areas": ("project-areas.schema.json", "归纳 3–7 个具体工作领域。每项给出已分析样本支持数、代表性项目/Skill/工作项和规模；不要按文件扩展名机械分类。描述时间变化时只使用输入月份分布。"),
    "interaction_style": ("interaction-style.schema.json", "用 2–4 段连贯叙事分析用户如何组织请求、迭代、纠正、授权、并行和验收。必须包含具体数量级或案例，最后压缩成一句鲜明但克制的 key_pattern。"),
    "what_works": ("what-works.schema.json", "选择 3–5 个真正令人印象深刻、跨任务重复或规模显著的成功工作流。每项写清做了什么、规模或复杂度、为什么成功；单任务只能标为代表性案例。"),
    "friction_analysis": ("friction-analysis.schema.json", "选择 3–5 个重复摩擦类别。每类必须形成：现象 → 支持任务数 → 后果 → 两个具体例子 → 可避免条件。区分 Agent、工具、环境和用户侧责任。"),
    "suggestions": ("suggestions.schema.json", "产出可供用户选择、而非自动写入的规则候选、Codex 现有能力建议和可复制工作模式。规则写出建议放置章节与完整正文；每个能力/模式给出 why_for_you、起步方法和可复制中文 Prompt。不得建议违反输入中已知安全边界的自动提交、删除或测试。"),
    "on_the_horizon": ("on-the-horizon.schema.json", "设计 2–4 个基于已证明强项的进阶工作流。每项给出可能形态、最小起步方式和可复制 Prompt；不能虚构 Codex 工具名或承诺当前产品不存在的能力。"),
    "fun_ending": ("fun-ending.schema.json", "用一句有记忆点但不油腻的标题和一小段具体结尾，总结用户最独特的工作方式；必须由证据支持，不做职业或心理诊断。"),
}


def _fallback(name: str, reason: str, payload: dict[str, Any]) -> dict[str, Any]:
    note = f"本章生成失败（{reason}），确定性统计和其他成功章节仍保留。"
    if name == "project_areas":
        return {"title": "你在做什么", "intro": note, "areas": [], "trend": "暂无", "confidence": 0.0}
    if name == "interaction_style":
        return {"title": "你如何使用 Codex", "paragraphs": [note], "key_pattern": "暂无", "evidence_refs": [], "confidence": 0.0}
    if name == "what_works":
        return {"title": "做得出色的工作", "intro": note, "wins": [], "confidence": 0.0}
    if name == "friction_analysis":
        return {"title": "摩擦与失败模式", "intro": note, "categories": [], "confidence": 0.0}
    if name == "suggestions":
        return {"title": "可尝试的改进", "intro": note, "rule_candidates": [], "features": [], "patterns": [], "confidence": 0.0}
    if name == "on_the_horizon":
        return {"title": "未来机会", "intro": note, "opportunities": [], "confidence": 0.0}
    if name == "fun_ending":
        return {"headline": "这次先保留事实", "detail": note, "evidence_refs": [], "confidence": 0.0}
    return {"title": "一眼看懂", "effective": {}, "obstacle": {}, "quick_win": {}, "future_workflow": {}, "confidence": 0.0}


def generate_sections(
    payload: dict[str, Any], allowed_refs: set[str], cache_root: Path,
    schema_path: Path, isolated_dir: Path, model: str | None, concurrency: int,
) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    sections: dict[str, dict[str, Any]] = {}
    stats = {"chapter_success": 0, "chapter_failure": 0, "chapter_cache_hits": 0}

    def execute(name: str, spec: tuple[str, str]) -> tuple[str, dict[str, Any], bool]:
        schema_name, instruction = spec
        section, hit = run_section(
            name, instruction, payload, allowed_refs,
            cache_path(cache_root, "chapters-v2", name), schema_path.parent / schema_name,
            isolated_dir / name, model,
        )
        return name, section, hit

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        futures = {
            executor.submit(execute, name, spec): name
            for name, spec in SECTION_SPECS.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                _, section, hit = future.result()
            except (ModelCallError, OSError, ValueError) as exc:
                sections[name] = _fallback(name, type(exc).__name__, payload)
                stats["chapter_failure"] += 1
            else:
                sections[name] = section
                stats["chapter_success"] += 1
                stats["chapter_cache_hits"] += int(hit)

    glance_payload = {
        "coverage": payload.get("coverage", {}),
        "sections": {name: sections[name] for name in SECTION_SPECS},
    }
    try:
        glance, hit = run_section(
            "at_a_glance",
            "串行综合前述章节，分别给出有效做法、最大阻碍、一个快速改进和一个进阶工作流。每项链接到最相关章节，只能压缩前文，不能增加新事实。",
            glance_payload, allowed_refs,
            cache_path(cache_root, "chapters-v2", "at_a_glance"), schema_path.parent / "at-a-glance.schema.json",
            isolated_dir / "at_a_glance", model,
        )
    except (ModelCallError, OSError, ValueError) as exc:
        sections["at_a_glance"] = _fallback("at_a_glance", type(exc).__name__, glance_payload)
        stats["chapter_failure"] += 1
    else:
        sections["at_a_glance"] = glance
        stats["chapter_success"] += 1
        stats["chapter_cache_hits"] += int(hit)
    return sections, stats
