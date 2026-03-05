<div align="center">

# 🦦 Otta CLI

### Minimal Loop · Small Router · Golden Replay

A command-line AI agent with local routing and nanobot execution.

Lower latency. Fewer cloud calls. Full control.
The more you use it, the smarter it gets.

[中文](README_CN.md) · [Quick Start](#-quick-start) · [Architecture](#-architecture)

</div>

---

## 🧠 Why Otta CLI?

Traditional AI agents are powerful — but:

- Token costs spiral quickly
- Every task requires a cloud call
- Execution paths aren't cached
- No learning from past successes
- Heavy dependencies and complex setup

Otta CLI is designed to fix that.

> AI should be efficient, reproducible, and self-improving.

---

## ✨ Core Capabilities

### 💰 Cost Reduction

**Local Router Model**
- Lightweight local router (0.5B parameters)
- Instant classification on-device
- Zero cloud cost for routing

**Golden Replay System**
- Reuse successful execution plans
- Slot-based parameterization
- Skip redundant LLM calls on repeated tasks

**Progressive Learning**
- Execution success → Extract slots → Promote to golden
- Next time same case_key → Direct replay
- Continuous cost reduction over time

---

### 🎯 Minimal Architecture

**Simple Execution Flow**
- Router → Golden Match → Execute (or Cloud → Execute → Learn)
- CLI-first design, no UI overhead
- Direct integration with nanobot

**Unified Capability System**
- Tools + MCP + Skills → Single capability namespace
- Capability chain learning from execution history
- Graph-based pattern recognition

**Flexible Router Backends**
- Python binding (recommended: persistent, low latency)
- Ollama (user-friendly alternative)
- CLI executor (minimal fallback)
- Automatic fallback chain

---

## 🏗 Architecture

### Execution Flow

```
User Input (CLI)
    ↓
Local Router (0.5B small model)
    ↓
Output: {route, risk, case_key, slots}
    ↓
Match golden_plans by case_key?
    ├─ Yes → Replay with nanobot.execute (zero cloud cost)
    └─ No  → Cloud LLM (via nanobot) → Execute → Promote to golden
```

### Technology Stack

| Layer | Technology |
|---|---|
| Interface | CLI (REPL / single command) |
| Router | Local small model (0.5B) |
| Executor | nanobot-ai (tools + MCP + cloud providers) |
| Storage | SQLite (golden_plans, candidates, exec_runs) |
| Capability | Unified capability graph (tools/MCP/skills) |

---

## 📦 Dependencies

- Python 3.10+
- `nanobot-ai` (already installed in your environment)
- Local model runtime (Python binding / Ollama / CLI executor)
- Router model file (0.5B quantized)

Install Python dependencies:

```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuration

### Router Backend Selection

Set environment variable:

```bash
# Option 1: Python binding (recommended)
export OTTA_ROUTER_BACKEND=py
export OTTA_ROUTER_MODEL=path/to/router.gguf

# Option 2: Ollama
export OTTA_ROUTER_BACKEND=ollama
export OTTA_OLLAMA_URL=http://127.0.0.1:11434
export OTTA_OLLAMA_MODEL=qwen2.5:0.5b-instruct

# Option 3: CLI executor
export OTTA_ROUTER_BACKEND=cli
export OTTA_ROUTER_EXECUTOR=path/to/executor
export OTTA_ROUTER_MODEL=path/to/router.gguf
```

*Windows: use `set` instead of `export`*

### Automatic Fallback

```bash
export OTTA_ROUTER_FALLBACKS=py,ollama,cli  # default
```

Router will try backends in order until one succeeds.

### Cloud Model (nanobot)

Uses nanobot's native config system (`~/.nanobot/config.yaml`).

**Configuration includes:**

- **LLM API Key & Base URL**: Configure in `~/.nanobot/config.yaml`
  ```yaml
  providers:
    openai:
      api_key: "sk-..."
      # optional: api_base for custom endpoints
    
    custom:
      api_key: "your-key"
      api_base: "https://your-endpoint.com/v1"
  
  agents:
    defaults:
      model: "gpt-4o-mini"  # or your preferred model
      temperature: 0.2
      max_tokens: 4000
  ```

- **Search API Key** (optional, for web search capability):
  ```yaml
  tools:
    web:
      search:
        api_key: "your-brave-api-key"  # Brave Search API
  ```

Refer to nanobot-ai documentation for full configuration options.

---

## 📖 文档

完整文档位于 [docs](docs/) 目录：

- **[配置指南](docs/CONFIGURATION.md)** - 详细的配置说明
- **[架构文档](docs/ARCHITECTURE.md)** - 系统设计和组件
- **[训练指南](docs/TRAINING.md)** - 训练自定义路由模型
- **[多卡训练](docs/MULTI_GPU_TRAINING.md)** - 多 GPU 加速训练
- **[llama.cpp 指南](docs/LLAMA_CPP.md)** - llama.cpp 编译和使用 ⭐
- **[API 参考](docs/API.md)** - 代码接口文档
- **[故障排查](docs/TROUBLESHOOTING.md)** - 常见问题解决

快速链接：
- [配置 LLM API Key](docs/CONFIGURATION.md#nanobot-配置详解)
- [训练路由器](docs/TRAINING.md)
- [llama.cpp 新版编译](docs/LLAMA_CPP.md) ⭐
- [理解架构](docs/ARCHITECTURE.md)

---

## 🚀 Quick Start

### Single Command Mode

```bash
python cli_once.py "organize my downloads folder by file type"
python cli_once.py "organize my downloads folder by file type"  # second time hits golden replay
```

### Interactive REPL

```bash
python cli_chat.py
```

---

## 💾 Data Structure (SQLite)

Default database: `./otta_min.db`

**Schema** (`store/schema.sql`):

- `golden_plans`: Replayable templates (slot-parameterized)
- `golden_candidates`: Cloud-generated candidates (new/tried/promoted/invalid)
- `exec_runs`: Execution history (route/source/latency/cloud_called)
- `capability_edges`: Learned capability chains (src→dst, count, last_used)

---

## 🛡️ Security Constraints

Execution safety through nanobot's security framework:

- Command confirmation for risky operations
- File access restrictions
- No permanent deletion (trash-based recovery)
- Explicit user approval for dangerous actions

---

## 🎯 Design Principles

**Minimal Closed Loop**

1. User input (CLI)
2. Local router → JSON output
3. Golden match? → Replay via nanobot
4. No match? → Cloud LLM → Execute → Learn
5. Success? → Parameterize → Promote to golden
6. Next time → Instant replay

**Execution & Cloud via nanobot**

- All tool execution through `nanobot.execute`
- Cloud LLM through nanobot providers
- Unified capability namespace (Tools + MCP + Skills)

---

## 🌱 Roadmap

- Deeper capability graph analysis
- Multi-modal router support
- Stronger slot extraction algorithms
- Community-contributed golden templates
- Enhanced learning mechanisms

---

<div align="center">

**Minimal Loop · Small Router · Golden Replay**


</div>
