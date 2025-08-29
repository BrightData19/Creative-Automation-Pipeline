# /apps/agent-worker/agent_graph.py

import json
import os
import time
from typing import TypedDict, List, Dict, Any, Optional

from dotenv import load_dotenv
from kafka import KafkaConsumer
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable, KafkaError
from kafka.admin import KafkaAdminClient
from langgraph.graph import StateGraph, END

from nodes import evaluate, retry, alerting
from nodes import approvals as approvals_node

load_dotenv()

# --- Kafka Configuration ---
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC_ASSETS_CREATED = "assets.created.v1"
TOPIC_COMPLIANCE = "compliance.v1"
TOPIC_PIPELINE_STATUS = "pipeline.status.v1"
TOPIC_BRIEFS_INGEST = "briefs.ingest.v1"
TOPIC_APPROVALS_REQUEST = "approvals.request.v1"
TOPIC_APPROVALS_DECISION = "approvals.decision.v1"

# --- Enhanced Agent State Definition ---
class AgentState(TypedDict):
    campaign_name: str
    products: Dict[str, Any]  # Tracks assets and hashes per product
    issues: List[Dict[str, Any]]  # List of detected issues
    attempts: Dict[str, int]  # Retry attempts per product
    new_event: Dict[str, Any]  # The incoming Kafka event
    mcp: Dict[str, Any]  # The structured alert context
    human_message: str  # The final human-readable message
    compliance_data: Dict[str, Any]  # Compliance tracking data
    localization_data: Dict[str, Any]  # Localization tracking data
    performance_metrics: Dict[str, Any]  # Performance and quality metrics

# --- Kafka Health Check ---
def check_kafka_health() -> bool:
    """Check if Kafka broker is accessible."""
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=KAFKA_BROKER,
            client_id='agent-worker-health-check'
        )
        admin_client.list_topics()
        admin_client.close()
        return True
    except Exception as e:
        print(f"Kafka health check failed: {e}")
        return False

# --- Enhanced Graph Definition ---
def build_graph():
    workflow = StateGraph(AgentState)

    # Add enhanced nodes
    workflow.add_node("track_outputs", evaluate.track_outputs)
    workflow.add_node("evaluate_quality", evaluate.evaluate_product_quality)
    workflow.add_node("evaluate_compliance", evaluate.evaluate_compliance)
    workflow.add_node("evaluate_localization", evaluate.evaluate_localization)
    workflow.add_node("compose_alert", alerting.compose_alert_mcp)
    workflow.add_node("draft_message", alerting.draft_human_message)
    workflow.add_node("emit_alert", alerting.emit_alert)

    # Define enhanced workflow
    workflow.set_entry_point("track_outputs")
    workflow.add_edge("track_outputs", "evaluate_quality")
    workflow.add_edge("evaluate_quality", "evaluate_compliance")
    workflow.add_edge("evaluate_compliance", "evaluate_localization")
    
    # Conditional edge: after comprehensive evaluation, either finish or proceed to alerting
    workflow.add_conditional_edges(
        "evaluate_localization",
        retry.retry_or_finalize_enhanced,
        {
            "compose_alert": "compose_alert",
            "__end__": END
        }
    )
    
    workflow.add_edge("compose_alert", "draft_message")
    workflow.add_edge("draft_message", "emit_alert")
    workflow.add_edge("emit_alert", END)

    return workflow.compile()

# --- Kafka Consumer ---
def get_kafka_consumer(topics: List[str]) -> KafkaConsumer:
    """Get a Kafka consumer for multiple topics with retry logic and health checks."""
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            if not check_kafka_health():
                raise NoBrokersAvailable("Kafka broker not healthy")
                
            consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=KAFKA_BROKER,
                auto_offset_reset='earliest',
                group_id='agent-worker-group',
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
                client_id=f'agent-worker-consumer-{topics[0]}'
            )
            print(f"Kafka consumer for topics {topics} connected successfully.")
            return consumer
        except (NoBrokersAvailable, KafkaError) as e:
            retry_count += 1
            wait_time = min(5 * retry_count, 30)
            print(f"Kafka broker not available for consumer (attempt {retry_count}/{max_retries}). Retrying in {wait_time} seconds...")
            print(f"Error: {e}")
            time.sleep(wait_time)
    
    raise Exception(f"Failed to connect consumer to Kafka after {max_retries} attempts")

# --- Enhanced Event Processing ---
def process_event(event: Dict[str, Any], campaign_states: Dict[str, AgentState]) -> AgentState:
    """Process an event and update campaign state accordingly."""
    event_type = event.get('topic', 'unknown')
    campaign = event.get('campaign_name', 'unknown')
    
    # Initialize campaign state if not exists
    if campaign not in campaign_states:
        campaign_states[campaign] = {
            "campaign_name": campaign,
            "products": {},
            "issues": [],
            "attempts": {},
            "new_event": None,
            "mcp": {},
            "human_message": "",
            "compliance_data": {},
            "localization_data": {},
            "performance_metrics": {
                "total_assets": 0,
                "compliance_score": 0.0,
                "localization_score": 0.0,
                "quality_score": 0.0,
                "processing_time": 0.0
            }
        }
    
    state = campaign_states[campaign]
    state["new_event"] = event
    
    # Process based on event type
    if event_type == TOPIC_ASSETS_CREATED:
        process_assets_created_event(event, state)
    elif event_type == TOPIC_COMPLIANCE:
        process_compliance_event(event, state)
    elif event_type == TOPIC_PIPELINE_STATUS:
        process_pipeline_status_event(event, state)
    elif event_type == TOPIC_BRIEFS_INGEST:
        # Store the latest brief to enable automated retries
        state['brief'] = event
    
    return state

