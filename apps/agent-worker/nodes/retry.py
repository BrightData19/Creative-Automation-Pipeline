# /apps/agent-worker/nodes/retry.py

from typing import Dict, Any, Literal
import os
import json
import uuid
from datetime import datetime, timezone
from kafka import KafkaProducer

def retry_or_finalize(state: Dict[str, Any]) -> Literal["compose_alert", "__end__"]:
    """
    Enhanced retry logic that considers multiple evaluation factors.
    """
    issues = state.get('issues', [])
    attempts = state.get('attempts', {})
    performance_metrics = state.get('performance_metrics', {})
    
    # Check if we have critical issues that require immediate attention
    critical_issues = [i for i in issues if i.get('severity') == 'high']
    medium_issues = [i for i in issues if i.get('severity') == 'medium']
    
    # If we have critical issues, always alert
    if critical_issues:
        print(f"[RETRY] Critical issues detected: {len(critical_issues)}. Proceeding to alert.")
        return "compose_alert"
    
    # Check performance metrics
    overall_score = performance_metrics.get('overall_performance_score', 0.0)
    compliance_score = performance_metrics.get('compliance_score', 0.0)
    localization_score = performance_metrics.get('localization_score', 0.0)
    quality_score = performance_metrics.get('quality_score', 0.0)
    
    # Determine if retry is needed based on multiple factors
    needs_retry = False
    retry_reason = []
    
    # Check compliance threshold
    if compliance_score < 0.8:
        needs_retry = True
        retry_reason.append(f"Compliance score {compliance_score:.2f} below threshold 0.8")
    
    # Check localization threshold
    if localization_score < 0.7:
        needs_retry = True
        retry_reason.append(f"Localization score {localization_score:.2f} below threshold 0.7")
    
    # Check quality threshold
    if quality_score < 0.6:
        needs_retry = True
        retry_reason.append(f"Quality score {quality_score:.2f} below threshold 0.6")
    
    # Check overall performance
    if overall_score < 0.75:
        needs_retry = True
        retry_reason.append(f"Overall performance score {overall_score:.2f} below threshold 0.75")
    
    # Check if we have too many medium issues
    if len(medium_issues) > 3:
        needs_retry = True
        retry_reason.append(f"Too many medium issues: {len(medium_issues)}")
    
    # If retry is needed, check if we haven't exceeded max attempts
    if needs_retry:
        campaign_name = state.get('campaign_name', 'unknown')
        current_attempts = attempts.get(campaign_name, 0)
        max_attempts = 3
        
        if current_attempts < max_attempts:
            print(f"[RETRY] Retry needed for campaign {campaign_name}. Attempt {current_attempts + 1}/{max_attempts}")
            print(f"[RETRY] Reasons: {'; '.join(retry_reason)}")
            
            # Increment attempt counter
            attempts[campaign_name] = current_attempts + 1
            
            # Add retry recommendation to state
            if 'retry_recommendations' not in state:
                state['retry_recommendations'] = []
            
            state['retry_recommendations'].append({
                'attempt': current_attempts + 1,
                'reasons': retry_reason,
                'timestamp': 'now'  # In production, use actual timestamp
            })
            # Trigger automated regeneration by re-publishing the original brief
            brief = state.get('brief')
            if brief:
                try:
                    producer = KafkaProducer(
                        bootstrap_servers=os.getenv("KAFKA_BROKER", "localhost:9092"),
                        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                        retries=3,
                        acks='all',
                        compression_type='gzip',
                        client_id='agent-worker-retry-producer'
                    )
                    event = dict(brief)
                    event['event_id'] = str(uuid.uuid4())
                    event['ts'] = datetime.now(timezone.utc).isoformat()
                    event['retry_attempt'] = current_attempts + 1
                    future = producer.send("briefs.ingest.v1", event)
                    future.get(timeout=10)
                    producer.close()
                    print(f"[RETRY] Re-published brief for campaign {campaign_name} (attempt {current_attempts + 1})")
                except Exception as e:
                    print(f"[RETRY] Failed to publish retry brief: {e}")
            
            return "__end__"  # End current workflow, retry will be handled externally
        else:
            print(f"[RETRY] Max retry attempts ({max_attempts}) exceeded for campaign {campaign_name}. Proceeding to alert.")
            return "compose_alert"
    
    # No retry needed, campaign is acceptable
    print(f"[RETRY] Campaign {state.get('campaign_name', 'unknown')} meets quality standards. No retry needed.")
    return "__end__"

