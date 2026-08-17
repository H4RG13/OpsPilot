from decimal import Decimal

# Approximate USD cost per 1K tokens (input, output). These are placeholder
# estimates for relative cost tracking in the portfolio demo, not verified
# current Groq pricing — update against provider docs before using this
# for real budget decisions (see spec Section 33).
COST_PER_1K_TOKENS: dict[str, tuple[Decimal, Decimal]] = {
    "openai/gpt-oss-20b": (Decimal("0.00010"), Decimal("0.00010")),
    "openai/gpt-oss-120b": (Decimal("0.00050"), Decimal("0.00050")),
    "qwen/qwen3.6-27b": (Decimal("0.00020"), Decimal("0.00020")),
}
_DEFAULT_RATE = (Decimal("0"), Decimal("0"))


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    input_rate, output_rate = COST_PER_1K_TOKENS.get(model, _DEFAULT_RATE)
    return (Decimal(input_tokens) / 1000 * input_rate) + (
        Decimal(output_tokens) / 1000 * output_rate
    )
