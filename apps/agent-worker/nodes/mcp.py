# /apps/agent-worker/nodes/mcp.py

from typing import List, Literal, Dict, Any

# Model Context Protocol (MCP)
# A structured way to represent an issue for an LLM to process.

def build_mcp(
    campaign: str,
    issue: Literal["insufficient_variants", "insufficient_diversity", "pipeline_error"],
    impact: str,
    next_steps: str,
    audience: List[Literal["marketing", "it", "legal", "creative"]]
) -> dict:
    """Constructs a structured context dictionary for an LLM."""
    return {
        "campaign": campaign,
        "issue": issue,
        "impact": impact,
        "suggested_next_steps": next_steps,
        "target_audience": audience,
    }


def build_mcp_extended(
    campaign: str,
    issue: str,
    impact: str,
    next_steps: str,
    audience: List[str],
    context: Dict[str, Any] | None = None,
) -> dict:
    """Extended MCP that can carry additional structured context.

    The base fields mirror MCP, while `context` can include:
      - compliance: {overall_score, issues, critical_issues}
      - metrics: {variant_count, diversity_score}
      - guidance: [str]
      - severity: str
    """
    m = build_mcp(campaign, issue, impact, next_steps, audience)
    if context:
        m["context"] = context
    return m

def format_mcp_for_llm(mcp: dict) -> str:
    """
    Formats the MCP dictionary into a string prompt for an LLM.
    This prompt asks the LLM to draft a human-readable alert.
    """
    prompt = (
        f"You are an AI assistant for a marketing operations team. Your task is to draft a clear, concise, and actionable alert based on the following structured data:\n\n"
        f"**Campaign:** {mcp['campaign']}\n"
        f"**Issue:** {mcp['issue']}\n"
        f"**Impact:** {mcp['impact']}\n"
        f"**Suggested Next Steps:** {mcp['suggested_next_steps']}\n"
        f"**Target Audience:** {', '.join(mcp['target_audience'])}\n\n"
        f"Please draft a human-readable message suitable for the specified audience. The tone should be professional and helpful. Do not include a greeting or sign-off."
    )
    return prompt
