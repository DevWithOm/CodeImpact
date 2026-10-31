import json
from unittest.mock import MagicMock
import pytest

from app.schemas.ai import ExplainResponse
from app.schemas.finding import FindingItem
from app.services.ai.gemini_service import AIServiceUnavailableError, GeminiService


@pytest.fixture
def sample_finding() -> FindingItem:
    return FindingItem(
        finding_id="f_ai_test",
        category="unused_export",
        title="Unused function",
        file_path="src/utils.ts",
        symbol="doWork",
        source_tool="knip",
        description="No references found",
        review_risk="medium",
    )


@pytest.mark.asyncio
async def test_gemini_service_unavailable_without_key(sample_finding):
    service = GeminiService(api_key=None, client=None)
    assert not service.is_available()

    # Default should raise AIServiceUnavailableError
    with pytest.raises(AIServiceUnavailableError) as exc_info:
        await service.explain_finding(sample_finding, fallback_on_error=False)
    assert "Gemini API key is not configured" in str(exc_info.value)

    # With fallback_on_error=True, returns deterministic ExplainResponse
    fallback = await service.explain_finding(sample_finding, fallback_on_error=True)
    assert isinstance(fallback, ExplainResponse)
    assert "knip" in fallback.summary
    assert len(fallback.verification_steps) > 0


@pytest.mark.asyncio
async def test_gemini_service_successful_generation(sample_finding):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "summary": "The function doWork is flagged because no static reference exists.",
        "why_it_matters": "Removing dead exports reduces code maintenance burden.",
        "false_positive_scenarios": ["Export might be called dynamically."],
        "verification_steps": ["Check dynamic invocations.", "Run test suite."],
        "suggested_action": "Review before making a change.",
        "limitations": ["Static analysis only."]
    })
    mock_client.models.generate_content.return_value = mock_response

    service = GeminiService(api_key="fake-key", model="gemini-2.5-flash", client=mock_client)
    assert service.is_available()

    result = await service.explain_finding(sample_finding, repo_name="test/repo")
    assert isinstance(result, ExplainResponse)
    assert "doWork" in result.summary
    assert len(result.false_positive_scenarios) == 1
    assert result.suggested_action == "Review before making a change."


@pytest.mark.asyncio
async def test_gemini_service_handles_markdown_json(sample_finding):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = """```json
    {
        "summary": "Wrapped in markdown blocks.",
        "why_it_matters": "Testing regex extraction.",
        "false_positive_scenarios": [],
        "verification_steps": ["Verify manually."],
        "suggested_action": "Safe review.",
        "limitations": []
    }
    ```"""
    mock_client.models.generate_content.return_value = mock_response

    service = GeminiService(api_key="fake-key", client=mock_client)
    result = await service.explain_finding(sample_finding)
    assert result.summary == "Wrapped in markdown blocks."


@pytest.mark.asyncio
async def test_gemini_service_api_error_handling(sample_finding):
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("Quota exceeded 429")

    service = GeminiService(api_key="fake-key", client=mock_client)

    # Should raise AIServiceUnavailableError when fallback_on_error is False
    with pytest.raises(AIServiceUnavailableError) as exc_info:
        await service.explain_finding(sample_finding, fallback_on_error=False)
    assert "Quota exceeded" in str(exc_info.value)

    # Should return deterministic fallback when fallback_on_error is True
    fallback = await service.explain_finding(sample_finding, fallback_on_error=True)
    assert isinstance(fallback, ExplainResponse)
    assert len(fallback.verification_steps) > 0
