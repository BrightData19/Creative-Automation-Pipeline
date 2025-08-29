# /apps/pipeline-worker/main.py

import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import NoBrokersAvailable, KafkaError
from kafka.admin import KafkaAdminClient, NewTopic

import storage
import prompt_builder
import variant_generator
try:
    import compliance
except Exception as _e:
    compliance = None  # type: ignore
    print(f"Warning: compliance engine not available ({_e}). Skipping compliance checks.")
from genai_adapter import get_generator
import privacy as privacy_mod
import ingestion
import creative_outputs
import governance
import hashlib
import branding

load_dotenv()

# --- Configuration ---
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
ENABLE_KAFKA = os.getenv("ENABLE_KAFKA", "true").lower() == "true"

TOPIC_BRIEFS_INGEST = "briefs.ingest.v1"
TOPIC_PIPELINE_STATUS = "pipeline.status.v1"
TOPIC_ASSETS_CREATED = "assets.created.v1"
TOPIC_COMPLIANCE = "compliance.v1"
TOPIC_APPROVALS_REQUEST = "approvals.request.v1"
TOPIC_APPROVALS_DECISION = "approvals.decision.v1"
TOPIC_READY_FOR_PUBLISH = "ready_for_publish.v1"

# --- Kafka Topic Management ---
def ensure_topics_exist():
    """Ensure all required Kafka topics exist with proper configuration."""
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=KAFKA_BROKER,
            client_id='pipeline-worker-admin'
        )
        
        # Define topics with proper configuration
        topics = [
            NewTopic(
                name=TOPIC_BRIEFS_INGEST,
                num_partitions=3,
                replication_factor=1
            ),
            NewTopic(
                name=TOPIC_PIPELINE_STATUS,
                num_partitions=3,
                replication_factor=1
            ),
            NewTopic(
                name=TOPIC_ASSETS_CREATED,
                num_partitions=3,
                replication_factor=1
            ),
            NewTopic(
                name=TOPIC_COMPLIANCE,
                num_partitions=3,
                replication_factor=1
            ),
            NewTopic(
                name=TOPIC_APPROVALS_REQUEST,
                num_partitions=3,
                replication_factor=1
            ),
            NewTopic(
                name=TOPIC_APPROVALS_DECISION,
                num_partitions=3,
                replication_factor=1
            ),
            NewTopic(
                name=TOPIC_READY_FOR_PUBLISH,
                num_partitions=3,
                replication_factor=1
            )
        ]
        
        # Create topics if they don't exist
        existing_topics = admin_client.list_topics()
        topics_to_create = [topic for topic in topics if topic.name not in existing_topics]
        
        if topics_to_create:
            admin_client.create_topics(topics_to_create)
            print(f"Created topics: {[t.name for t in topics_to_create]}")
        else:
            print("All required topics already exist")
            
        admin_client.close()
        return True
    except Exception as e:
        print(f"Warning: Could not ensure topics exist: {e}")
        return False

# --- Kafka Health Check ---
def check_kafka_health() -> bool:
    """Check if Kafka broker is accessible."""
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=KAFKA_BROKER,
            client_id='pipeline-worker-health-check'
        )
        admin_client.list_topics()
        admin_client.close()
        return True
    except Exception as e:
        print(f"Kafka health check failed: {e}")
        return False

# --- Kafka Client Initialization ---
def get_kafka_producer() -> KafkaProducer:
    """Get a Kafka producer with retry logic and health checks."""
    if not ENABLE_KAFKA:
        class _NoopFuture:
            def get(self, timeout=None):
                return type("_Meta", (), {"partition": 0, "offset": -1})()

        class _NoopProducer:
            def send(self, topic, message):
                print(f"[NO-KAFKA] Would send to {topic}: {message.get('stage') or message.get('product') or 'event'}")
                return _NoopFuture()
            def close(self):
                pass
        return _NoopProducer()  # type: ignore
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            if not check_kafka_health():
                raise NoBrokersAvailable("Kafka broker not healthy")
                
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                retries=3,
                acks='all',
                compression_type='gzip',
                client_id='pipeline-worker-producer'
            )
            print("Kafka producer connected successfully.")
            return producer
        except (NoBrokersAvailable, KafkaError) as e:
            retry_count += 1
            wait_time = min(5 * retry_count, 30)
            print(f"Kafka broker not available (attempt {retry_count}/{max_retries}). Retrying in {wait_time} seconds...")
            print(f"Error: {e}")
            time.sleep(wait_time)
    
    raise Exception(f"Failed to connect to Kafka after {max_retries} attempts")

