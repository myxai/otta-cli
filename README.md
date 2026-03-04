# Otta 最小闭环（CLI）— llama.cpp 小模型路由 + nanobot 执行/云端

你要的目标：**不做原先 4 大引擎，不要 UI，只保留 nanobot**，做一个可跑的“最小闭环”：

1) 用户输入（命令行对话 / REPL）
2) 本地小模型（llama.cpp）输出 Router JSON（route/risk/case_key/slots）
3) 命中 golden_plans → 回放（用 nanobot tools.execute 执行）
4) 未命中 → 云端大模型（通过 nanobot provider）生成 candidate plan → nanobot 执行
5) 执行成功 → 参数化(slot 化) → promote 写入 golden_plans（SQLite）
6) 下一次同 case_key → 直接回放，减少云端调用

---

## 0. 依赖

- Python 3.10+
- 已安装 `nanobot-ai`（与你现有环境保持一致）
- 已编译好的 llama.cpp `llama-cli`（或 `main`），以及小模型 GGUF

安装 Python 依赖：
```bash
pip install -r requirements.txt
```

---

## 1. 配置

### 1.1 llama.cpp 路由模型
环境变量：
- `OTTA_LLAMA_CLI`：llama.cpp 可执行文件路径（如 `./llama-cli`）
- `OTTA_ROUTER_GGUF`：路由模型 GGUF 路径

可选：
- `OTTA_LLAMA_EXTRA`：附加参数（如 `--threads 8 --ctx-size 1024 --temp 0`）

### 1.2 nanobot 云端模型
使用 nanobot 自己的配置体系（~/.nanobot/config.yaml 等）。本项目直接复用 nanobot 的 `load_config()`。

---

## 2. 运行（最小闭环）

单句模式：
```bash
python cli_once.py "把下载目录按类型整理一下"
python cli_once.py "把下载目录按类型整理一下"   # 第二次应命中回放（golden）
```

REPL 对话：
```bash
python cli_chat.py
```

---

## 3. 数据结构（SQLite）

- `store/schema.sql`
  - `golden_plans`：可回放模板（slot 化）
  - `golden_candidates`：云端生成的候选（new/tried/promoted/invalid）
  - `exec_runs`：每次执行记录（route/source/latency/cloud_called）

数据库默认：`./otta_min.db`

---

## 4. 训练与导出（0.5B Router）

目录：`train/`

### 4.1 生成训练数据（Router-only）
```bash
python train/generate_router_train.py --catalog train/template_catalog.json --n_total 5000 --out_train train/train.jsonl --out_val train/val.jsonl
```

### 4.2 LoRA 微调（HuggingFace + PEFT，避免 TRL 版本坑）
```bash
python train/sft_lora_train.py \
  --base_model Qwen/Qwen2.5-0.5B-Instruct \
  --train_jsonl train/train.jsonl \
  --val_jsonl train/val.jsonl \
  --out_dir out/lora_router \
  --max_seq_len 1024 \
  --steps 800
```

### 4.3 合并 LoRA → HF 模型
```bash
python train/merge_lora.py --base_model Qwen/Qwen2.5-0.5B-Instruct --lora_dir out/lora_router --out_dir out/merged_router
```

### 4.4 转 GGUF（llama.cpp）
你需要有 llama.cpp 仓库：
- `convert-hf-to-gguf.py`
- `quantize`

示例：
```bash
python /path/to/llama.cpp/convert-hf-to-gguf.py out/merged_router --outfile out/router.f16.gguf
/path/to/llama.cpp/quantize out/router.f16.gguf out/router.q4_k_m.gguf q4_k_m
```

---

## 5. 关键约束（你要求的“最小闭环”）
- 不引入旧的 4 大引擎（意图引擎/策略中枢/执行棱镜/能力森林）——这里只做 Router + Golden 回放闭环。
- 执行层与云端 LLM 调用都通过 nanobot（tools.execute + provider）。
- 本地小模型推理采用 llama.cpp（subprocess 调用）。
- CLI 形态即可。

生成时间：2026-03-04


## 6. 工具白名单（推荐）

先打印你环境里 nanobot 实际可用工具名，然后 Cloud 编译会自动用白名单约束输出：
```bash
python tools/print_nanobot_tools.py
```


## 6. 用 nanobot 实际工具列表驱动训练数据（推荐流程）

### 6.1 导出当前环境可用工具白名单
```bash
python tools/print_nanobot_tools.py --out_json runtime/allowed_tools.json --max_n 200
```

### 6.2 生成训练数据（system 注入 Allowed tools）
```bash
python train/generate_router_train.py --catalog train/template_catalog.json --n_total 5000 --out_train train/train.jsonl --out_val train/val.jsonl --allowed_tools_json runtime/allowed_tools.json --inject_tools_in_system 1 --system_tools_top_n 60
```

说明：
- 不建议把所有工具都塞进 system（会涨 token、注意力发散）
- `system_tools_top_n` 推荐 40~80，保留“常用+关键”工具即可


## v4 Capability System

统一能力层：

Tools + MCP + Skills → Capability

导出能力：

```
python tools/export_capabilities.py
```

生成训练数据：

```
python train/generate_router_train.py \
  --catalog train/template_catalog.json \
  --capabilities_json runtime/capabilities.json \
  --n_total 5000 \
  --out_train train/train.jsonl \
  --out_val train/val.jsonl
```

Router 训练会看到：

```
Available capabilities:
web_search, smart_fetch, exec, ...
```


## v5 Capability Graph（能力链学习）

系统会从每次“成功执行”的 plan 中学习 capability chain，并写入 SQLite 表 `capability_edges`：

- src -> dst
- count（出现次数）
- last_used_at

查看学习到的能力链：
```bash
python tools/show_capability_graph.py --db otta_min.db --limit 50
```

Cloud 编译输出 steps 已升级为：
- {"capability": "...", "args": {...}}

runner 仍兼容旧格式（tool 字段）。


## v6 Router Backends（支持 llama-cpp-python + Ollama + CLI，带自动 fallback）

Router 后端通过环境变量选择：

- `OTTA_ROUTER_BACKEND=py|ollama|cli`
- `OTTA_ROUTER_FALLBACKS=py,ollama,cli`（默认）

### 1) llama-cpp-python（推荐：常驻、低延迟）
安装（可选）：
```bash
pip install llama-cpp-python
```
配置：
```bash
set OTTA_ROUTER_BACKEND=py
set OTTA_ROUTER_GGUF=path/to/router.q4_k_m.gguf
```
（Linux/macOS 用 `export`）

### 2) Ollama（可选：用户友好）
配置：
```bash
set OTTA_ROUTER_BACKEND=ollama
set OTTA_OLLAMA_URL=http://127.0.0.1:11434
set OTTA_OLLAMA_MODEL=qwen2.5:0.5b-instruct
```
Router 会调用 `POST /api/generate`（非流式）

### 3) llama-cli（兜底：最少依赖）
配置：
```bash
set OTTA_ROUTER_BACKEND=cli
set OTTA_LLAMA_CLI=path/to/llama-cli(.exe)
set OTTA_ROUTER_GGUF=path/to/router.q4_k_m.gguf
```
