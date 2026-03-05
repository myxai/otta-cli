from __future__ import annotations
import os
from typing import List, Optional
from .base import Router

def _parse_list(s: str) -> List[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip()]

def from_env() -> Router:
    """从环境变量创建路由器"""
    primary = os.environ.get("OTTA_ROUTER_BACKEND","").strip().lower()
    fallbacks = _parse_list(os.environ.get("OTTA_ROUTER_FALLBACKS","py,ollama,cli").lower())
    order = [primary] + [x for x in fallbacks if x != primary] if primary else fallbacks

    last_err = None
    for b in order:
        try:
            if b == "py":
                from .llama_py_router import from_env as f
                return f()
            if b == "ollama":
                from .ollama_router import from_env as f
                return f()
            if b == "cli":
                from .llamacpp_router import from_env as f
                return f()
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Cannot init router backends {order}: {last_err}")

def make_router_from_args(args) -> Router:
    """从命令行参数创建路由器"""
    backend = getattr(args, "router_backend", None) or os.environ.get("OTTA_ROUTER_BACKEND", "py").strip().lower()
    verbose = getattr(args, "verbose", False)
    
    # 获取 capabilities 配置
    cap_file = getattr(args, "cap_file", None) or os.environ.get("OTTA_CAP_FILE", "").strip() or None
    topn = getattr(args, "cap_topn", None) or int(os.environ.get("OTTA_CAP_TOPN", "60"))

    if backend == "py":
        from .llama_py_router import LlamaPythonRouter

        model_path = getattr(args, "router_model", None) or os.environ.get("OTTA_ROUTER_MODEL") or os.environ.get("OTTA_ROUTER_GGUF")
        if not model_path:
            raise ValueError("--router-model is required for py backend")

        n_gpu_layers = getattr(args, "router_gpu_layers", None)
        if n_gpu_layers is None:
            n_gpu_layers = int(os.environ.get("OTTA_ROUTER_N_GPU_LAYERS", "0"))

        n_threads = getattr(args, "router_threads", None)
        if n_threads is None:
            n_threads = int(os.environ.get("OTTA_ROUTER_THREADS", "0"))

        n_ctx = getattr(args, "router_ctx_size", None)
        if n_ctx is None:
            n_ctx = int(os.environ.get("OTTA_ROUTER_CTX", "1024"))

        return LlamaPythonRouter(gguf=model_path, n_ctx=n_ctx, n_threads=n_threads, n_gpu_layers=n_gpu_layers, verbose=verbose, cap_file=cap_file, topn=topn)

    elif backend == "ollama":
        from .ollama_router import OllamaRouter

        base_url = getattr(args, "ollama_url", None) or os.environ.get("OTTA_OLLAMA_URL", "http://127.0.0.1:11434")
        model = getattr(args, "ollama_model", None) or os.environ.get("OTTA_OLLAMA_MODEL")
        if not model:
            raise ValueError("--ollama-model is required for ollama backend")

        return OllamaRouter(base_url=base_url, model=model, verbose=verbose, cap_file=cap_file, topn=topn)

    elif backend == "cli":
        from .llamacpp_router import LlamaCliRouter

        llama_cli = getattr(args, "cli_executor", None) or os.environ.get("OTTA_LLAMA_CLI")
        model_path = getattr(args, "router_model", None) or os.environ.get("OTTA_ROUTER_MODEL") or os.environ.get("OTTA_ROUTER_GGUF")
        if not llama_cli:
            raise ValueError("--cli-executor is required for cli backend")
        if not model_path:
            raise ValueError("--router-model is required for cli backend")

        extra_parts = []
        n_threads = getattr(args, "router_threads", None)
        if n_threads:
            extra_parts.extend(["--threads", str(n_threads)])
        n_gpu_layers = getattr(args, "router_gpu_layers", None)
        if n_gpu_layers:
            extra_parts.extend(["-ngl", str(n_gpu_layers)])
        n_ctx = getattr(args, "router_ctx_size", None)
        if n_ctx:
            extra_parts.extend(["--ctx-size", str(n_ctx)])

        return LlamaCliRouter(llama_cli=llama_cli, gguf=model_path, extra=" ".join(extra_parts) if extra_parts else "", verbose=verbose, cap_file=cap_file, topn=topn)

    else:
        raise ValueError(f"Unknown router backend: {backend}")
