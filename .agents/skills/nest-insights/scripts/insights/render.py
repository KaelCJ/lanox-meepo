from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Any

from .contracts import TEMPLATE_VERSION, atomic_write_text


OUTCOME_LABELS = {
    "completed": "完成", "mostly_completed": "大体完成", "partially_completed": "部分完成",
    "blocked": "受阻", "abandoned": "放弃", "unknown": "未知", "not_analyzed": "未抽样",
}
TASK_TYPE_LABELS = {
    "single_task": "单任务", "multi_turn": "多轮任务", "exploration": "探索",
    "review": "审查", "implementation": "实施", "operations": "运维",
    "learning": "学习", "other": "其他",
}
SENTIMENT_LABELS = {"positive": "明确正向", "negative": "明确负向", "mixed": "混合", "neutral": "中性"}
ANCHORS = {
    "project_areas": "你在做什么", "interaction_style": "你如何使用 Codex",
    "what_works": "做得出色的工作", "friction_analysis": "摩擦与失败模式",
    "suggestions": "可尝试的改进", "on_the_horizon": "未来机会",
}


def e(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def number(value: object) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def confidence(value: object) -> str:
    try:
        return f"{float(value):.0%}"
    except (TypeError, ValueError):
        return "0%"


def evidence_chips(refs: object) -> str:
    if not isinstance(refs, list) or not refs:
        return ""
    return '<div class="evidence">' + "".join(f'<span>{e(ref)}</span>' for ref in refs[:12]) + "</div>"


def bars(values: dict[str, Any], labels: dict[str, str] | None = None, limit: int = 12) -> str:
    if not values:
        return '<p class="empty">暂无数据</p>'
    rows = list(values.items())[:limit]
    maximum = max((int(value) for _, value in rows), default=1) or 1
    result = []
    for key, value in rows:
        count = int(value)
        label = labels.get(str(key), str(key)) if labels else str(key)
        width = max(2, round(count / maximum * 100))
        result.append(
            f'<div class="bar-row"><div class="bar-label" title="{e(label)}">{e(label)}</div>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{width}%"></div></div>'
            f'<div class="bar-value">{number(count)}</div></div>'
        )
    return "".join(result)


def copy_box(text: object, copy_id: str, label: str = "复制") -> str:
    return (
        '<div class="copy-box">'
        f'<pre id="{e(copy_id)}">{e(text)}</pre>'
        f'<button class="copy-btn" type="button" data-copy="{e(copy_id)}">{e(label)}</button>'
        '</div>'
    )


def at_a_glance(section: dict[str, Any]) -> str:
    items = []
    for key, label in (("effective", "有效做法"), ("obstacle", "最大阻碍"), ("quick_win", "快速改进"), ("future_workflow", "进阶工作流")):
        item = section.get(key, {}) if isinstance(section.get(key), dict) else {}
        anchor = ANCHORS.get(str(item.get("anchor")), "你在做什么")
        items.append(
            '<div class="glance-item">'
            f'<strong>{e(label)} · {e(item.get("title"))}</strong>'
            f'<p>{e(item.get("detail"))} <a href="#{e(anchor)}">继续阅读 →</a></p>'
            f'{evidence_chips(item.get("evidence_refs"))}</div>'
        )
    return (
        '<section id="一眼看懂" class="glance">'
        f'<div class="glance-title">{e(section.get("title") or "一眼看懂")}</div>'
        f'<div class="glance-grid">{"".join(items)}</div></section>'
    )


def project_areas(section: dict[str, Any]) -> str:
    cards = []
    for item in section.get("areas", []):
        if not isinstance(item, dict):
            continue
        cards.append(
            '<article class="area-card"><div class="card-head">'
            f'<h3>{e(item.get("name"))}</h3><span>约 {number(item.get("sample_count"))} 个深度样本</span></div>'
            f'<p>{e(item.get("description"))}</p>{evidence_chips(item.get("evidence_refs"))}</article>'
        )
    return (
        '<section id="你在做什么"><h2>你在做什么</h2>'
        f'<p class="section-intro">{e(section.get("intro"))}</p><div class="stack">{"".join(cards)}</div>'
        f'<div class="key-insight"><strong>变化：</strong>{e(section.get("trend"))}</div></section>'
    )


def interaction_style(section: dict[str, Any]) -> str:
    paragraphs = "".join(f'<p>{e(value)}</p>' for value in section.get("paragraphs", []) if value)
    return (
        '<section id="你如何使用 Codex"><h2>你如何使用 Codex</h2>'
        f'<div class="narrative">{paragraphs}{evidence_chips(section.get("evidence_refs"))}'
        f'<div class="key-insight"><strong>关键模式：</strong>{e(section.get("key_pattern"))}</div></div></section>'
    )


def what_works(section: dict[str, Any]) -> str:
    wins = []
    for item in section.get("wins", []):
        if not isinstance(item, dict):
            continue
        wins.append(
            '<article class="win-card"><h3>{}</h3><p>{}</p><p class="why"><strong>为什么有效：</strong>{}</p>{}</article>'.format(
                e(item.get("title")), e(item.get("description")), e(item.get("why_it_worked")), evidence_chips(item.get("evidence_refs"))
            )
        )
    return (
        '<section id="做得出色的工作"><h2>做得出色的工作</h2>'
        f'<p class="section-intro">{e(section.get("intro"))}</p><div class="stack">{"".join(wins)}</div></section>'
    )


def friction(section: dict[str, Any]) -> str:
    cards = []
    for item in section.get("categories", []):
        if not isinstance(item, dict):
            continue
        examples = "".join(
            f'<li>{e(example.get("detail"))}{evidence_chips(example.get("evidence_refs"))}</li>'
            for example in item.get("examples", []) if isinstance(example, dict)
        )
        cards.append(
            '<article class="friction-card">'
            f'<div class="card-head"><h3>{e(item.get("title"))}</h3><span>{number(item.get("sample_count"))} 个样本</span></div>'
            f'<p>{e(item.get("description"))}</p><p><strong>后果：</strong>{e(item.get("consequence"))}</p>'
            f'<ul>{examples}</ul><p class="avoid"><strong>可避免条件：</strong>{e(item.get("avoid_by"))}</p></article>'
        )
    return (
        '<section id="摩擦与失败模式"><h2>摩擦与失败模式</h2>'
        f'<p class="section-intro">{e(section.get("intro"))}</p><div class="stack">{"".join(cards)}</div></section>'
    )


def suggestions(section: dict[str, Any]) -> str:
    rules = []
    for index, item in enumerate(section.get("rule_candidates", []), start=1):
        if not isinstance(item, dict):
            continue
        content = f"## {item.get('section', '')}\n{item.get('content', '')}".strip()
        rules.append(
            '<article class="rule-card"><h3>{}</h3>{}<p class="why"><strong>为什么适合你：</strong>{}</p>{}</article>'.format(
                e(item.get("title")), copy_box(content, f"rule-{index}"), e(item.get("why")), evidence_chips(item.get("evidence_refs"))
            )
        )

    def suggestion_cards(field: str, kind: str) -> str:
        result = []
        for index, item in enumerate(section.get(field, []), start=1):
            if not isinstance(item, dict):
                continue
            result.append(
                f'<article class="{kind}-card"><h3>{e(item.get("title"))}</h3><p>{e(item.get("summary"))}</p>'
                f'<p><strong>为什么适合你：</strong>{e(item.get("why_for_you"))}</p>'
                f'<p><strong>从这里开始：</strong>{e(item.get("how_to_start"))}</p>'
                f'{copy_box(item.get("copyable_prompt"), f"{field}-{index}", "复制 Prompt")}'
                f'{evidence_chips(item.get("evidence_refs"))}</article>'
            )
        return "".join(result)

    return (
        '<section id="可尝试的改进"><h2>可尝试的改进</h2>'
        f'<p class="section-intro">{e(section.get("intro"))}</p>'
        f'<h3 class="subhead">候选 AGENTS.md / Skill 规则</h3><p class="small-note">这些只是候选，不会自动写入。可复制后按工作空间边界审查。</p><div class="stack">{"".join(rules)}</div>'
        f'<h3 class="subhead">现有 Codex 能力可以这样用</h3><div class="stack">{suggestion_cards("features", "feature")}</div>'
        f'<h3 class="subhead">新的工作模式</h3><div class="stack">{suggestion_cards("patterns", "pattern")}</div></section>'
    )


def horizon(section: dict[str, Any]) -> str:
    cards = []
    for index, item in enumerate(section.get("opportunities", []), start=1):
        if not isinstance(item, dict):
            continue
        cards.append(
            '<article class="horizon-card"><h3>{}</h3><p>{}</p><p><strong>起步：</strong>{}</p>{}{}</article>'.format(
                e(item.get("title")), e(item.get("possibility")), e(item.get("getting_started")),
                copy_box(item.get("copyable_prompt"), f"horizon-{index}", "复制 Prompt"), evidence_chips(item.get("evidence_refs"))
            )
        )
    return (
        '<section id="未来机会"><h2>未来机会</h2>'
        f'<p class="section-intro">{e(section.get("intro"))}</p><div class="stack">{"".join(cards)}</div></section>'
    )


def fun_ending(section: dict[str, Any]) -> str:
    return (
        '<section class="fun-ending">'
        f'<div class="fun-headline">{e(section.get("headline"))}</div><p>{e(section.get("detail"))}</p>'
        f'{evidence_chips(section.get("evidence_refs"))}</section>'
    )


def task_table(tasks: list[dict[str, Any]]) -> str:
    rows = []
    for task in tasks[:120]:
        rows.append(
            '<tr>'
            f'<td><code>{e(task.get("task_alias"))}</code></td><td>{e(task.get("date"))}</td>'
            f'<td>{number(task.get("turns"))}</td><td>{number(task.get("child_threads"))}</td>'
            f'<td>{e(OUTCOME_LABELS.get(str(task.get("outcome")), task.get("outcome")))}</td>'
            f'<td>{e(task.get("summary"))}</td><td>{confidence(task.get("confidence"))}</td></tr>'
        )
    return "".join(rows)


def render_report(
    report_path: Path, aggregated: dict[str, Any], sections: dict[str, dict[str, Any]], generated_at: datetime,
) -> None:
    coverage = aggregated.get("coverage", {})
    metrics = aggregated.get("metrics", {})
    distributions = aggregated.get("distributions", {})
    active_days = int(metrics.get("active_days", 0) or 0)
    messages = int(metrics.get("user_messages", 0) or 0)
    avg_messages = messages / active_days if active_days else 0
    top_stats = "".join([
        f'<div class="top-stat"><strong>{number(messages)}</strong><span>用户消息</span></div>',
        f'<div class="top-stat"><strong>{number(metrics.get("observed_files"))}</strong><span>Patch 文件项（含重复）</span></div>',
        f'<div class="top-stat"><strong>{number(active_days)}</strong><span>活跃日期</span></div>',
        f'<div class="top-stat"><strong>{avg_messages:.1f}</strong><span>日均消息</span></div>',
        f'<div class="top-stat"><strong>{number(coverage.get("facet_success"))}</strong><span>深度 Facet</span></div>',
    ])
    charts = [
        ("你想完成什么", distributions.get("goals", {}), None),
        ("常用工具族", distributions.get("tools", {}), None),
        ("观察到的文件类型", distributions.get("extensions", {}), None),
        ("任务类型", distributions.get("task_types", {}), TASK_TYPE_LABELS),
        ("用户响应时间", distributions.get("response_times", {}), None),
        ("一天中的消息时段（UTC）", distributions.get("hours", {}), None),
        ("结构化工具失败", distributions.get("tool_errors", {}), None),
        ("最常见成功因素", distributions.get("successes", {}), None),
        ("任务结果（模型推断）", distributions.get("outcomes", {}), OUTCOME_LABELS),
        ("摩擦类型（模型推断）", distributions.get("frictions", {}), None),
        ("明确表达的态度", distributions.get("sentiment", {}), SENTIMENT_LABELS),
        ("历史月份分布", distributions.get("months", {}), None),
    ]
    chart_html = "".join(
        f'<article class="chart"><div class="chart-title">{e(title)}</div>{bars(values, labels)}</article>'
        for title, values, labels in charts
    )
    coverage_cards = "".join(
        f'<div class="coverage-stat"><strong>{number(value)}</strong><span>{e(label)}</span></div>'
        for label, value in (
            ("扫描 JSONL", coverage.get("filesystem_jsonl")), ("SQLite Thread", coverage.get("sqlite_threads")),
            ("Root Task", coverage.get("root_threads")), ("TaskMeta", coverage.get("task_meta_success")),
            ("Facet 样本", coverage.get("facet_success")), ("活动延后", coverage.get("deferred_live")),
        )
    )
    body = "".join([
        at_a_glance(sections.get("at_a_glance", {})),
        project_areas(sections.get("project_areas", {})),
        interaction_style(sections.get("interaction_style", {})),
        f'<section id="使用统计"><h2>使用统计</h2><div class="charts">{chart_html}</div>'
        f'<div class="parallel-note"><strong>并行工作观察：</strong>30 分钟窗口中观察到 {number(metrics.get("parallel_task_pairs"))} 组 Root Task 交叠、{number(metrics.get("parallel_events"))} 次交叠事件。该指标只表示时间重叠，不等于并行 Agent。</div></section>',
        what_works(sections.get("what_works", {})),
        friction(sections.get("friction_analysis", {})),
        suggestions(sections.get("suggestions", {})),
        horizon(sections.get("on_the_horizon", {})),
        fun_ending(sections.get("fun_ending", {})),
    ])
    html_text = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nest Insights</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}html{{scroll-behavior:smooth}}body{{font-family:Inter,"Segoe UI","Microsoft YaHei",sans-serif;background:#f8fafc;color:#334155;line-height:1.68;padding:42px 22px}}.container{{max-width:900px;margin:auto}}
h1{{font-size:38px;color:#0f172a;margin-bottom:6px}}h2{{font-size:23px;color:#0f172a;margin:48px 0 14px}}h3{{color:#0f172a;font-size:16px}}.subtitle{{color:#64748b;margin-bottom:20px}}.nav{{display:flex;flex-wrap:wrap;gap:7px;background:#fff;border:1px solid #e2e8f0;padding:14px;border-radius:10px;margin:22px 0}}.nav a{{font-size:12px;text-decoration:none;color:#475569;background:#f1f5f9;padding:5px 10px;border-radius:6px}}
.stats-row{{display:flex;gap:24px;flex-wrap:wrap;border-top:1px solid #e2e8f0;border-bottom:1px solid #e2e8f0;padding:18px 0;margin:26px 0 30px}}.top-stat{{text-align:center;min-width:100px}}.top-stat strong{{display:block;font-size:23px;color:#0f172a}}.top-stat span{{font-size:11px;color:#64748b}}
.glance{{background:linear-gradient(135deg,#fef3c7,#fde68a);border:1px solid #f59e0b;border-radius:12px;padding:22px 24px}}.glance-title{{font-size:18px;font-weight:700;color:#92400e;margin-bottom:12px}}.glance-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px 22px}}.glance-item strong{{color:#92400e}}.glance-item p{{font-size:14px;color:#78350f;margin:4px 0}}.glance a{{color:#b45309}}
.section-intro{{color:#64748b;font-size:14px;margin-bottom:15px}}.stack{{display:flex;flex-direction:column;gap:12px}}.area-card,.narrative,.win-card,.friction-card,.rule-card,.feature-card,.pattern-card,.horizon-card{{background:#fff;border:1px solid #e2e8f0;border-radius:9px;padding:17px}}.card-head{{display:flex;justify-content:space-between;gap:12px;align-items:start}}.card-head span{{font-size:12px;color:#64748b;background:#f1f5f9;padding:3px 8px;border-radius:5px;white-space:nowrap}}article p,.narrative p{{font-size:14px;margin-top:7px}}.key-insight{{background:#f0fdf4;border:1px solid #bbf7d0;color:#166534;border-radius:8px;padding:12px 15px;margin-top:13px;font-size:14px}}.win-card{{background:#f0fdf4;border-color:#bbf7d0}}.win-card h3{{color:#166534}}.why{{color:#475569}}.friction-card{{background:#fef2f2;border-color:#fca5a5}}.friction-card h3{{color:#991b1b}}.friction-card ul{{margin:10px 0 0 22px}}.friction-card li{{font-size:13px;margin:8px 0}}.avoid{{background:#fff;padding:9px;border-radius:6px}}
.subhead{{margin:28px 0 10px}}.small-note{{color:#64748b;font-size:12px;margin-bottom:12px}}.rule-card{{background:#eff6ff;border-color:#bfdbfe}}.feature-card{{background:#f0fdf4;border-color:#86efac}}.pattern-card{{background:#f0f9ff;border-color:#7dd3fc}}.horizon-card{{background:linear-gradient(135deg,#faf5ff,#f5f3ff);border-color:#c4b5fd}}.copy-box{{position:relative;margin-top:12px}}.copy-box pre{{white-space:pre-wrap;word-break:break-word;background:#fff;border:1px solid #cbd5e1;border-radius:6px;padding:12px 64px 12px 12px;font:12px/1.55 ui-monospace,Consolas,monospace;color:#334155}}.copy-btn{{position:absolute;right:7px;top:7px;border:0;border-radius:5px;background:#2563eb;color:#fff;padding:5px 9px;cursor:pointer;font-size:11px}}
.charts{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.chart{{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:16px}}.chart-title{{font-size:12px;font-weight:700;color:#64748b;text-transform:uppercase;margin-bottom:10px}}.bar-row{{display:grid;grid-template-columns:125px 1fr 38px;gap:8px;align-items:center;margin:7px 0;font-size:11px}}.bar-label{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.bar-track{{height:7px;background:#f1f5f9;border-radius:5px;overflow:hidden}}.bar-fill{{height:100%;background:#64748b;border-radius:5px}}.bar-value{{text-align:right;color:#64748b}}.parallel-note{{margin-top:14px;background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:12px;font-size:13px}}
.evidence{{display:flex;flex-wrap:wrap;gap:5px;margin-top:10px}}.evidence span{{font:10px ui-monospace,monospace;color:#64748b;background:rgba(255,255,255,.75);border:1px solid #dbe2ea;padding:2px 5px;border-radius:4px}}.fun-ending{{background:linear-gradient(135deg,#fef3c7,#fde68a);border:1px solid #fbbf24;border-radius:12px;padding:22px;text-align:center;margin-top:42px}}.fun-headline{{font-size:19px;font-weight:700;color:#78350f}}.fun-ending p{{color:#92400e;margin-top:6px}}
details{{background:#fff;border:1px solid #e2e8f0;border-radius:9px;padding:15px;margin-top:22px}}summary{{cursor:pointer;font-weight:600;color:#475569}}.coverage-grid{{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin:14px 0}}.coverage-stat{{background:#f8fafc;padding:10px;border-radius:7px;text-align:center}}.coverage-stat strong{{display:block;font-size:18px;color:#0f172a}}.coverage-stat span{{font-size:10px;color:#64748b}}.method{{font-size:12px;color:#64748b;margin:12px 0}}.table-wrap{{overflow:auto;margin-top:14px}}table{{border-collapse:collapse;width:100%;min-width:820px;font-size:11px}}th,td{{padding:8px;border-bottom:1px solid #e2e8f0;text-align:left;vertical-align:top}}th{{background:#f1f5f9}}td:nth-child(6){{min-width:260px}}footer{{text-align:center;color:#94a3b8;font-size:11px;margin-top:32px}}
@media(max-width:720px){{body{{padding:22px 12px}}.glance-grid,.charts{{grid-template-columns:1fr}}.coverage-grid{{grid-template-columns:repeat(3,1fr)}}.bar-row{{grid-template-columns:100px 1fr 34px}}}}
</style></head><body><main class="container">
<header><h1>Nest Insights</h1><p class="subtitle">{number(messages)} 条用户消息，覆盖 {number(coverage.get('task_meta_success'))} 个已解析 Root Task（发现 {number(coverage.get('root_threads'))} 个） · {e(metrics.get('date_start'))} 至 {e(metrics.get('date_end'))}</p></header>
<nav class="nav"><a href="#一眼看懂">一眼看懂</a><a href="#你在做什么">工作领域</a><a href="#你如何使用 Codex">交互风格</a><a href="#使用统计">使用统计</a><a href="#做得出色的工作">成功工作流</a><a href="#摩擦与失败模式">摩擦</a><a href="#可尝试的改进">建议</a><a href="#未来机会">未来机会</a></nav>
<div class="stats-row">{top_stats}</div>{body}
<details><summary>覆盖、匿名任务索引与方法边界</summary><div class="coverage-grid">{coverage_cards}</div>
<p class="method">深度语义层会加载全部仍有效的 Facet 缓存，并从尚未分析的 Task 中按跨时间与高活动信号每轮最多新增 {number(coverage.get('facet_attempted_this_run'))} 个；当前成功 {number(coverage.get('facet_success'))}，本轮失败 {number(coverage.get('facet_failure'))}，待后续增量 {number(coverage.get('facet_pending'))}。章节成功 {number(coverage.get('chapter_success'))}，失败 {number(coverage.get('chapter_failure'))}。</p>
<p class="method">报告只读派生自 sessions、archived_sessions 和可用 SQLite 索引。模型输入排除了 system/developer 指令、reasoning、原始工具参数与输出、diff、附件和绝对路径。Token、工具、Patch 和时长是观察值；目标、结果、态度、摩擦及建议是模型推断。匿名化不能保证绝对不可识别，报告默认仅供本地查看。</p>
<div class="table-wrap"><table><thead><tr><th>任务</th><th>日期</th><th>Turn</th><th>Child</th><th>结果</th><th>摘要</th><th>置信度</th></tr></thead><tbody>{task_table(aggregated.get('tasks', []))}</tbody></table></div></details>
<footer>生成时间 {e(generated_at.astimezone().strftime('%Y-%m-%d %H:%M'))} · 模板 {e(TEMPLATE_VERSION)} · 本地私有报告</footer></main>
<script>
document.addEventListener('click', async (event) => {{
  const button = event.target.closest('[data-copy]'); if (!button) return;
  const target = document.getElementById(button.dataset.copy); if (!target) return;
  const text = target.textContent || '';
  try {{ await navigator.clipboard.writeText(text); }} catch (_) {{
    const area = document.createElement('textarea'); area.value = text; area.style.position = 'fixed'; area.style.opacity = '0';
    document.body.appendChild(area); area.select(); document.execCommand('copy'); area.remove();
  }}
  const old = button.textContent; button.textContent = '已复制'; setTimeout(() => button.textContent = old, 1200);
}});
</script></body></html>'''
    atomic_write_text(report_path, html_text)
