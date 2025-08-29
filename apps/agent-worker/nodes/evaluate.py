# /apps/agent-worker/nodes/evaluate.py

import imagehash
from typing import Any, Dict, List

# Import dropbox_io from the parent directory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dropbox_io

# --- Enhanced Configuration ---
DIVERSITY_THRESHOLD = 5  # Hamming distance threshold for phash
MIN_VARIANTS = 3
COMPLIANCE_THRESHOLD = 0.8  # Minimum compliance score
LOCALIZATION_THRESHOLD = 0.7  # Minimum localization score

# --- Enhanced Diversity and Count Evaluation ---
def track_outputs(state: Dict[str, Any]) -> Dict[str, Any]:
    """Updates the state with newly created assets and calculates their hashes."""
    event = state['new_event']
    # Only process asset creation events here
    if event.get('topic') != 'assets.created.v1':
        return state
    product_name = event.get('product', 'unknown')
    
    # Initialize tracking for the product if not present
    if product_name not in state['products']:
        state['products'][product_name] = {'variants': [], 'hashes': [], 'metadata': {}}

    # Download image, calculate phash, and add to state
    for variant in event.get('variants', []):
        dbx_path = variant.get('path', '').replace("dropbox:", "")
        if dbx_path:
            try:
                img = dropbox_io.download_pil_image(dbx_path)
                h = str(imagehash.phash(img))
                state['products'][product_name]['variants'].append(variant)
                state['products'][product_name]['hashes'].append(h)
                
                # Store additional metadata
                if 'metadata' not in state['products'][product_name]:
                    state['products'][product_name]['metadata'] = {}
                
                state['products'][product_name]['metadata'][variant.get('ratio', 'unknown')] = {
                    'hash': h,
                    'target_market': variant.get('target_market', 'unknown'),
                    'compliance_score': variant.get('compliance_score', 0.0),
                    'localized': variant.get('localized', False)
                }
                
                print(f"Tracked output for {product_name}: {variant.get('ratio', 'unknown')} (phash: {h})")
            except Exception as e:
                print(f"Could not process image {dbx_path}: {e}")
                # Add an issue to the state to be handled later
                state['issues'].append({
                    'type': 'pipeline_error',
                    'detail': f"Failed to download or hash image {dbx_path}.",
                    'severity': 'high'
                })

    return state