def retry_or_finalize_enhanced(state: Dict[str, Any]) -> Literal["compose_alert", "__end__"]:
    """
    Enhanced retry logic that provides detailed analysis and recommendations.
    """
    issues = state.get('issues', [])
    attempts = state.get('attempts', {})
    performance_metrics = state.get('performance_metrics', {})
    campaign_name = state.get('campaign_name', 'unknown')
    
    # Comprehensive issue analysis
    critical_issues = [i for i in issues if i.get('severity') == 'high']
    medium_issues = [i for i in issues if i.get('severity') == 'medium']
    low_issues = [i for i in issues if i.get('severity') == 'low']
    
    # Performance analysis
    overall_score = performance_metrics.get('overall_performance_score', 0.0)
    compliance_score = performance_metrics.get('compliance_score', 0.0)
    localization_score = performance_metrics.get('localization_score', 0.0)
    quality_score = performance_metrics.get('quality_score', 0.0)
    
    # Create detailed analysis
    analysis = {
        'campaign_name': campaign_name,
        'overall_score': overall_score,
        'component_scores': {
            'compliance': compliance_score,
            'localization': localization_score,
            'quality': quality_score
        },
        'issue_summary': {
            'critical': len(critical_issues),
            'medium': len(medium_issues),
            'low': len(low_issues),
            'total': len(issues)
        },
        'recommendations': []
    }
    
    # Generate specific recommendations
    if compliance_score < 0.8:
        analysis['recommendations'].append({
            'type': 'compliance',
            'priority': 'high' if compliance_score < 0.5 else 'medium',
            'action': 'Review brand guidelines and regenerate assets with proper compliance',
            'score': compliance_score
        })
    
    if localization_score < 0.7:
        analysis['recommendations'].append({
            'type': 'localization',
            'priority': 'medium',
            'action': 'Ensure all target markets have proper localized variants',
            'score': localization_score
        })
    
    if quality_score < 0.6:
        analysis['recommendations'].append({
            'type': 'quality',
            'priority': 'medium',
            'action': 'Regenerate assets with improved diversity and quality',
            'score': quality_score
        })
    
    if len(critical_issues) > 0:
        analysis['recommendations'].append({
            'type': 'critical_issues',
            'priority': 'high',
            'action': 'Address critical issues before proceeding',
            'count': len(critical_issues)
        })
    
    # Store analysis in state
    state['campaign_analysis'] = analysis
    
    # Determine if retry is needed
    needs_retry = (
        compliance_score < 0.8 or
        localization_score < 0.7 or
        quality_score < 0.6 or
        len(critical_issues) > 0 or
        overall_score < 0.75
    )
    
    if needs_retry:
        current_attempts = attempts.get(campaign_name, 0)
        max_attempts = 3
        
        if current_attempts < max_attempts:
            print(f"[RETRY] Enhanced retry analysis for {campaign_name}:")
            print(f"  - Overall score: {overall_score:.2f}")
            print(f"  - Compliance: {compliance_score:.2f}")
            print(f"  - Localization: {localization_score:.2f}")
            print(f"  - Quality: {quality_score:.2f}")
            print(f"  - Critical issues: {len(critical_issues)}")
            print(f"  - Attempt {current_attempts + 1}/{max_attempts}")
            
            # Increment attempt counter
            attempts[campaign_name] = current_attempts + 1
            
            # Add detailed retry information
            if 'retry_details' not in state:
                state['retry_details'] = []
            
            state['retry_details'].append({
                'attempt': current_attempts + 1,
                'analysis': analysis,
                'timestamp': 'now'
            })
            # Re-publish the original brief with prompt guidance to trigger regeneration
            brief = state.get('brief')
            if brief:
                try:
                    producer = KafkaProducer(
                        bootstrap_servers=os.getenv("KAFKA_BROKER", "localhost:9092"),
                        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                        retries=3,
                        acks='all',
                        compression_type='gzip',
                        client_id='agent-worker-retry-producer'
                    )
                    event = dict(brief)
                    event['event_id'] = str(uuid.uuid4())
                    event['ts'] = datetime.now(timezone.utc).isoformat()
                    event['retry_attempt'] = current_attempts + 1
                    # Attach prompt guidance if available
                    if 'prompt_guidance' in state:
                        event['prompt_guidance'] = state['prompt_guidance']
                    future = producer.send("briefs.ingest.v1", event)
                    future.get(timeout=10)
                    producer.close()
                    print(f"[RETRY] Re-published brief with prompt guidance for campaign {campaign_name} (attempt {current_attempts + 1})")
                except Exception as e:
                    print(f"[RETRY] Failed to publish retry brief: {e}")

            return "__end__"
        else:
            print(f"[RETRY] Max retry attempts exceeded for {campaign_name}. Proceeding to alert.")
            return "compose_alert"
    
    # Campaign meets standards
    print(f"[RETRY] Campaign {campaign_name} meets all quality standards:")
    print(f"  - Overall score: {overall_score:.2f}")
    print(f"  - No critical issues")
    print(f"  - All component scores above thresholds")
    
    return "__end__"

def should_retry_campaign(state: Dict[str, Any]) -> bool:
    """
    Helper function to determine if a campaign should be retried.
    """
    performance_metrics = state.get('performance_metrics', {})
    
    # Check if any critical thresholds are not met
    compliance_score = performance_metrics.get('compliance_score', 0.0)
    localization_score = performance_metrics.get('localization_score', 0.0)
    quality_score = performance_metrics.get('quality_score', 0.0)
    overall_score = performance_metrics.get('overall_performance_score', 0.0)
    
    # Check for critical issues
    issues = state.get('issues', [])
    critical_issues = [i for i in issues if i.get('severity') == 'high']
    
    return (
        compliance_score < 0.8 or
        localization_score < 0.7 or
        quality_score < 0.6 or
        overall_score < 0.75 or
        len(critical_issues) > 0
    )

def get_retry_priority(state: Dict[str, Any]) -> str:
    """
    Determine the priority level for retry actions.
    """
    performance_metrics = state.get('performance_metrics', {})
    issues = state.get('issues', [])
    
    compliance_score = performance_metrics.get('compliance_score', 0.0)
    critical_issues = [i for i in issues if i.get('severity') == 'high']
    
    if compliance_score < 0.5 or len(critical_issues) > 2:
        return "urgent"
    elif compliance_score < 0.8 or len(critical_issues) > 0:
        return "high"
    else:
        return "medium"
