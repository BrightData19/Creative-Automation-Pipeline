# /apps/agent-worker/nodes/alerting.py

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda
from kafka import KafkaProducer
from kafka.errors import KafkaError

from . import mcp

# --- Kafka Producer for Alerts ---
def get_kafka_producer() -> KafkaProducer:
    """Get a Kafka producer with proper configuration."""
    try:
        producer = KafkaProducer(
            bootstrap_servers=os.getenv("KAFKA_BROKER", "localhost:9092"),
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=3,
            acks='all',
            compression_type='gzip',
            client_id='agent-worker-alerting-producer'
        )
        return producer
    except Exception as e:
        print(f"Failed to create Kafka producer: {e}")
        raise

TOPIC_ALERTS = "alerts.v1"

def get_llm_runnable() -> Runnable:
    """Creates a no-op runnable that simply returns the provided prompt.

    Replace with a real LLM (e.g., ChatOpenAI) by returning: prompt | llm | StrOutputParser()
    """
    prompt = ChatPromptTemplate.from_template("{mcp_prompt}")
    # RunnableLambda returns the input prompt as the final message (no LLM needed)
    return prompt | RunnableLambda(lambda x: x["mcp_prompt"])  # type: ignore


# --- Alerting Node Functions ---
def compose_alert_mcp(state: Dict[str, Any]) -> Dict[str, Any]:
    """Builds the MCP based on the agent's final state."""
    campaign = state['campaign_name']
    issues = state.get('issues', [])
    
    # For this PoC, we'll just use the first issue found
    if not issues:
        # No issues to alert about
        return state
        
    issue_details = issues[0]
    issue_type = issue_details['type']
    
    # Determine audience and next steps based on issue type
    if issue_type == "insufficient_variants":
        impact = f"The campaign may lack enough creative options for A/B testing for product: {issue_details['product']}."
        next_steps = "Consider regenerating assets for the affected product or manually providing more variants."
        audience = ["marketing", "creative"]
    elif issue_type == "insufficient_diversity":
        impact = f"The generated creatives for product {issue_details['product']} are too visually similar, which may lead to poor ad performance."
        next_steps = "Trigger a regeneration with a different seed or prompt, or manually create more diverse assets."
        audience = ["creative"]
    else: # pipeline_error
        impact = "A technical failure occurred in the asset generation pipeline, preventing creative production."
        next_steps = "Review the pipeline logs to diagnose the failure. The system may need to be restarted."
        audience = ["it"]

    # Include compliance and metrics context if available
    compliance = {}
    try:
        comp_map = state.get('compliance_data', {})
        # If product-level report exists, pick any; else use aggregate score
        if isinstance(comp_map, dict) and comp_map:
            # Flatten to find overall score and any issues
            scores = []
            all_issues = []
            for v in comp_map.values():
                if isinstance(v, dict):
                    if 'overall_score' in v:
                        scores.append(v['overall_score'])
                    if isinstance(v.get('all_issues'), list):
                        all_issues.extend(v['all_issues'])
            if scores:
                compliance['overall_score'] = sum(scores)/len(scores)
            compliance['issues'] = all_issues
            compliance['issues_count'] = len(all_issues)
    except Exception:
        pass

    metrics = state.get('performance_metrics', {})
    context = {
        'compliance': compliance,
        'metrics': {
            'variant_count': metrics.get('variant_count', 0),
            'quality_score': metrics.get('quality_score', 0.0),
            'localization_score': metrics.get('localization_score', 0.0),
            'compliance_score': metrics.get('compliance_score', 0.0),
        },
        'guidance': state.get('prompt_guidance', {}),
    }

    # Determine severity from compliance/quality
    severity = 'warning'
    try:
        if metrics.get('compliance_score', 0.0) < 0.5:
            severity = 'critical'
        elif metrics.get('quality_score', 0.0) < 0.6:
            severity = 'warning'
    except Exception:
        pass
    context['severity'] = severity

    built_mcp = mcp.build_mcp_extended(campaign, issue_type, impact, next_steps, audience, context)
    state['mcp'] = built_mcp
    return state