def evaluate_product_quality(state: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluates a single product's generated assets for count and diversity."""
    # Only evaluate quality right after assets are created
    if state['new_event'].get('topic') != 'assets.created.v1':
        return state
    product_name = state['new_event'].get('product', 'unknown')
    if product_name not in state['products']:
        state['issues'].append({
            'type': 'missing_product_data',
            'detail': f"No product data found for {product_name}",
            'severity': 'high'
        })
        return state
    
    product_data = state['products'][product_name]
    
    # 1. Check variant count
    if len(product_data['variants']) < MIN_VARIANTS:
        print(f"[EVAL] Insufficient variants for {product_name}. Found {len(product_data['variants'])}, need {MIN_VARIANTS}.")
        state['issues'].append({
            'type': 'insufficient_variants',
            'product': product_name,
            'detail': f"Expected {MIN_VARIANTS} variants, but only found {len(product_data['variants'])}",
            'severity': 'medium'
        })
        # Add prompt guidance to encourage more variety on retry
        _add_prompt_guidance(state, product_name, [
            "Create distinctly different backgrounds (outdoor, studio, lifestyle)",
            "Vary camera angle and framing (top-down, close-up, wide)",
            "Use different compositions (rule of thirds, centered, asymmetrical)",
            "Introduce or remove human elements (hand interaction, model usage)",
            "Change lighting styles (soft daylight, dramatic contrast, warm indoor)",
            "Add context props relevant to the product use-case",
        ])
        return state

    # 2. Check diversity
    hashes = [imagehash.hex_to_hash(h) for h in product_data['hashes']]
    is_diverse = True
    diversity_score = 1.0
    
    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            distance = hashes[i] - hashes[j]
            if distance < DIVERSITY_THRESHOLD:
                print(f"[EVAL] Low diversity detected for {product_name}. Distance between hashes: {distance}")
                is_diverse = False
                diversity_score = min(diversity_score, distance / DIVERSITY_THRESHOLD)
    
    if not is_diverse:
        state['issues'].append({
            'type': 'insufficient_diversity',
            'product': product_name,
            'detail': f"Generated images are too similar (Hamming distance < {DIVERSITY_THRESHOLD}).",
            'severity': 'medium'
        })
        # Add prompt guidance to drive diversity on retry
        _add_prompt_guidance(state, product_name, [
            "Alter color palettes while staying brand-compliant",
            "Switch environments (kitchen, gym, office, outdoors)",
            "Change camera perspective (eye-level, low-angle, macro)",
            "Use different surfaces/textures (wood, marble, concrete)",
            "Include motion or action where appropriate",
        ])
    
    # Update performance metrics
    if 'performance_metrics' not in state:
        state['performance_metrics'] = {}
    
    state['performance_metrics']['quality_score'] = diversity_score
    state['performance_metrics']['variant_count'] = len(product_data['variants'])
    
    print(f"[EVAL] Quality evaluation complete for {product_name}. Quality score: {diversity_score:.2f}")
    return state

def evaluate_compliance(state: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluates compliance across all products in the campaign."""
    campaign_name = state.get('campaign_name', 'unknown')
    compliance_data = state.get('compliance_data', {})
    
    if not compliance_data:
        print(f"[EVAL] No compliance data available for campaign {campaign_name}")
        return state
    
    overall_compliance_score = 0.0
    compliance_issues = []
    total_products = len(compliance_data)
    
    for product_name, compliance_report in compliance_data.items():
        if isinstance(compliance_report, dict):
            product_score = compliance_report.get('overall_score', 0.0)
            overall_compliance_score += product_score
            
            # Check for critical compliance issues
            if product_score < COMPLIANCE_THRESHOLD:
                compliance_issues.append({
                    'product': product_name,
                    'score': product_score,
                    'issues': compliance_report.get('all_issues', [])
                })
                
                state['issues'].append({
                    'type': 'compliance_failure',
                    'product': product_name,
                    'detail': f"Compliance score {product_score:.2f} below threshold {COMPLIANCE_THRESHOLD}",
                    'severity': 'high' if product_score < 0.5 else 'medium'
                })
                # Add targeted prompt guidance from breakdown
                breakdown = compliance_report.get('compliance_breakdown', {})
                logo_c = breakdown.get('logo_compliance', {})
                color_c = breakdown.get('color_compliance', {})
                text_c = breakdown.get('text_compliance', {})
                guidance: List[str] = []
                if not logo_c.get('logo_detected', True) or not logo_c.get('meets_size_requirement', True):
                    guidance.append("Ensure brand logo is visible and sized 5–10% of image area (e.g., top-right)")
                if color_c.get('compliance_score', 1.0) < 0.7:
                    guidance.append("Increase usage of primary brand colors in backgrounds or accents")
                if text_c.get('issues'):
                    guidance.append("Remove prohibited words/symbols and keep copy concise")
                if guidance:
                    _add_prompt_guidance(state, product_name, guidance)
    
    if total_products > 0:
        overall_compliance_score /= total_products
    
    # Update performance metrics
    if 'performance_metrics' not in state:
        state['performance_metrics'] = {}
    
    state['performance_metrics']['compliance_score'] = overall_compliance_score
    state['performance_metrics']['compliance_issues_count'] = len(compliance_issues)
    
    print(f"[EVAL] Compliance evaluation complete for campaign {campaign_name}. Overall score: {overall_compliance_score:.2f}")
    
    # Add compliance summary to issues if there are problems
    if compliance_issues:
        state['issues'].append({
            'type': 'compliance_summary',
            'detail': f"Campaign has {len(compliance_issues)} products with compliance issues",
            'severity': 'medium',
            'compliance_details': compliance_issues
        })
    
    return state

def evaluate_localization(state: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluates localization coverage and quality across the campaign."""
    campaign_name = state.get('campaign_name', 'unknown')
    localization_data = state.get('localization_data', {})
    products = state.get('products', {})
    
    if not localization_data:
        print(f"[EVAL] No localization data available for campaign {campaign_name}")
        return state
    
    # Count localized markets
    localized_markets = list(localization_data.keys())
    total_markets = len(localized_markets)
    
    # Check localization coverage per product
    localization_coverage = {}
    total_localization_score = 0.0
    
    for product_name, product_data in products.items():
        product_variants = product_data.get('variants', [])
        localized_variants = [v for v in product_variants if v.get('localized', False)]
        
        if product_variants:
            coverage = len(localized_variants) / len(product_variants)
            localization_coverage[product_name] = coverage
            total_localization_score += coverage
        else:
            localization_coverage[product_name] = 0.0
    
    # Calculate overall localization score
    if products:
        overall_localization_score = total_localization_score / len(products)
    else:
        overall_localization_score = 0.0
    
    # Check for localization issues
    if overall_localization_score < LOCALIZATION_THRESHOLD:
        state['issues'].append({
            'type': 'insufficient_localization',
            'detail': f"Localization score {overall_localization_score:.2f} below threshold {LOCALIZATION_THRESHOLD}",
            'severity': 'medium'
        })
        # Add general localization guidance
        markets = list(state.get('localization_data', {}).keys()) or ["target market"]
        _add_prompt_guidance(state, None, [
            f"Incorporate visual cues relevant to {', '.join(markets)} market(s)",
            "Ensure any on-image text is localized and culturally appropriate",
        ])
    
    # Check if all products have variants for all markets
    expected_variants_per_market = len(products) * 3  # 3 aspect ratios
    actual_variants = sum(len(p.get('variants', [])) for p in products.values())
    
    if actual_variants < expected_variants_per_market:
        state['issues'].append({
            'type': 'incomplete_localization',
            'detail': f"Expected {expected_variants_per_market} total variants, found {actual_variants}",
            'severity': 'low'
        })
    
    # Update performance metrics
    if 'performance_metrics' not in state:
        state['performance_metrics'] = {}
    
    state['performance_metrics']['localization_score'] = overall_localization_score
    state['performance_metrics']['localized_markets_count'] = total_markets
    state['performance_metrics']['localization_coverage'] = localization_coverage
    
    print(f"[EVAL] Localization evaluation complete for campaign {campaign_name}")
    print(f"  - Localized markets: {total_markets}")
    print(f"  - Overall localization score: {overall_localization_score:.2f}")
    print(f"  - Products with localization: {len([c for c in localization_coverage.values() if c > 0])}")
    
    return state


def _add_prompt_guidance(state: Dict[str, Any], product_name: str | None, suggestions: List[str]):
    """Accumulate prompt guidance suggestions per product to inform regeneration prompts."""
    if 'prompt_guidance' not in state:
        state['prompt_guidance'] = {}
    key = product_name or '__campaign__'
    state['prompt_guidance'].setdefault(key, [])
    existing = set(state['prompt_guidance'][key])
    for s in suggestions:
        if s not in existing:
            state['prompt_guidance'][key].append(s)
            existing.add(s)

def evaluate_campaign_performance(state: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluates overall campaign performance and generates summary metrics."""
    campaign_name = state.get('campaign_name', 'unknown')
    performance_metrics = state.get('performance_metrics', {})
    issues = state.get('issues', [])
    
    # Calculate overall performance score
    scores = []
    if 'quality_score' in performance_metrics:
        scores.append(performance_metrics['quality_score'])
    if 'compliance_score' in performance_metrics:
        scores.append(performance_metrics['compliance_score'])
    if 'localization_score' in performance_metrics:
        scores.append(performance_metrics['localization_score'])
    
    overall_performance_score = sum(scores) / len(scores) if scores else 0.0
    
    # Categorize issues by severity
    critical_issues = [i for i in issues if i.get('severity') == 'high']
    medium_issues = [i for i in issues if i.get('severity') == 'medium']
    low_issues = [i for i in issues if i.get('severity') == 'low']
    
    # Update performance metrics
    performance_metrics['overall_performance_score'] = overall_performance_score
    performance_metrics['total_issues'] = len(issues)
    performance_metrics['critical_issues_count'] = len(critical_issues)
    performance_metrics['medium_issues_count'] = len(medium_issues)
    performance_metrics['low_issues_count'] = len(low_issues)
    
    # Determine campaign status
    if overall_performance_score >= 0.9 and len(critical_issues) == 0:
        campaign_status = "excellent"
    elif overall_performance_score >= 0.8 and len(critical_issues) == 0:
        campaign_status = "good"
    elif overall_performance_score >= 0.7 and len(critical_issues) <= 1:
        campaign_status = "acceptable"
    else:
        campaign_status = "needs_attention"
    
    performance_metrics['campaign_status'] = campaign_status
    
    print(f"[EVAL] Campaign performance evaluation complete for {campaign_name}")
    print(f"  - Overall performance score: {overall_performance_score:.2f}")
    print(f"  - Campaign status: {campaign_status}")
    print(f"  - Total issues: {len(issues)} (Critical: {len(critical_issues)}, Medium: {len(medium_issues)}, Low: {len(low_issues)})")
    
    return state
