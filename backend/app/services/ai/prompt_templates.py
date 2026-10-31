import json
from typing import Any

from app.schemas.finding import FindingDetail, FindingItem

SYSTEM_INSTRUCTION = """You are CodeImpact's expert AI codebase intelligence assistant.
Your role is to analyze static code analysis findings, dependency graph context, and evidence to produce clear, evidence-grounded refactoring explanations and safe cleanup recommendations.

CRITICAL RULES:
1. Never claim or guarantee that code is definitely safe to delete. Always use careful, responsible phrasing such as "potentially unused", "no static references were found by the configured scan", or "candidate for review".
2. Ground your explanation strictly on the provided finding evidence, risk factors, and dependency relationships. Do not invent facts or phantom callers.
3. Identify plausible false-positive scenarios (e.g., dynamic imports, runtime reflection, framework entry points, plugin registration, external library exports).
4. Provide concrete, step-by-step verification steps a developer must perform before refactoring or removing the code.
5. Highlight analysis limitations (e.g., static analysis cannot observe runtime execution or dynamic dependency injection).
6. Return your response as a valid JSON object matching the requested schema.
"""


def _normalize_ev(ev: Any) -> dict[str, Any]:
    if isinstance(ev, dict):
        return {
            "kind": ev.get("kind") or ev.get("rule") or "static_reference",
            "status": ev.get("status", "found"),
            "source": ev.get("source") or ev.get("source_tool") or "knip",
            "details": ev.get("details") or ev.get("detail") or str(ev),
        }
    return {
        "kind": getattr(ev, "kind", None) or getattr(ev, "rule", "static_reference"),
        "status": getattr(ev, "status", "found"),
        "source": getattr(ev, "source", None) or getattr(ev, "source_tool", "knip"),
        "details": getattr(ev, "details", None) or getattr(ev, "detail", str(ev)),
    }


def _get_prop(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def build_explanation_prompt(
    finding: FindingItem | FindingDetail,
    repo_name: str = "",
    user_prompt: str | None = None,
) -> str:
    """Builds a structured prompt grounded in the finding's evidence, impact data, and optional developer prompt."""
    context: dict[str, Any] = {
        "repository": repo_name or "Target Repository",
        "finding_id": finding.finding_id,
        "category": finding.category,
        "title": finding.title,
        "file_path": finding.file_path,
        "location": {
            "start_line": finding.start_line,
            "end_line": finding.end_line,
            "symbol": finding.symbol,
        },
        "source_tool": finding.source_tool,
        "description": finding.description,
        "evidence_class": finding.evidence_class,
        "review_risk": finding.review_risk,
        "evidence": [_normalize_ev(ev) for ev in finding.evidence],
        "risk_factors": finding.risk_factors,
    }

    if getattr(finding, "risk_score", None) is not None:
        context["risk_score"] = getattr(finding, "risk_score")
    if getattr(finding, "risk_confidence", None) is not None:
        context["risk_confidence"] = getattr(finding, "risk_confidence")

    if finding.impact:
        tc_list = _get_prop(finding.impact, "related_test_candidates", []) or []
        context["impact"] = {
            "direct_dependants": _get_prop(finding.impact, "direct_dependants", []),
            "dependency_count": _get_prop(finding.impact, "dependency_count", 0),
            "cycle_member": _get_prop(finding.impact, "cycle_member", False),
            "related_test_candidates": [
                {
                    "file_path": _get_prop(tc, "file_path", ""),
                    "reason": _get_prop(tc, "reason", ""),
                    "mapping_strength": _get_prop(tc, "mapping_strength", "direct"),
                }
                for tc in tc_list
            ],
            "impact_risk_factors": _get_prop(finding.impact, "risk_factors", []),
        }

    limitations = getattr(finding, "limitations", [])
    if limitations:
        context["tool_limitations"] = limitations

    prompt = f"""{SYSTEM_INSTRUCTION}

Below is the verified static analysis and dependency evidence for a finding in {context['repository']}:

```json
{json.dumps(context, indent=2)}
```
"""

    if user_prompt and user_prompt.strip():
        prompt += f"""
Specific Developer Inquiry:
"{user_prompt.strip()}"

Address this specific inquiry thoroughly while grounding all conclusions strictly on the verified facts above.
"""

    prompt += """
Generate a structured explanation in JSON format with the following fields:
- "summary": A concise, evidence-grounded summary of what was detected and why.
- "why_it_matters": Explanation of the architectural, performance, or maintenance impact.
- "false_positive_scenarios": A list of specific scenarios where this code may actually be used despite static analysis findings.
- "verification_steps": Concrete steps and tests a developer should run to verify the finding before removing or modifying the code.
- "suggested_action": Recommended safe next action (e.g. "Review before making a change", "Verify dynamic references before cleanup").
- "limitations": Specific limitations of the static tools in this scenario (e.g. lack of runtime visibility).
"""
    return prompt


def generate_deterministic_fallback(
    finding: FindingItem | FindingDetail,
    user_prompt: str | None = None,
) -> dict[str, Any]:
    """Generates an evidence-grounded fallback explanation when Gemini is unavailable."""
    symbol_str = f"symbol '{finding.symbol}' in " if finding.symbol else ""
    line_str = f" (lines {finding.start_line}-{finding.end_line})" if finding.start_line else ""
    location_desc = f"{symbol_str}{finding.file_path}{line_str}"

    summary = (
        f"Static analysis by {finding.source_tool} flagged {location_desc} as {finding.category.replace('_', ' ')}. "
        f"No direct static references were identified during the scan."
    )
    if user_prompt and user_prompt.strip():
        summary += f" Developer inquiry: '{user_prompt.strip()}'."

    why_it_matters = (
        f"Unused or duplicated code increases cognitive overhead, maintenance surface, and potential bundle size. "
        f"This finding carries a '{finding.review_risk}' review risk."
    )

    fps = [
        "The code may be referenced dynamically via string reflection or dynamic imports.",
        "The component or export may be part of a public API consumed outside this repository.",
    ]
    if finding.impact and _get_prop(finding.impact, "cycle_member", False):
        fps.append("The module participates in a circular dependency which may mask reachability.")

    steps = [
        f"Search the codebase for dynamic references or string usages of '{finding.symbol or finding.file_path}'.",
    ]
    impact_tcs = _get_prop(finding.impact, "related_test_candidates", []) if finding.impact else []
    if impact_tcs:
        test_paths = [
            _get_prop(tc, "file_path", "")
            for tc in impact_tcs
            if _get_prop(tc, "file_path", "")
        ]
        if test_paths:
            steps.append(f"Run and inspect related test suites: {', '.join(test_paths)}.")
        else:
            steps.append("Check if test coverage exists for this module before refactoring.")
    else:
        steps.append("Check if test coverage exists for this module before refactoring.")

    steps.append("Perform a manual code review with the original author or domain team.")

    limitations = [
        f"Static analysis by {finding.source_tool} cannot observe runtime reachability or dynamic execution.",
        "Missing references do not definitively prove the code is uncalled in production.",
    ]
    if getattr(finding, "limitations", None):
        limitations.extend(finding.limitations)

    deduped_limitations = list(dict.fromkeys(limitations))

    return {
        "summary": summary,
        "why_it_matters": why_it_matters,
        "false_positive_scenarios": fps,
        "verification_steps": steps,
        "suggested_action": "Review before making a change.",
        "limitations": deduped_limitations,
        # Convenience aliases for frontend
        "explanation": summary,
        "potential_risks": fps,
        "uncertainty_notes": deduped_limitations,
    }
