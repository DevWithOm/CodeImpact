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


def build_explanation_prompt(finding: FindingItem | FindingDetail, repo_name: str = "") -> str:
    """Builds a structured prompt grounded in the finding's evidence and impact data."""
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
        "evidence": [
            {
                "kind": ev.kind,
                "status": ev.status,
                "source": ev.source,
                "details": ev.details,
            }
            for ev in finding.evidence
        ],
        "risk_factors": finding.risk_factors,
    }

    if finding.impact:
        context["impact"] = {
            "direct_dependants": finding.impact.direct_dependants,
            "dependency_count": finding.impact.dependency_count,
            "cycle_member": finding.impact.cycle_member,
            "related_test_candidates": [
                {
                    "file_path": tc.file_path,
                    "reason": tc.reason,
                    "mapping_strength": tc.mapping_strength,
                }
                for tc in finding.impact.related_test_candidates
            ],
            "impact_risk_factors": finding.impact.risk_factors,
        }

    limitations = getattr(finding, "limitations", [])
    if limitations:
        context["tool_limitations"] = limitations

    prompt = f"""{SYSTEM_INSTRUCTION}

Below is the verified static analysis and dependency evidence for a finding in {context['repository']}:

```json
{json.dumps(context, indent=2)}
```

Generate a structured explanation in JSON format with the following fields:
- "summary": A concise, evidence-grounded summary of what was detected and why.
- "why_it_matters": Explanation of the architectural, performance, or maintenance impact.
- "false_positive_scenarios": A list of specific scenarios where this code may actually be used despite static analysis findings.
- "verification_steps": Concrete steps and tests a developer should run to verify the finding before removing or modifying the code.
- "suggested_action": Recommended safe next action (e.g. "Review before making a change", "Verify dynamic references before cleanup").
- "limitations": Specific limitations of the static tools in this scenario (e.g. lack of runtime visibility).
"""
    return prompt


def generate_deterministic_fallback(finding: FindingItem | FindingDetail) -> dict[str, Any]:
    """Generates an evidence-grounded fallback explanation when Gemini is unavailable."""
    symbol_str = f"symbol '{finding.symbol}' in " if finding.symbol else ""
    line_str = f" (lines {finding.start_line}-{finding.end_line})" if finding.start_line else ""
    location_desc = f"{symbol_str}{finding.file_path}{line_str}"

    summary = (
        f"Static analysis by {finding.source_tool} flagged {location_desc} as {finding.category.replace('_', ' ')}. "
        f"No direct static references were identified during the scan."
    )

    why_it_matters = (
        f"Unused or duplicated code increases cognitive overhead, maintenance surface, and potential bundle size. "
        f"This finding carries a '{finding.review_risk}' review risk."
    )

    fps = [
        "The code may be referenced dynamically via string reflection or dynamic imports.",
        "The component or export may be part of a public API consumed outside this repository.",
    ]
    if finding.impact and finding.impact.cycle_member:
        fps.append("The module participates in a circular dependency which may mask reachability.")

    steps = [
        f"Search the codebase for dynamic references or string usages of '{finding.symbol or finding.file_path}'.",
    ]
    if finding.impact and finding.impact.related_test_candidates:
        test_paths = [tc.file_path for tc in finding.impact.related_test_candidates]
        steps.append(f"Run and inspect related test suites: {', '.join(test_paths)}.")
    else:
        steps.append("Check if test coverage exists for this module before refactoring.")

    steps.append("Perform a manual code review with the original author or domain team.")

    limitations = [
        f"Static analysis by {finding.source_tool} cannot observe runtime reachability or dynamic execution.",
        "Missing references do not definitively prove the code is uncalled in production.",
    ]
    if getattr(finding, "limitations", None):
        limitations.extend(finding.limitations)

    return {
        "summary": summary,
        "why_it_matters": why_it_matters,
        "false_positive_scenarios": fps,
        "verification_steps": steps,
        "suggested_action": "Review before making a change.",
        "limitations": list(dict.fromkeys(limitations)),  # deduplicate
    }
