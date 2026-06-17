"""Application settings loaded from environment and .env."""

from __future__ import annotations

from functools import lru_cache
from typing import ClassVar, Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

VALID_ANTHROPIC_MODELS = {
    "claude-opus-4-8",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
    "claude-fable-5",
}

VALID_OPENAI_MODELS = {
    "gpt-5.5",
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
}

VALID_EMBEDDING_MODELS = {"text-embedding-3-large"}


def validate_model_string(model: str) -> str:
    if model.startswith(("claude-3-", "claude-3-5-", "gpt-4o")):
        raise ValueError(f"Deprecated model string is not allowed: {model}")
    valid = VALID_ANTHROPIC_MODELS | VALID_OPENAI_MODELS | VALID_EMBEDDING_MODELS
    if model not in valid:
        raise ValueError(f"Unknown model string: {model}")
    return model


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    VALID_ANTHROPIC_MODELS: ClassVar[set[str]] = VALID_ANTHROPIC_MODELS
    VALID_OPENAI_MODELS: ClassVar[set[str]] = VALID_OPENAI_MODELS

    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_DEFAULT: str = "claude-sonnet-4-6"
    LLM_FAST: str = "claude-haiku-4-5-20251001"
    LLM_POWERFUL: str = "claude-opus-4-8"
    LLM_EMBEDDINGS: str = "text-embedding-3-large"

    OPENAI_LLM_DEFAULT: str = "gpt-5"
    OPENAI_LLM_FAST: str = "gpt-5-mini"
    OPENAI_LLM_FRONTIER: str = "gpt-5.5"

    DATABASE_URL: str = "postgresql://localhost:5432/ai_native"
    REDIS_URL: str = "redis://localhost:6379"

    VECTOR_STORE: Literal["pgvector", "qdrant"] = "pgvector"
    PGVECTOR_HNSW_M: int = 16
    PGVECTOR_HNSW_EF_CONSTRUCTION: int = 64
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""

    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""

    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_PROJECT: str = "ai-native-capabilities"
    PHOENIX_COLLECTOR_ENDPOINT: str = "http://localhost:6006"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"

    MCP_TRANSPORT: Literal["streamable-http", "stdio"] = "streamable-http"
    MCP_INTERNAL_KB_URL: str = ""
    MCP_WEB_RESEARCH_URL: str = ""
    MCP_EPISODIC_MEMORY_URL: str = ""
    MCP_AUDIT_LOG_URL: str = ""
    MCP_GIT_REPO_URL: str = ""
    MCP_TEST_RUNNER_URL: str = ""
    MCP_SECURITY_SCANNER_URL: str = ""
    MCP_PRODUCT_CATALOG_URL: str = ""
    MCP_ORDER_MANAGEMENT_URL: str = ""
    MCP_ERP_SYSTEM_URL: str = ""
    MCP_WMS_SYSTEM_URL: str = ""
    MCP_REGULATORY_FEEDS_URL: str = ""
    MCP_KNOWLEDGE_GRAPH_URL: str = ""

    AUTONOMOUS_ACTION_THRESHOLD_USD: float = 5000.0
    EVAL_MODE: Literal["development", "ci", "production"] = "development"
    LLM_MODE: Literal["real", "mock"] = "real"
    ERP_MODE: Literal["mock", "production"] = "mock"

    SESSION_BUDGET_USD: float = 5.0
    RUN_BUDGET_USD: float = 10.0
    MONTHLY_BUDGET_USD: float = 500.0

    @field_validator(
        "LLM_DEFAULT",
        "LLM_FAST",
        "LLM_POWERFUL",
        "LLM_EMBEDDINGS",
        "OPENAI_LLM_DEFAULT",
        "OPENAI_LLM_FAST",
        "OPENAI_LLM_FRONTIER",
    )
    @classmethod
    def _validate_models(cls, value: str) -> str:
        return validate_model_string(value)

    @model_validator(mode="after")
    def _require_anthropic_key_unless_mock(self) -> Settings:
        placeholder_keys = {"", "sk-ant-...", "sk-ant-api03-..."}
        if self.LLM_MODE != "mock" and self.ANTHROPIC_API_KEY in placeholder_keys:
            raise ValueError("ANTHROPIC_API_KEY is required unless LLM_MODE=mock")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