def get_kafka_consumer(topics) -> KafkaConsumer:
    """Get a Kafka consumer with retry logic and health checks. Accepts str or list of str."""
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            if not check_kafka_health():
                raise NoBrokersAvailable("Kafka broker not healthy")
                
            if isinstance(topics, str):
                topics = [topics]
            consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=KAFKA_BROKER,
                auto_offset_reset='earliest',
                group_id='pipeline-worker-group',
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
                client_id=f'pipeline-worker-consumer-{topics[0]}'
            )
            print(f"Kafka consumer connected successfully for topics: {topics}")
            return consumer
        except (NoBrokersAvailable, KafkaError) as e:
            retry_count += 1
            wait_time = min(5 * retry_count, 30)
            print(f"Kafka broker not available for consumer (attempt {retry_count}/{max_retries}). Retrying in {wait_time} seconds...")
            print(f"Error: {e}")
            time.sleep(wait_time)
    
    raise Exception(f"Failed to connect consumer to Kafka after {max_retries} attempts")

# Initialize producer with retry logic
producer: Optional[KafkaProducer] = None
privacy_checker = privacy_mod.PrivacyChecker()

def get_producer() -> KafkaProducer:
    """Get or create the Kafka producer."""
    global producer
    if producer is None:
        producer = get_kafka_producer()
    return producer

# --- Helper Functions ---
def send_status(campaign: str, product: str, stage: str, detail: str, artifacts: Optional[list] = None, error: Optional[str] = None):
    """Send pipeline status update to Kafka."""
    if artifacts is None:
        artifacts = []
    
    try:
        # Redact PII in details if configured
        redact = os.getenv("REDACT_PII", "true").lower() == "true"
        redacted_detail = privacy_checker.mask_text(detail) if (detail and redact) else detail
        message = {
            "event_id": str(uuid.uuid4()),
            "ts": datetime.now(timezone.utc).isoformat(),
            "campaign_name": campaign,
            "product": product,
            "stage": stage,
            "detail": redacted_detail,
            "artifacts": artifacts,
            "error": error,
            "redacted": redact,
        }
        
        p = get_producer()
        future = p.send(TOPIC_PIPELINE_STATUS, message)
        # Wait for the message to be sent
        record_metadata = future.get(timeout=10)
        print(f"Sent status: {stage} for {product} (partition: {record_metadata.partition}, offset: {record_metadata.offset})")
        
    except Exception as e:
        print(f"Failed to send status message: {e}")
        # Reset producer on error
        global producer
        producer = None

def send_assets_created(campaign: str, product: str, variants: list):
    """Send assets created event to Kafka."""
    try:
        message = {
            "event_id": str(uuid.uuid4()),
            "ts": datetime.now(timezone.utc).isoformat(),
            "campaign_name": campaign,
            "product": product,
            "variants": variants
        }
        
        p = get_producer()
        future = p.send(TOPIC_ASSETS_CREATED, message)
        # Wait for the message to be sent
        record_metadata = future.get(timeout=10)
        print(f"Sent assets created event for {product} (partition: {record_metadata.partition}, offset: {record_metadata.offset})")
        
    except Exception as e:
        print(f"Failed to send assets created message: {e}")
        # Reset producer on error
        global producer
        producer = None

def send_compliance_report(campaign: str, product: str, compliance_report: dict):
    """Send compliance report to Kafka."""
    try:
        message = {
            "event_id": str(uuid.uuid4()),
            "ts": datetime.now(timezone.utc).isoformat(),
            "campaign_name": campaign,
            "product": product,
            "compliance_report": compliance_report
        }
        
        p = get_producer()
        future = p.send(TOPIC_COMPLIANCE, message)
        # Wait for the message to be sent
        record_metadata = future.get(timeout=10)
        print(f"Sent compliance report for {product} (partition: {record_metadata.partition}, offset: {record_metadata.offset})")
        
    except Exception as e:
        print(f"Failed to send compliance report: {e}")
        # Reset producer on error
        global producer
        producer = None

