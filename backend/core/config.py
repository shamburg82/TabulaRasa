"""
Shared application configuration.

All settings live here so any stage can read them by importing from
backend.core.config. Env-driven; Posit Connect content settings panel
sets these in deployment.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    # ------------------------------------------------------------------ #
    # MongoDB
    # ------------------------------------------------------------------ #
    mongo_uri: str = field(default_factory=lambda: _env("MONGO_URI", "mongodb://localhost:27017"))
    mongo_db: str = field(default_factory=lambda: _env("MONGO_DB", "tlf_automation"))

    coll_documents: str = "documents"
    coll_chunks: str = "doc_chunks"
    coll_extractions: str = "sap_extractions"      # Stage 1
    coll_toc_syntheses: str = "toc_syntheses"      # Stage 2
    coll_audit: str = "audit_log"

    # ------------------------------------------------------------------ #
    # AWS Bedrock
    # ------------------------------------------------------------------ #
    aws_region: str = field(default_factory=lambda: _env("AWS_REGION", "us-east-1"))
    model_extraction: str = field(
        default_factory=lambda: _env("MODEL_EXTRACTION", "anthropic.claude-opus-4-8")
    )
    model_fallback: str = field(default_factory=lambda: _env("MODEL_FALLBACK", ""))
    model_light: str = field(
        default_factory=lambda: _env("MODEL_LIGHT", "global.anthropic.claude-sonnet-4-6-v1")
    )
    llm_temperature: float = 0.0
    llm_max_tokens: int = 16000
    llm_max_retries: int = 5
    llm_retry_base_seconds: float = 2.0
    llm_read_timeout: int = field(default_factory=lambda: int(_env("LLM_READ_TIMEOUT", "900")))

    # ------------------------------------------------------------------ #
    # Stage 1 extraction batching
    # ------------------------------------------------------------------ #
    pass_char_budget: int = field(default_factory=lambda: int(_env("PASS_CHAR_BUDGET", "150000")))

    # ------------------------------------------------------------------ #
    # Stage 2 shell library
    # ------------------------------------------------------------------ #
    # Local mount on Posit Connect containing the proprietary library.
    # Layout expected: <root>/<version_tag>/<archetype-files>.docx or .pdf
    # plus an optional <root>/<version_tag>/conventions.md
    shell_library_root: str = field(
        default_factory=lambda: _env("SHELL_LIBRARY_ROOT", "")
    )
    shell_library_default_version: str = field(
        default_factory=lambda: _env("SHELL_LIBRARY_DEFAULT_VERSION", "")
    )

    # ------------------------------------------------------------------ #
    # CORS
    # ------------------------------------------------------------------ #
    cors_allow_origins: list[str] = field(
        default_factory=lambda: [
            o.strip()
            for o in _env(
                "CORS_ALLOW_ORIGINS",
                "http://localhost:5173,http://localhost:3000",
            ).split(",")
            if o.strip()
        ]
    )

    debug: bool = field(default_factory=lambda: _env_bool("DEBUG", False))


settings = Settings()
