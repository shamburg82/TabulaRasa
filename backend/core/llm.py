"""
Bedrock LLM access via LlamaIndex BedrockConverse.

Credentials are never specified here: BedrockConverse resolves through the
default AWS credential chain (instance role on Posit Connect, AWS_PROFILE
or env keys locally). The model identifier may be either a plain Bedrock
model id or an inference profile ARN
(e.g. arn:aws:bedrock:us-west-2:<acct>:inference-profile/us.anthropic....),
which newer Claude models require for on-demand invocation.

configure_bedrock_llm() mirrors the connect-and-test pattern: build the
client, run a one-token test call, fall back to MODEL_FALLBACK if the
primary fails, return None if nothing works.

BedrockClient keeps the same public interface as before (complete_json),
so the extraction agent and pipeline are unchanged. It still owns:
  - strict JSON extraction with one self-repair retry
  - audit metadata per call: model id, prompt/response SHA-256, token
    usage, latency
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

from llama_index.core.llms import ChatMessage
from llama_index.llms.bedrock_converse import BedrockConverse

from .config import settings

logger = logging.getLogger(__name__)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


@dataclass
class LlmResult:
    data: Any                       # parsed JSON payload
    raw_text: str
    audit: dict[str, Any]           # model_id, hashes, usage, latency_ms


class BedrockClient:
    def __init__(self, model_id: Optional[str] = None, region: Optional[str] = None):
        self.model_id = model_id or settings.model_extraction
        self.region = region or settings.aws_region
        self._llms: dict[str, BedrockConverse] = {}

    def _llm(self, model_id: str, max_tokens: Optional[int] = None) -> BedrockConverse:
        key = f"{model_id}:{max_tokens or settings.llm_max_tokens}"
        if key not in self._llms:
            self._llms[key] = BedrockConverse(
                model=model_id,
                region_name=self.region,
                temperature=settings.llm_temperature,
                max_tokens=max_tokens or settings.llm_max_tokens,
                max_retries=settings.llm_max_retries,
                timeout=settings.llm_read_timeout,
            )
        return self._llms[key]

    # ------------------------------------------------------------------ #

    def healthcheck(self) -> None:
        """One-token test call; raises if the model is unreachable."""
        llm = self._llm(self.model_id, max_tokens=16)
        response = llm.chat([ChatMessage(role="user", content="Reply with the word OK.")])
        if not (response.message.content or "").strip():
            raise RuntimeError(f"Empty response from {self.model_id}")

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        model_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        action: str = "llm_call",
    ) -> LlmResult:
        """Run one chat call and return parsed JSON with audit metadata."""
        model = model_id or self.model_id
        raw, usage, latency_ms = self._chat(system, user, model, max_tokens)
        try:
            data = _parse_json(raw)
        except ValueError:
            logger.warning("JSON parse failed for %s; attempting one self-repair", action)
            repair_user = (
                "The previous response was not valid JSON. Reproduce the SAME content "
                "as a single valid JSON object only, with no commentary and no markdown "
                "fences.\n\nPrevious response:\n" + raw[:50000]
            )
            raw2, usage2, latency2 = self._chat(system, repair_user, model, max_tokens)
            data = _parse_json(raw2)
            raw = raw2
            usage = {k: usage.get(k, 0) + usage2.get(k, 0)
                     for k in ("inputTokens", "outputTokens")}
            latency_ms += latency2

        audit = {
            "action": action,
            "model_id": model,
            "temperature": settings.llm_temperature,
            "prompt_sha256": _sha(system + "\n" + user),
            "response_sha256": _sha(raw),
            "input_tokens": usage.get("inputTokens"),
            "output_tokens": usage.get("outputTokens"),
            "latency_ms": latency_ms,
        }
        return LlmResult(data=data, raw_text=raw, audit=audit)

    # ------------------------------------------------------------------ #

    def _chat(self, system: str, user: str, model_id: str,
              max_tokens: Optional[int]) -> tuple[str, dict, int]:
        llm = self._llm(model_id, max_tokens)
        start = time.monotonic()
        response = llm.chat([
            ChatMessage(role="system", content=system),
            ChatMessage(role="user", content=user),
        ])
        latency_ms = int((time.monotonic() - start) * 1000)
        text = response.message.content or ""
        usage = (response.raw or {}).get("usage", {}) if isinstance(response.raw, dict) else {}
        return text, usage, latency_ms


def configure_bedrock_llm() -> Optional[BedrockClient]:
    """
    Build and verify the Bedrock client at startup.

    Tries MODEL_EXTRACTION first (model id or inference profile ARN), then
    MODEL_FALLBACK if set. Returns a working BedrockClient or None.
    """
    candidates = [m for m in (settings.model_extraction, settings.model_fallback) if m]
    for model in candidates:
        logger.info("Configuring Bedrock LLM: model=%s region=%s temperature=%s",
                    model, settings.aws_region, settings.llm_temperature)
        client = BedrockClient(model_id=model)
        try:
            client.healthcheck()
            logger.info("Bedrock LLM test successful: %s", model)
            return client
        except Exception as exc:  # noqa: BLE001 - report and try fallback
            logger.error("Bedrock LLM test failed for %s: %s", model, exc)
    logger.error("No working Bedrock model found (tried: %s)", candidates)
    return None


def _parse_json(text: str) -> Any:
    cleaned = _FENCE.sub("", text.strip()).strip()
    if not cleaned.startswith(("{", "[")):
        start = min(
            (i for i in (cleaned.find("{"), cleaned.find("[")) if i >= 0),
            default=-1,
        )
        if start < 0:
            raise ValueError("No JSON found in model output")
        cleaned = cleaned[start:]
    decoder = json.JSONDecoder()
    obj, _ = decoder.raw_decode(cleaned)
    return obj


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
