#!/usr/bin/env python3
"""
Kafka Topic Setup Script
Creates and configures all required topics for the Creative Automation Pipeline.
"""

import os
import sys
from typing import List, Dict, Any
from kafka.admin import KafkaAdminClient, NewTopic, ConfigResource, ConfigResourceType
from kafka.errors import TopicAlreadyExistsError, NoBrokersAvailable
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration - Use external port for host machine access
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")

# Validate broker configuration
if "29092" in KAFKA_BROKER:
    print("⚠️  Warning: Detected internal Docker port (29092) in KAFKA_BROKER")
    print("   This script runs from the host machine and should use localhost:9092")
    print("   Updating to use external port...")
    KAFKA_BROKER = "localhost:9092"

print(f"🔧 Using Kafka broker: {KAFKA_BROKER}")

# Topic definitions with proper configuration
TOPICS = [
    {
        "name": "briefs.ingest.v1",
        "partitions": 3,
        "replication_factor": 1,
        "configs": {
            "retention.ms": "604800000",  # 7 days
            "cleanup.policy": "delete",
            "compression.type": "gzip"
        }
    },
    {
        "name": "pipeline.status.v1",
        "partitions": 3,
        "replication_factor": 1,
        "configs": {
            "retention.ms": "2592000000",  # 30 days
            "cleanup.policy": "delete",
            "compression.type": "gzip"
        }
    },
    {
        "name": "assets.created.v1",
        "partitions": 3,
        "replication_factor": 1,
        "configs": {
            "retention.ms": "2592000000",  # 30 days
            "cleanup.policy": "delete",
            "compression.type": "gzip"
        }
    },
    {
        "name": "alerts.v1",
        "partitions": 2,
        "replication_factor": 1,
        "configs": {
            "retention.ms": "1209600000",  # 14 days
            "cleanup.policy": "delete",
            "compression.type": "gzip"
        }
    },
    {
        "name": "approvals.request.v1",
        "partitions": 3,
        "replication_factor": 1,
        "configs": {
            "retention.ms": "2592000000",
            "cleanup.policy": "delete",
            "compression.type": "gzip"
        }
    },
    {
        "name": "approvals.decision.v1",
        "partitions": 3,
        "replication_factor": 1,
        "configs": {
            "retention.ms": "2592000000",
            "cleanup.policy": "delete",
            "compression.type": "gzip"
        }
    },
    {
        "name": "compliance.v1",
        "partitions": 3,
        "replication_factor": 1,
        "configs": {
            "retention.ms": "2592000000",
            "cleanup.policy": "delete",
            "compression.type": "gzip"
        }
    },
    {
        "name": "performance.metrics.v1",
        "partitions": 3,
        "replication_factor": 1,
        "configs": {
            "retention.ms": "2592000000",
            "cleanup.policy": "delete",
            "compression.type": "gzip"
        }
    },
    {
        "name": "ready_for_publish.v1",
        "partitions": 3,
        "replication_factor": 1,
        "configs": {
            "retention.ms": "2592000000",
            "cleanup.policy": "delete",
            "compression.type": "gzip"
        }
    },
]

def check_kafka_connection() -> bool:
    """Check if Kafka broker is accessible."""
    try:
        print(f"🔍 Testing connection to {KAFKA_BROKER}...")
        admin_client = KafkaAdminClient(
            bootstrap_servers=KAFKA_BROKER,
            client_id='topic-setup-health-check',
            request_timeout_ms=10000,
            connections_max_idle_ms=5000
        )
        admin_client.list_topics()
        admin_client.close()
        print(f"✅ Successfully connected to {KAFKA_BROKER}")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to Kafka broker at {KAFKA_BROKER}: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False