def send_approval_request(campaign: str, product: str, variants: list, compliance_report: dict):
    """Send approval request event with artifacts and compliance summary."""
    try:
        message = {
            "event_id": str(uuid.uuid4()),
            "ts": datetime.now(timezone.utc).isoformat(),
            "campaign_name": campaign,
            "product": product,
            "variants": variants,
            "compliance_report": compliance_report,
            "status": "ready_for_review"
        }
        p = get_producer()
        future = p.send(TOPIC_APPROVALS_REQUEST, message)
        record_metadata = future.get(timeout=10)
        print(f"Sent approval request for {product} (partition: {record_metadata.partition}, offset: {record_metadata.offset})")
    except Exception as e:
        print(f"Failed to send approval request: {e}")
        global producer
        producer = None

def send_ready_for_publish(campaign: str, product: str, artifacts: list, manifest_path: Optional[str] = None):
    """Emit ready_for_publish event with finalized artifact paths."""
    try:
        message = {
            "event_id": str(uuid.uuid4()),
            "ts": datetime.now(timezone.utc).isoformat(),
            "campaign_name": campaign,
            "product": product,
            "artifacts": artifacts,
            "status": "ready_for_publish",
            "manifest": manifest_path,
        }
        p = get_producer()
        future = p.send(TOPIC_READY_FOR_PUBLISH, message)
        record_metadata = future.get(timeout=10)
        print(f"Sent ready_for_publish for {product} (partition: {record_metadata.partition}, offset: {record_metadata.offset})")
    except Exception as e:
        print(f"Failed to send ready_for_publish: {e}")
        global producer
        producer = None

def persist_approval_decision(campaign: str, product: str, decision_event: dict):
    approvals_dir = f"{storage.get_root()}/outputs/{campaign}/approvals"
    storage.ensure_folder(approvals_dir)
    path = f"{approvals_dir}/{product.replace(' ', '_')}.json"
    storage.write_json(path, decision_event)