def process_assets_created_event(event: Dict[str, Any], state: AgentState):
    """Process assets created event."""
    product = event.get('product', 'unknown')
    variants = event.get('variants', [])
    
    if product not in state['products']:
        state['products'][product] = {
            'variants': [],
            'hashes': [],
            'metadata': {}
        }
    
    # Update product data
    state['products'][product]['variants'].extend(variants)
    
    # Extract metadata
    for variant in variants:
        if 'target_market' in variant:
            state['localization_data'][variant['target_market']] = True
        if 'compliance_score' in variant:
            state['compliance_data'][product] = variant['compliance_score']
    
    # Update performance metrics
    state['performance_metrics']['total_assets'] = sum(len(p['variants']) for p in state['products'].values())

def process_compliance_event(event: Dict[str, Any], state: AgentState):
    """Process compliance event."""
    product = event.get('product', 'unknown')
    compliance_report = event.get('compliance_report', {})
    
    if product not in state['compliance_data']:
        state['compliance_data'][product] = {}
    
    # Store compliance data
    state['compliance_data'][product] = compliance_report
    
    # Update overall compliance score
    if state['compliance_data']:
        scores = [data.get('overall_score', 0.0) for data in state['compliance_data'].values() if isinstance(data, dict)]
        if scores:
            state['performance_metrics']['compliance_score'] = sum(scores) / len(scores)

def process_pipeline_status_event(event: Dict[str, Any], state: AgentState):
    """Process pipeline status event."""
    stage = event.get('stage', 'unknown')
    product = event.get('product', 'unknown')
    
    # Track processing stages
    if 'processing_stages' not in state['performance_metrics']:
        state['performance_metrics']['processing_stages'] = {}
    
    if product not in state['performance_metrics']['processing_stages']:
        state['performance_metrics']['processing_stages'][product] = []
    
    state['performance_metrics']['processing_stages'][product].append({
        'stage': stage,
        'timestamp': event.get('ts', ''),
        'detail': event.get('detail', '')
    })

# --- Main Execution Loop ---
if __name__ == "__main__":
    print("Enhanced Agent worker starting...")
    print("Features: Comprehensive monitoring, compliance tracking, localization support")
    
    # Check Kafka health before starting
    print("Checking Kafka broker health...")
    if not check_kafka_health():
        print("Kafka broker is not accessible. Please ensure the broker is running.")
        exit(1)
    
    app = build_graph()
    
    # Subscribe to multiple topics for comprehensive monitoring
    topics = [TOPIC_ASSETS_CREATED, TOPIC_COMPLIANCE, TOPIC_PIPELINE_STATUS, TOPIC_BRIEFS_INGEST, TOPIC_APPROVALS_REQUEST, TOPIC_APPROVALS_DECISION]
    consumer = get_kafka_consumer(topics)
    
    # Maintain a persistent state for each campaign across multiple events
    campaign_states: Dict[str, AgentState] = {}

    try:
        for message in consumer:
            try:
                event = message.value
                event['topic'] = message.topic  # Add topic information
                
                campaign = event.get('campaign_name', 'unknown')
                print(f"\nReceived {message.topic} event for campaign: {campaign}")

                # Process the event and update campaign state
                updated_state = process_event(event, campaign_states)
                
                # Approval request Slack notification
                if message.topic == TOPIC_APPROVALS_REQUEST:
                    approvals_node.post_slack_approval(
                        campaign,
                        event.get('product', 'unknown'),
                        event.get('variants', [])
                    )
                # Finalize or reject on approval decision
                if message.topic == TOPIC_APPROVALS_DECISION:
                    try:
                        p = KafkaProducer(
                            bootstrap_servers=KAFKA_BROKER,
                            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                            acks='all',
                            retries=3,
                            compression_type='gzip'
                        )
                        stage = 'approved' if (event.get('decision') == 'approved') else 'rejected'
                        status_evt = {
                            'event_id': os.urandom(8).hex(),
                            'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                            'campaign_name': campaign,
                            'product': event.get('product', 'unknown'),
                            'stage': stage,
                            'detail': 'Approval decision received',
                        }
                        p.send(TOPIC_PIPELINE_STATUS, status_evt).get(timeout=10)
                        p.close()
                    except Exception as e:
                        print(f"Failed to emit pipeline status for approval decision: {e}")
                # Run the enhanced graph for this campaign
                try:
                    result = app.invoke(updated_state)
                    print(f"Enhanced graph execution completed for campaign: {campaign}")
                    
                    # Update the stored state
                    campaign_states[campaign] = result
                    
                    # Log performance metrics
                    metrics = result.get('performance_metrics', {})
                    print(f"Campaign {campaign} metrics:")
                    print(f"  - Total assets: {metrics.get('total_assets', 0)}")
                    print(f"  - Compliance score: {metrics.get('compliance_score', 0.0):.2f}")
                    print(f"  - Localization markets: {len(result.get('localization_data', {}))}")
                    
                except Exception as e:
                    print(f"Error executing enhanced graph for campaign {campaign}: {e}")
                    # Continue processing other campaigns
                    
            except Exception as e:
                print(f"Error processing message: {e}")
                # Continue processing other messages
                
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    finally:
        consumer.close()
        print("Enhanced Agent worker shutdown complete.")
