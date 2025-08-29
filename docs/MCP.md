# Model Context Protocol (MCP)

The MCP defines the structured context provided to an LLM to draft human-readable alerts.

## Schema

```
{
  "campaign": "string",
  "issue": "insufficient_variants | insufficient_diversity | pipeline_error",
  "impact": "string",
  "suggested_next_steps": "string",
  "target_audience": ["marketing" | "it" | "legal" | "creative"]
}
```

## LLM Prompt Template

```
You are an AI assistant for a marketing operations team. Your task is to draft a clear, concise,
and actionable alert based on the following structured data:

Campaign: {{campaign}}
Issue: {{issue}}
Impact: {{impact}}
Suggested Next Steps: {{suggested_next_steps}}
Target Audience: {{target_audience_comma_separated}}

Please draft a human-readable message suitable for the specified audience. The tone should be
professional and helpful. Do not include a greeting or sign-off.
```

## Example

```
{
  "campaign": "Summer Refresh 2024",
  "issue": "insufficient_diversity",
  "impact": "Generated creatives for Eco-Friendly Water Bottle are too visually similar, risking poor CTR.",
  "suggested_next_steps": "Regenerate with varied prompts or seeds; adjust styling cues.",
  "target_audience": ["creative"]
}
```

