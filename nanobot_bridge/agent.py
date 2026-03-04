from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import asyncio

def make_agent_loop():
    """Create a nanobot AgentLoop similarly to otta-dev/app.py but minimal.
    Requires nanobot-ai installed and configured.
    """
    from loguru import logger
    from nanobot.agent.loop import AgentLoop
    from nanobot.bus.queue import MessageBus
    from nanobot.config.loader import load_config
    from nanobot.cron.service import CronService
    from nanobot.config.loader import get_data_dir

    logger.disable("nanobot")
    config = load_config()
    bus = MessageBus()

    # Provider: reuse nanobot config routing
    from nanobot.providers.custom_provider import CustomProvider
    from nanobot.providers.litellm_provider import LiteLLMProvider
    from nanobot.providers.openai_codex_provider import OpenAICodexProvider

    model = config.agents.defaults.model
    provider_name = config.get_provider_name(model)
    p = config.get_provider(model)
    api_key = None
    if p and getattr(p, "api_key", None):
        api_key = p.api_key

    if provider_name == "openai_codex" or model.startswith("openai-codex/"):
        provider = OpenAICodexProvider(default_model=model)
    elif provider_name == "custom":
        provider = CustomProvider(
            api_key=api_key or "no-key",
            api_base=config.get_api_base(model) or "http://localhost:8000/v1",
            default_model=model,
        )
    else:
        provider = LiteLLMProvider(
            api_key=api_key,
            api_base=config.get_api_base(model),
            default_model=model,
            extra_headers=p.extra_headers if p else None,
            provider_name=provider_name,
        )

    cron_store = get_data_dir() / "cron" / "jobs.json"
    cron = CronService(cron_store)

    agent = AgentLoop(
        bus=bus,
        provider=provider,
        workspace=config.workspace_path,
        model=model,
        temperature=config.agents.defaults.temperature,
        max_tokens=config.agents.defaults.max_tokens,
        max_iterations=6,  # tool iterations; not used in our manual plan execution
        memory_window=config.agents.defaults.memory_window,
        brave_api_key=getattr(config.tools.web.search, "api_key", None) or None,
        exec_config=config.tools.exec,
        cron_service=cron,
        restrict_to_workspace=config.tools.restrict_to_workspace,
        mcp_servers=config.tools.mcp_servers,
    )
    return agent, provider

def provider_chat(provider, messages: List[Dict[str, str]], *, max_tokens: int = 800, temperature: float = 0.2) -> str:
    """Call nanobot provider with best-effort method discovery."""
    # Try common method names
    for name in ["chat", "complete", "completion", "generate", "invoke"]:
        fn = getattr(provider, name, None)
        if callable(fn):
            try:
                out = fn(messages=messages, max_tokens=max_tokens, temperature=temperature)
                # out might be dict or str
                if isinstance(out, str):
                    return out
                if isinstance(out, dict):
                    # common keys
                    for k in ["text","content","response","output"]:
                        if k in out and isinstance(out[k], str):
                            return out[k]
                    # openai-like
                    if "choices" in out:
                        ch = out["choices"][0]
                        if isinstance(ch, dict):
                            msg = ch.get("message") or {}
                            if isinstance(msg, dict) and "content" in msg:
                                return msg["content"]
                            if "text" in ch:
                                return ch["text"]
                return str(out)
            except TypeError:
                # signature mismatch, try calling with positional
                try:
                    out = fn(messages)
                    return out if isinstance(out, str) else str(out)
                except Exception:
                    continue
            except Exception:
                continue
    raise RuntimeError("Cannot call nanobot provider: unknown interface")
