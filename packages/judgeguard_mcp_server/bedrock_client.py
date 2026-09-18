"""
AWS Bedrock Client Integration for JudgeGuard Alexa+ Governance
Provides secondary semantic safety evaluation, reasoning traces, and policy verification
using AWS Bedrock (Claude 3.5 Sonnet / Amazon Titan Text Express).
Compliant with Amazon Developer Hackathon 2026 AWS Builder Mini-Challenge.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("JudgeGuard.AWSBedrock")

DEFAULT_BEDROCK_MODEL_ID = os.getenv("AWS_BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

class AWSBedrockSafetyClient:
    """
    Evaluates high-stakes agent actions using AWS Bedrock runtime.
    Supports both Anthropic Claude and Amazon Titan model payload formats.
    Acts as Layer 2 semantic reasoner alongside JudgeGuard core.
    """
    def __init__(self, model_id: str = DEFAULT_BEDROCK_MODEL_ID, region: str = AWS_REGION):
        self.model_id = model_id
        self.region = region
        self._client = None
        self._has_boto3 = False
        
        try:
            import boto3
            self._has_boto3 = True
            if os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_PROFILE"):
                self._client = boto3.client("bedrock-runtime", region_name=self.region)
                logger.info(f"AWS Bedrock client initialized in {self.region} (Model: {self.model_id}).")
            else:
                logger.info("AWS Bedrock: No credentials detected. Operating in reproducible simulated Bedrock evaluation mode.")
        except ImportError:
            logger.info("boto3 not installed. Operating in reproducible deterministic Bedrock fallback mode.")

    @property
    def is_live(self) -> bool:
        return self._client is not None

    def _format_request_body(self, prompt: str, model_id: str) -> str:
        """
        Formats model-specific payload for Bedrock invoke_model API.
        Distinguishes Anthropic Claude vs Amazon Titan Text payloads.
        """
        if "anthropic.claude" in model_id.lower():
            return json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0
            })
        elif "amazon.titan" in model_id.lower():
            return json.dumps({
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 512,
                    "temperature": 0.0,
                    "topP": 0.9,
                    "stopSequences": []
                }
            })
        else:
            # Generic fallback payload
            return json.dumps({
                "inputText": prompt,
                "max_tokens": 512,
                "temperature": 0.0
            })

    def _extract_response_text(self, response_body: Dict[str, Any], model_id: str) -> str:
        """
        Extracts generated text based on target Bedrock model response schema.
        """
        if "anthropic.claude" in model_id.lower():
            content = response_body.get("content", [])
            if content and isinstance(content, list):
                return content[0].get("text", "")
            return ""
        elif "amazon.titan" in model_id.lower():
            results = response_body.get("results", [])
            if results and isinstance(results, list):
                return results[0].get("outputText", "")
            return response_body.get("outputText", "")
        else:
            return str(response_body)

    def evaluate_action_safety(self, action: str, context: Optional[str] = None, override_model: Optional[str] = None) -> Dict[str, Any]:
        """
        Sends an action evaluation prompt to AWS Bedrock to assess safety, financial risk, and intent integrity.
        """
        target_model = override_model or self.model_id
        prompt = (
            f"You are the AWS Bedrock Safety Evaluator for Alexa+ autonomous actions.\n"
            f"Evaluate the following action for safety, unauthorized transactions, or security violations:\n"
            f"Action: {action}\n"
            f"Context: {context or 'None provided'}\n\n"
            f"Respond ONLY with valid JSON with keys: verdict ('PASSED'|'BLOCKED'), risk_score (0.0-1.0), reasoning (string), model_used (string)."
        )

        if self.is_live:
            try:
                body_payload = self._format_request_body(prompt, target_model)
                response = self._client.invoke_model(
                    modelId=target_model,
                    body=body_payload,
                    contentType="application/json",
                    accept="application/json"
                )
                response_body = json.loads(response["body"].read().decode("utf-8"))
                raw_text = self._extract_response_text(response_body, target_model)
                parsed = json.loads(raw_text.strip())
                parsed["live_backend"] = True
                parsed["mode"] = "live_aws_bedrock"
                parsed["aws_region"] = self.region
                parsed["model_used"] = target_model
                return parsed
            except Exception as e:
                logger.warning(f"AWS Bedrock live invocation failed ({target_model}): {e}. Falling back to reproducible local evaluation.")

        # Deterministic offline evaluation fallback
        action_lower = action.lower()
        is_dangerous = any(p in action_lower for p in [
            "rm -rf", "delete database", "drop table", "unlock front door", 
            "charge $", "send money", "bypass", "wire funds"
        ])

        verdict = "BLOCKED" if is_dangerous else "PASSED"
        risk_score = 0.95 if is_dangerous else 0.05
        reasoning = (
            "Detected prohibited high-consequence action (physical security compromise or unverified financial transfer)."
            if is_dangerous else "Action falls within acceptable autonomous parameters."
        )

        return {
            "verdict": verdict,
            "approved": verdict == "PASSED",
            "risk_score": risk_score,
            "reasoning": reasoning,
            "model_used": f"{target_model} (Deterministic Engine)",
            "aws_region": self.region,
            "live_backend": self.is_live,
            "mode": "live_aws_bedrock" if self.is_live else "simulated_bedrock_fallback"
        }
