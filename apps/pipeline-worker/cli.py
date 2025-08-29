"""
CLI entrypoint for running the creative pipeline locally without Kafka/Dropbox.

Example:
  uv run python cli.py --brief ../../data/samples/brief_sample.json \
    --storage-backend local --local-root ./local_storage
"""
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

# Ensure env is loaded
load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Run creative pipeline locally")
    parser.add_argument("--brief", required=True, help="Path to brief JSON file")
    parser.add_argument("--storage-backend", default=os.getenv("STORAGE_BACKEND", "local"), choices=["local", "dropbox"], help="Storage backend")
    parser.add_argument("--local-root", default=os.getenv("LOCAL_ROOT", "local_storage"), help="Local root folder for assets/outputs when using local backend")
    parser.add_argument("--generator", default=os.getenv("GENERATOR_PROVIDER", "intelligent"), choices=["intelligent", "gemini", "firefly", "openai", "stub"], help="GenAI provider selection")
    args = parser.parse_args()

    # Configure environment for offline run
    os.environ.setdefault("ENABLE_KAFKA", "false")
    os.environ["STORAGE_BACKEND"] = args.storage_backend
    if args.storage_backend == "local":
        os.environ["LOCAL_ROOT"] = args.local_root

    # Lazy import after env setup
    from main import process_brief

    brief_path = Path(args.brief)
    brief = json.loads(brief_path.read_text(encoding="utf-8"))

    print(f"Running pipeline for campaign: {brief.get('campaign_name')}")
    print(f"Storage backend: {args.storage_backend} (root={os.getenv('LOCAL_ROOT', '')})")

    process_brief(brief)

    print("Done. Check outputs under:")
    if args.storage_backend == "local":
        print(f"  {Path(os.getenv('LOCAL_ROOT', 'local_storage')) / 'outputs' / brief.get('campaign_name', '')}")
    else:
        print(f"  Dropbox: {os.getenv('DROPBOX_ROOT', '/Apps/CreativeAutomation')}/outputs/{brief.get('campaign_name', '')}")


if __name__ == "__main__":
    main()

