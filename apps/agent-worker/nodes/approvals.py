import json
import os
from urllib import request
from typing import Dict, Any


def post_slack_approval(campaign: str, product: str, variants: list):
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        print("[approvals] SLACK_WEBHOOK_URL not set; skipping Slack notification")
        return

    text = f"Approval needed for {campaign} – {product}"
    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text},
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Approve"},
                    "style": "primary",
                    "url": f"http://localhost:3000/api/approvals?campaign_name={campaign}&product={product}&decision=approved"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Reject"},
                    "style": "danger",
                    "url": f"http://localhost:3000/api/approvals?campaign_name={campaign}&product={product}&decision=rejected"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Open Dashboard"},
                    "url": "http://localhost:3000/dashboard"
                }
            ]
        }
    ]
    payload = json.dumps({"text": text, "blocks": blocks}).encode("utf-8")
    req = request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=5) as resp:
            print(f"[approvals] Slack response: {resp.status}")
    except Exception as e:
        print(f"[approvals] Slack webhook error: {e}")

