"""pytest configuration — sets env vars so modules can import."""

import os

os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key-12345")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")
os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("LLM_MODEL", "qwen3:4b")
os.environ.setdefault("EMBED_MODEL", "qwen3-embedding:8b")