def create_topics() -> bool:
    """Create all required topics."""
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=KAFKA_BROKER,
            client_id='topic-setup-admin',
            request_timeout_ms=10000
        )
        
        # Get existing topics
        existing_topics = admin_client.list_topics()
        print(f"📋 Existing topics: {existing_topics}")
        
        # Create new topics
        topics_to_create = []
        for topic_config in TOPICS:
            if topic_config["name"] not in existing_topics:
                new_topic = NewTopic(
                    name=topic_config["name"],
                    num_partitions=topic_config["partitions"],
                    replication_factor=topic_config["replication_factor"],
                    topic_configs=topic_config["configs"]
                )
                topics_to_create.append(new_topic)
                print(f"➕ Will create topic: {topic_config['name']}")
            else:
                print(f"✅ Topic already exists: {topic_config['name']}")
        
        if not topics_to_create:
            print("🎉 All required topics already exist!")
            return True
        
        # Create topics
        print(f"\n🚀 Creating {len(topics_to_create)} topics...")
        admin_client.create_topics(topics_to_create)
        
        # Verify topics were created
        time.sleep(2)  # Give Kafka time to create topics
        updated_topics = admin_client.list_topics()
        
        for topic_config in TOPICS:
            if topic_config["name"] in updated_topics:
                print(f"✅ Topic created successfully: {topic_config['name']}")
            else:
                print(f"❌ Failed to create topic: {topic_config['name']}")
                return False
        
        admin_client.close()
        return True
        
    except TopicAlreadyExistsError as e:
        print(f"⚠️  Some topics already exist: {e}")
        return True
    except Exception as e:
        print(f"❌ Error creating topics: {e}")
        return False

def configure_topic_settings() -> bool:
    """Configure additional settings for existing topics."""
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=KAFKA_BROKER,
            client_id='topic-setup-config',
            request_timeout_ms=10000
        )
        
        print("\n🔧 Configuring topic settings...")
        
        for topic_config in TOPICS:
            topic_name = topic_config["name"]
            configs = topic_config["configs"]
            
            # Create config resource for the topic
            # Note: Different Kafka client versions have different APIs
            try:
                # Try newer API first
                config_resource = ConfigResource(
                    ConfigResourceType.TOPIC,
                    topic_name,
                    set_config=configs
                )
            except TypeError:
                try:
                    # Try older API
                    config_resource = ConfigResource(
                        ConfigResourceType.TOPIC,
                        topic_name
                    )
                    # Set configs separately if needed
                    print(f"⚠️  Using legacy API for topic {topic_name}")
                except Exception as e:
                    print(f"⚠️  Could not create config resource for {topic_name}: {e}")
                    continue
            
            try:
                admin_client.alter_configs([config_resource])
                print(f"✅ Configured topic: {topic_name}")
            except Exception as e:
                print(f"⚠️  Could not configure topic {topic_name}: {e}")
        
        admin_client.close()
        return True
        
    except Exception as e:
        print(f"❌ Error configuring topics: {e}")
        return False

def main():
    """Main execution function."""
    print("🚀 Kafka Topic Setup for Creative Automation Pipeline")
    print("=" * 60)
    
    # Check connection
    print(f"\n🔍 Checking Kafka connection to {KAFKA_BROKER}...")
    if not check_kafka_connection():
        print("\n💡 Troubleshooting tips:")
        print("   1. Ensure Docker Compose services are running: make run-services")
        print("   2. Wait for Kafka to be ready: make wait-kafka")
        print("   3. Check if the broker URL is correct in your .env file")
        print("   4. Verify Docker containers are healthy: docker compose ps")
        print("   5. Check Docker logs: docker compose logs kafka")
        print(f"\n   Current KAFKA_BROKER setting: {KAFKA_BROKER}")
        print("   Expected: localhost:9092 (external port)")
        sys.exit(1)
    
    print("✅ Kafka connection successful!")
    
    # Create topics
    print("\n📝 Creating topics...")
    if not create_topics():
        print("❌ Failed to create topics")
        sys.exit(1)
    
    # Configure topic settings
    print("\n⚙️  Configuring topic settings...")
    if not configure_topic_settings():
        print("⚠️  Some topic configurations may not have been applied")
    
    print("\n🎉 Kafka topic setup completed successfully!")
    print("\n📊 You can now:")
    print("   - Start the application services: make run-dev")
    print("   - Monitor topics in Redpanda Console: http://localhost:8080")
    print("   - Submit a test brief: make demo")

if __name__ == "__main__":
    import time
    main()
