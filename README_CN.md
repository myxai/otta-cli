<div align="center">

# 🦦 Otta CLI（命令行版）

### 最小闭环 · 小模型路由 · Golden 回放

基于本地路由和 nanobot 执行的命令行 AI 智能体。

更低延迟 · 更少云端调用 · 完全可控
用得越多，越智能。

[English](README.md) · [快速开始](#-快速开始) · [架构](#-架构)

</div>

---

## 🧠 为什么选择 Otta CLI？

传统 AI 智能体虽然强大 — 但：

- Token 成本快速攀升
- 每个任务都需要云端调用
- 执行路径无法缓存
- 无法从过往成功中学习
- 依赖重、配置复杂

Otta CLI 专为解决这些问题而生。

> AI 应该高效、可复现、能自我进化。

---

## ✨ 核心能力

### 💰 成本削减

**本地路由模型**
- 轻量级本地路由器（0.5B 参数）
- 设备端即时分类
- 路由阶段零云端成本

**Golden 回放系统**
- 复用成功的执行计划
- 基于 slot 的参数化
- 重复任务跳过冗余 LLM 调用

**渐进式学习**
- 执行成功 → 提取 slot → 提升为 golden
- 下次相同 case_key → 直接回放
- 持续降低成本

---

### 🎯 极简架构

**简洁执行流程**
- 路由器 → Golden 匹配 → 执行（或 云端 → 执行 → 学习）
- CLI 优先设计，无 UI 开销
- 直接集成 nanobot

**统一能力系统**
- Tools + MCP + Skills → 单一能力命名空间
- 从执行历史学习能力链
- 基于图的模式识别

**灵活的路由后端**
- Python 绑定（推荐：常驻、低延迟）
- Ollama（用户友好的备选）
- CLI 执行器（最小化回退）
- 自动回退链

---

## 🏗 架构

### 执行流程

```
用户输入（CLI）
    ↓
本地路由器（0.5B 小模型）
    ↓
输出：{route, risk, case_key, slots}
    ↓
按 case_key 匹配 golden_plans？
    ├─ 是 → 用 nanobot.execute 回放（零云端成本）
    └─ 否 → 云端 LLM（通过 nanobot）→ 执行 → 提升为 golden
```

### 技术栈

| 层次 | 技术 |
|---|---|
| 交互界面 | CLI（REPL / 单命令模式） |
| 路由器 | 本地小模型（0.5B） |
| 执行器 | nanobot-ai（tools + MCP + 云端 providers） |
| 存储 | SQLite（golden_plans、candidates、exec_runs） |
| 能力层 | 统一能力图（tools/MCP/skills） |

---

## 📦 依赖

- Python 3.10+
- `nanobot-ai`（已在你的环境中安装）
- 本地模型运行时（Python 绑定 / Ollama / CLI 执行器）
- 路由模型文件（0.5B 量化版）

安装 Python 依赖：

```bash
pip install -r requirements.txt
```

---

## ⚙️ 配置

### 路由后端选择

设置环境变量：

```bash
# 选项 1：Python 绑定（推荐）
export OTTA_ROUTER_BACKEND=py
export OTTA_ROUTER_MODEL=path/to/router.gguf

# 选项 2：Ollama
export OTTA_ROUTER_BACKEND=ollama
export OTTA_OLLAMA_URL=http://127.0.0.1:11434
export OTTA_OLLAMA_MODEL=qwen2.5:0.5b-instruct

# 选项 3：CLI 执行器
export OTTA_ROUTER_BACKEND=cli
export OTTA_ROUTER_EXECUTOR=path/to/executor
export OTTA_ROUTER_MODEL=path/to/router.gguf
```

*Windows 环境：使用 `set` 替代 `export`*

### 自动回退

```bash
export OTTA_ROUTER_FALLBACKS=py,ollama,cli  # 默认配置
```

路由器会按顺序尝试各后端，直到成功。

### 云端模型（nanobot）

使用 nanobot 原生配置系统（`~/.nanobot/config.yaml`）。

**配置内容包括：**

- **LLM API Key 和 Base URL**：在 `~/.nanobot/config.yaml` 中配置
  ```yaml
  providers:
    openai:
      api_key: "sk-..."
      # 可选：自定义端点的 api_base
    
    custom:
      api_key: "your-key"
      api_base: "https://your-endpoint.com/v1"
  
  agents:
    defaults:
      model: "gpt-4o-mini"  # 或你偏好的模型
      temperature: 0.2
      max_tokens: 4000
  ```

- **搜索 API Key**（可选，用于网页搜索能力）：
  ```yaml
  tools:
    web:
      search:
        api_key: "your-brave-api-key"  # Brave Search API
  ```

完整配置选项请参考 nanobot-ai 文档。

---

## 🚀 快速开始

### 单命令模式

```bash
python cli_once.py "把下载目录按类型整理一下"
python cli_once.py "把下载目录按类型整理一下"  # 第二次会命中 golden 回放
```

### 交互式 REPL

```bash
python cli_chat.py
```

---

## 💾 数据结构（SQLite）

默认数据库：`./otta_min.db`

**Schema**（`store/schema.sql`）：

- `golden_plans`：可回放模板（slot 参数化）
- `golden_candidates`：云端生成的候选（new/tried/promoted/invalid）
- `exec_runs`：执行历史（route/source/latency/cloud_called）
- `capability_edges`：学习到的能力链（src→dst、count、last_used）

---

## 🛡️ 安全约束

通过 nanobot 安全框架保障执行安全：

- 高风险操作需要确认
- 文件访问限制
- 无永久删除（基于回收站的恢复）
- 危险操作需明确用户批准

---

## 🎯 设计原则

**最小闭环**

1. 用户输入（CLI）
2. 本地路由器 → JSON 输出
3. Golden 匹配？→ 通过 nanobot 回放
4. 未匹配？→ 云端 LLM → 执行 → 学习
5. 成功？→ 参数化 → 提升为 golden
6. 下次 → 即时回放

**执行与云端通过 nanobot**

- 所有工具执行通过 `nanobot.execute`
- 云端 LLM 通过 nanobot providers
- 统一能力命名空间（Tools + MCP + Skills）

---

## 🌱 路线图

- 更深入的能力图分析
- 多模态路由器支持
- 更强的 slot 提取算法
- 社区贡献的 golden 模板
- 增强学习机制

---

<div align="center">

**最小闭环 · 小模型路由 · Golden 回放**

</div>
