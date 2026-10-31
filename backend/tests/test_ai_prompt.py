from app.schemas.evidence import EvidenceItem, FindingImpact, TestCandidate
from app.schemas.finding import FindingDetail, FindingItem
from app.services.ai.prompt_templates import (
    build_explanation_prompt,
    generate_deterministic_fallback,
)


def test_build_explanation_prompt_contains_finding_details():
    finding = FindingItem(
        finding_id="f_prompt_1",
        category="unused_export",
        title="Unused calculateTotal export",
        file_path="src/billing/calc.ts",
        start_line=15,
        end_line=25,
        symbol="calculateTotal",
        source_tool="knip",
        description="Export has no static references",
        review_risk="medium",
        evidence=[
            EvidenceItem(
                kind="direct_reference",
                status="not_found",
                source="knip",
                details="No static references found in project",
            )
        ],
        risk_factors=["Symbol is exported from utility module"],
        impact=FindingImpact(
            direct_dependants=["src/billing/invoice.ts"],
            dependency_count=1,
            cycle_member=False,
            related_test_candidates=[
                TestCandidate(file_path="tests/calc.test.ts", reason="Direct unit test", mapping_strength="direct")
            ],
            risk_factors=["Imported by invoice.ts"],
            review_risk="medium",
        ),
    )

    prompt = build_explanation_prompt(finding, repo_name="facebook/react")

    assert "facebook/react" in prompt
    assert "f_prompt_1" in prompt
    assert "calculateTotal" in prompt
    assert "src/billing/calc.ts" in prompt
    assert "invoice.ts" in prompt
    assert "calc.test.ts" in prompt
    assert "Never claim or guarantee that code is definitely safe to delete" in prompt
    assert "false_positive_scenarios" in prompt
    assert "verification_steps" in prompt


def test_generate_deterministic_fallback_returns_valid_structure():
    finding = FindingDetail(
        finding_id="f_fallback_1",
        category="unused_file",
        title="Unused legacy helper",
        file_path="src/legacy.ts",
        source_tool="knip",
        description="Zero references to this file",
        review_risk="higher",
        evidence=[],
        limitations=["Dynamic calls not analyzed"],
    )

    fallback = generate_deterministic_fallback(finding)

    assert "summary" in fallback
    assert "knip" in fallback["summary"]
    assert "why_it_matters" in fallback
    assert len(fallback["false_positive_scenarios"]) > 0
    assert len(fallback["verification_steps"]) > 0
    assert fallback["suggested_action"] == "Review before making a change."
    assert "Dynamic calls not analyzed" in fallback["limitations"]