def draft_human_message(state: Dict[str, Any]) -> Dict[str, Any]:
    """Uses MCP + Gemini (if available) to draft a human-readable alert message."""
    # Prepare MCP structures (and typed message if SDK enabled)
    _ = format_with_mcp_sdk(state['mcp'], state)

    # Attempt Gemini generation
    human_message = _try_generate_with_gemini(state['mcp'])
    if not human_message:
        # Fallback to a deterministic, human-readable template
        issue_type = state['mcp']['issue']
        campaign = state['mcp']['campaign']
        human_message = (
            f"Warning: The '{campaign}' campaign triggered an alert for '{issue_type}'. "
            f"{state['mcp']['impact']} Suggested action: {state['mcp']['suggested_next_steps']}"
        )
    state['human_message'] = human_message
    return state


def _import_mcp_types():
    """Try importing the official Model Context Protocol Python SDK types.

    Returns the imported module (types) or None if unavailable.
    """
    try:
        # Primary import path per https://github.com/modelcontextprotocol/python-sdk
        from mcp import types as mcp_types  # type: ignore
        return mcp_types
    except Exception:
        try:
            # Alternate package name (defensive)
            from modelcontextprotocol import types as mcp_types  # type: ignore
            return mcp_types
        except Exception:
            return None


def format_with_mcp_sdk(mcp_payload: Dict[str, Any], state: Dict[str, Any] | None = None) -> str:
    """Attempt to use the MCP SDK (if installed) to format a prompt.

    If the SDK is unavailable or USE_MCP_SDK is not enabled, fall back to plain text prompt.
    """
    use_sdk = os.getenv("USE_MCP_SDK", "false").lower() == "true"
    if not use_sdk:
        return mcp.format_mcp_for_llm(mcp_payload)
    try:
        mcp_types = _import_mcp_types()
        if mcp_types is None:
            return mcp.format_mcp_for_llm(mcp_payload)

        # Build a typed MCP user message containing the structured MCP payload as text content.
        json_block = json.dumps(mcp_payload, indent=2)
        text_content = mcp_types.TextContent(text=json_block)  # type: ignore[attr-defined]
        typed_message = mcp_types.Message(role="user", content=[text_content])  # type: ignore[attr-defined]

        # Expose typed message for downstream consumers (emit_alert will include it too)
        if isinstance(state, dict):
            state["mcp_typed_message"] = {
                "role": typed_message.role,
                "content": [{"type": "text", "text": json_block}],
            }

        # Also return a deterministic prompt for LLMs that don't speak MCP yet
        return (
            "You are an AI assistant. Use the following MCP JSON to produce an alert.\n"
            f"---\n{json_block}\n---\n"
            "Draft a concise, actionable message for the specified audience."
        )
    except Exception:
        return mcp.format_mcp_for_llm(mcp_payload)

def emit_alert(state: Dict[str, Any]) -> Dict[str, Any]:
    """Publishes the final alert to the Kafka topic."""
    try:
        mcp_data = state['mcp']
        alert = {
            "event_id": str(uuid.uuid4()),
            "ts": datetime.now(timezone.utc).isoformat(),
            "severity": "warning", # Could be dynamic
            "campaign_name": state['campaign_name'],
            "issue": mcp_data['issue'],
            "detail": mcp_data['impact'],
            "audience": mcp_data['target_audience'],
            "human_message": state['human_message'],
            "mcp": mcp_data,
        }
        if 'mcp_typed_message' in state:
            alert['mcp_typed_message'] = state['mcp_typed_message']
        
        producer = get_kafka_producer()
        future = producer.send(TOPIC_ALERTS, alert)
        
        # Wait for the message to be sent
        record_metadata = future.get(timeout=10)
        print(f"\n--- ALERT EMITTED for {state['campaign_name']} ---")
        print(f"Issue: {alert['issue']}")
        print(f"Message: {alert['human_message']}")
        print(f"Topic: {TOPIC_ALERTS}, Partition: {record_metadata.partition}, Offset: {record_metadata.offset}\n")
        
        # Close the producer
        producer.close()
        
        return state # Return state to terminate the graph gracefully
        
    except Exception as e:
        print(f"Failed to emit alert: {e}")
        # Continue execution even if alert fails
        return state