def finalize_product_assets(campaign: str, product: str) -> tuple[list, str]:
    """Copy generated assets into finalized/ path.
    Returns list of finalized artifact paths (dropbox: prefixed).
    """
    artifacts = []
    manifest_items = []
    base = f"{storage.get_root()}/outputs/{campaign}"
    product_slug = product.replace(' ', '_')
    product_dir = f"{base}/{product_slug}"
    ratios = storage.list_folder(product_dir)
    for ratio in ratios or []:
        src_ratio_dir = f"{product_dir}/{ratio}"
        files = storage.list_folder(src_ratio_dir)
        dest_ratio_dir = f"{base}/finalized/{product_slug}/{ratio}"
        storage.ensure_folder(dest_ratio_dir)
        for name in files or []:
            src_path = f"{src_ratio_dir}/{name}"
            dest_path = f"{dest_ratio_dir}/{name}"
            try:
                data = storage.download_bytes(src_path)
                storage.upload_bytes(dest_path, data)
                if name.lower().endswith('.jpg') or name.lower().endswith('.jpeg'):
                    artifacts.append(f"dropbox:{dest_path}")
                    # Try to attach lineage metadata
                    lineage_path = f"{src_ratio_dir}/{os.path.splitext(name)[0]}.json"
                    lineage = None
                    try:
                        lineage = storage.read_json(lineage_path)
                    except Exception:
                        pass
                    manifest_items.append({
                        "ratio": ratio.replace('x', ':'),
                        "file": f"dropbox:{dest_path}",
                        "lineage": lineage,
                    })
            except Exception as e:
                print(f"Finalize copy warning for {src_path}: {e}")
    # Write manifest
    manifest_dir = f"{base}/finalized/{product_slug}"
    storage.ensure_folder(manifest_dir)
    manifest = {
        "campaign": campaign,
        "product": product,
        "artifacts": manifest_items,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path = f"{manifest_dir}/manifest.json"
    storage.write_json(manifest_path, manifest)
    return artifacts, f"dropbox:{manifest_path}"

# --- Enhanced Processing Logic ---
def process_brief(brief: dict):
    """Process a creative brief and generate assets with compliance checking and localization."""
    campaign_name = brief['campaign_name']
    target_market = brief.get('target_market', 'US')
    output_folder = f"{storage.get_root()}/outputs/{campaign_name}"
    storage.ensure_folder(output_folder)

    # Initialize enhanced components
    genai = get_generator(os.getenv("GENERATOR_PROVIDER", "gemini"))
    prompt_builder_instance = prompt_builder.PromptBuilder()
    compliance_engine = compliance.ComplianceEngine() if compliance else None
    prompt_guidance = brief.get('prompt_guidance', {}) or {}
    retry_attempt = brief.get('retry_attempt')

    # Generate localization report
    try:
        localization_report = prompt_builder_instance.build_localization_report(
            brief['campaign_message'], 
            [target_market]
        )
        print(f"Localization report for {target_market}: {localization_report['localized_versions'].get(target_market, {})}")
    except Exception as e:
        print(f"Warning: Could not generate localization report: {e}")
    
    # Ingest inbox assets (images, videos, docs, etc.) for reuse and traceability
    inbox_folder = brief.get('inbox_folder')
    inbox_assets = []
    if inbox_folder:
        inbox_folder = inbox_folder.replace("dropbox:", "")
        try:
            inbox_assets = ingestion.index_inbox(inbox_folder)
            copied = ingestion.copy_all_assets_to_outputs(campaign_name, inbox_folder, inbox_assets)
            send_status(campaign_name, "__campaign__", "ingestion_assets_indexed", f"Indexed {len(inbox_assets)} assets; copied {len(copied)} to outputs.")
        except Exception as e:
            print(f"Asset ingestion warning: {e}")

    force_generate_new = bool(brief.get('force_generate_new', False))

    for product in brief['products']:
        product_name = product['name']
        send_status(campaign_name, product_name, "ingest_started", "Processing product with enhanced features.")

        try:
            base_image = None
            asset_source = None
            if (not force_generate_new) and product.get('image'):
                # Download provided image
                image_path = product['image'].replace("dropbox:", "")
                base_image = storage.download_pil_image(image_path)
                send_status(campaign_name, product_name, "asset_downloaded", f"Downloaded {image_path}")
                asset_source = "provided"
                # Optionally enhance/edit provided image using GenAI image edit
                try:
                    if os.getenv("EDIT_WITH_GENAI", "true").lower() == "true":
                        editor = get_generator("gemini")
                        base_image = editor.generate_from_image(
                            base_image,
                            f"Enhance product photo for {product_name} keeping subject centered and crop-safe.",
                            1024,
                            1024,
                        )
                        send_status(campaign_name, product_name, "asset_enhanced", "Enhanced provided image via GenAI.")
                except Exception as e:
                    print(f"Image enhancement skipped: {e}")
            else:
                # Try to reuse image from inbox assets first
                chosen = None if force_generate_new else ingestion.pick_product_image_asset(product_name, inbox_assets)
                if chosen and (not force_generate_new):
                    base_image = ingestion.load_image_from_asset(chosen)
                    send_status(campaign_name, product_name, "asset_reused", f"Reused inbox asset {chosen.name}")
                    asset_source = "reused_inbox"
                    try:
                        if os.getenv("EDIT_WITH_GENAI", "true").lower() == "true":
                            editor = get_generator("gemini")
                            base_image = editor.generate_from_image(
                                base_image,
                                f"Enhance product photo for {product_name} keeping subject centered and crop-safe.",
                                1024,
                                1024,
                            )
                            send_status(campaign_name, product_name, "asset_enhanced", "Enhanced reused image via GenAI.")
                    except Exception as e:
                        print(f"Image enhancement skipped: {e}")
                # If not found or force flag set, generate image using enhanced prompt builder
                if base_image is None:
                    prompt = prompt_builder_instance.build_image_prompt(
                        product_name, 
                        brief['campaign_message'], 
                        brief['target_audience'],
                        target_market
                    )
                    # Apply agent-provided prompt guidance if available
                    guidance_lines = []
                    if product_name in prompt_guidance:
                        guidance_lines.extend(prompt_guidance.get(product_name, []))
                    guidance_lines.extend(prompt_guidance.get('__campaign__', []))
                    if guidance_lines:
                        prompt += " Variation directives: " + "; ".join(guidance_lines) + "."
                    if retry_attempt:
                        prompt += f" Ensure this attempt differs in composition, lighting, and scene from prior outputs (attempt {retry_attempt})."
                    print(f"Generated localized prompt for {product_name}: {prompt[:100]}...")
                    # For generation, we use a standard large size (single call, then resize)
                    base_image = genai.generate(prompt, 1024, 1024)
                    send_status(campaign_name, product_name, "asset_generated", "Generated base image using enhanced prompt.")
                    asset_source = "genai"

            # Optional logo overlay prior to compliance
            try:
                logo_path = brief.get('logo_path')
                if logo_path:
                    logo_bytes_path = logo_path.replace("dropbox:", "")
                    logo_img = storage.download_pil_image(logo_bytes_path)
                    # Use top-right safe area
                    base_image = branding.overlay_logo(base_image, logo_img, position=os.getenv("LOGO_POSITION", "top_right"))
                    send_status(campaign_name, product_name, "logo_overlay", f"Applied logo overlay from {logo_bytes_path}")
            except Exception as e:
                print(f"Logo overlay warning: {e}")

            # Run compliance checks on the base image
            compliance_report = {"overall_compliant": True, "overall_score": 1.0}
            if compliance_engine:
                send_status(campaign_name, product_name, "compliance_check", "Running comprehensive compliance checks.")
                # Check both image and campaign message
                campaign_message = brief['campaign_message']
                compliance_report = compliance_engine.run_comprehensive_check(base_image, campaign_message)
                # Send compliance report
                send_compliance_report(campaign_name, product_name, compliance_report)
                # Log compliance results
                if compliance_report.get("overall_compliant", False):
                    send_status(campaign_name, product_name, "compliance_passed", 
                              f"Compliance check passed with score {compliance_report.get('overall_score', 0):.2f}")
                else:
                    issues = compliance_report.get("all_issues", [])
                    send_status(campaign_name, product_name, "compliance_issues", 
                              f"Compliance issues detected: {len(issues)} issues found")
                    print(f"Compliance issues for {product_name}: {issues}")

            # Generate variants with enhanced aspect ratios
            send_status(campaign_name, product_name, "variant_generation", "Generating variants for multiple aspect ratios.")
            variants = variant_generator.generate_variants(base_image)
            
            # Upload variants to Dropbox with enhanced organization
            saved_variants = []
            for ratio, img in variants.items():
                # Create organized path: /outputs/<campaign>/<product>/<ratio>/<market>.jpg
                product_dir = f"{output_folder}/{product_name.replace(' ', '_')}/{ratio.replace(':', 'x')}"
                storage.ensure_folder(product_dir)
                dbx_path = f"{product_dir}/{target_market}.jpg"
                
                # Save variant
                storage.upload_pil_image(dbx_path, img)
                
                # Add metadata to variant info
                lineage = {
                    "campaign": campaign_name,
                    "product": product_name,
                    "ratio": ratio,
                    "market": target_market,
                    "source": asset_source,
                    "generator_provider": os.getenv("GENERATOR_PROVIDER", "gemini"),
                    "prompt_sha256": hashlib.sha256(prompt.encode('utf-8')).hexdigest() if 'prompt' in locals() else None,
                    "compliance_score": compliance_report.get("overall_score", 0.0),
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
                storage.write_json(f"{product_dir}/{target_market}.json", lineage)
                variant_info = {
                    "ratio": ratio,
                    "path": f"dropbox:{dbx_path}",
                    "target_market": target_market,
                    "compliance_score": compliance_report.get("overall_score", 0.0),
                    "localized": True
                }
                saved_variants.append(variant_info)
            
            send_status(campaign_name, product_name, "variants_saved", 
                      f"All variants saved to Dropbox with localization for {target_market}.", 
                      artifacts=[v['path'] for v in saved_variants])
            
            # Send enhanced assets created event
            send_assets_created(campaign_name, product_name, saved_variants)
            # Approval request and gating stage
            send_status(campaign_name, product_name, "ready_for_review", "Assets awaiting approval.")
            send_approval_request(campaign_name, product_name, saved_variants, compliance_report)
            
            # Additional creatives (carousel, animated gif, localized messages)
            try:
                creative_outputs.generate_carousel_from_image(campaign_name, product_name, base_image)
                creative_outputs.generate_animated_gif_from_image(campaign_name, product_name, target_market, base_image)
                msgs = {
                    "market": target_market,
                    "product": product_name,
                    "headline": f"{product_name}: {brief['campaign_message']}",
                    "cta": "Shop Now",
                    "link": "https://example.com/product",
                }
                creative_outputs.save_localized_messages(campaign_name, product_name, target_market, msgs)
                send_status(campaign_name, product_name, "other_creatives", "Generated carousels, animated GIF, and localized messages.")
            except Exception as e:
                print(f"Other creatives generation warning for {product_name}: {e}")

            # Log success with enhanced details
            print(f"Successfully processed {product_name} for {target_market} market")
            print(f"Generated {len(saved_variants)} variants with compliance score: {compliance_report.get('overall_score', 0):.2f}")

        except Exception as e:
            error_msg = f"Failed to process product {product_name}: {str(e)}"
            send_status(campaign_name, product_name, "error", error_msg, error=error_msg)
            print(error_msg)

    # Update campaign-level catalog manifest
    try:
        catalog = {
            "campaign": campaign_name,
            "market": target_market,
            "products": [p["name"] for p in brief["products"]],
        }
        creative_outputs.update_catalog(campaign_name, catalog)
    except Exception as e:
        print(f"Catalog update warning: {e}")

    # Apply governance retention policy if configured
    try:
        retention_days = int(os.getenv("RETENTION_DAYS", "0"))
        if retention_days > 0:
            governance.apply_retention_policy(retention_days)
    except Exception as e:
        print(f"Governance retention warning: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    print("Enhanced Pipeline worker starting...")
    print("Features: GenAI integration, compliance checking, localized messaging")
    
    # Ensure Kafka topics exist
    print("Ensuring Kafka topics exist...")
    ensure_topics_exist()
    
    # Initialize Kafka producer
    if ENABLE_KAFKA:
        print("Initializing Kafka producer...")
        try:
            get_producer()
            print("Kafka producer initialized successfully")
        except Exception as e:
            print(f"Failed to initialize Kafka producer: {e}")
            exit(1)
    
    # Start consuming briefs and approval decisions
    print("Starting to consume briefs and approval decisions...")
    consumer = get_kafka_consumer([TOPIC_BRIEFS_INGEST, TOPIC_APPROVALS_DECISION])
    
    try:
        for message in consumer:
            try:
                if message.topic == TOPIC_BRIEFS_INGEST:
                    brief = message.value
                    print(f"\nProcessing enhanced brief for campaign: {brief['campaign_name']}")
                    print(f"Target market: {brief.get('target_market', 'US')}")
                    print(f"Products: {len(brief['products'])}")
                    process_brief(brief)
                elif message.topic == TOPIC_APPROVALS_DECISION:
                    decision_evt = message.value
                    campaign = decision_evt.get('campaign_name', 'unknown')
                    product = decision_evt.get('product', 'unknown')
                    decision = (decision_evt.get('decision') or '').lower()
                    print(f"\nReceived approval decision for {campaign} / {product}: {decision}")
                    # Persist the decision
                    persist_approval_decision(campaign, product, decision_evt)
                    if decision == 'approved':
                        # Promote to finalized and emit ready_for_publish
                        arts, manifest = finalize_product_assets(campaign, product)
                        send_ready_for_publish(campaign, product, arts, manifest)
                    else:
                        send_status(campaign, product, 'rejected', 'Assets rejected; awaiting changes')
                
            except Exception as e:
                print(f"Error processing message: {e}")
                # Continue processing other messages
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    finally:
        consumer.close()
        if producer:
            producer.close()
        print("Enhanced Pipeline worker shutdown complete.")
