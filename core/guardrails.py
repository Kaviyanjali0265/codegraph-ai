from pydantic import BaseModel


class GuardrailResult(BaseModel):
    passed: bool
    reason: str = ""


MAX_QUERY_LENGTH = 1000
MIN_QUERY_LENGTH = 5
MIN_RESULT_LENGTH = 20


def validate_input(query: str) -> GuardrailResult:
    if not query or not query.strip():
        return GuardrailResult(passed=False, reason="Query is empty.")

    if len(query.strip()) < MIN_QUERY_LENGTH:
        return GuardrailResult(passed=False, reason="Query is too short to be meaningful.")

    if len(query) > MAX_QUERY_LENGTH:
        return GuardrailResult(
            passed=False,
            reason=f"Query too long ({len(query)} chars). Max allowed is {MAX_QUERY_LENGTH}.",
        )

    return GuardrailResult(passed=True)


def validate_output(result: str, sources: list[str]) -> GuardrailResult:
    if not result or not result.strip():
        return GuardrailResult(passed=False, reason="Agent returned an empty response.")

    if len(result.strip()) < MIN_RESULT_LENGTH:
        return GuardrailResult(passed=False, reason="Agent response too short — likely a failure.")

    if not sources:
        return GuardrailResult(
            passed=False,
            reason="No sources cited — response may be hallucinated.",
        )

    return GuardrailResult(passed=True)
