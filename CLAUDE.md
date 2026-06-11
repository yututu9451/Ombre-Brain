# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

Ombre Brain 是一个为 Claude 设计的永久记忆系统，通过 MCP 协议对接 Claude Desktop / Claude.ai。记忆以 Obsidian 原生 `.md` 文件存储（YAML frontmatter 存元数据），使用改进版艾宾浩斯遗忘曲线管理记忆权重，支持关键词模糊匹配 + 向量语义检索双通道。

---

## 常用命令

### 运行测试

```bash
# 本地测试（不需要 API Key）
pytest tests/test_scoring.py tests/test_feel_flow.py -v --asyncio-mode=auto

# 含 LLM 质量测试（需要 API Key）
OMBRE_API_KEY=your-key pytest tests/test_llm_quality.py -v --asyncio-mode=auto

# 运行单个测试文件
pytest tests/test_scoring.py -v --asyncio-mode=auto

# 运行单个测试函数
pytest tests/test_scoring.py::test_function_name -v --asyncio-mode=auto
```

### 启动服务

```bash
# 本地 stdio 模式（配合 Claude Desktop）
python server.py

# Docker 开发模式（含 Cloudflare Tunnel）
docker compose up -d

# Docker 预构建镜像
docker compose -f docker-compose.user.yml up -d
```

### 工具脚本

```bash
python backfill_embeddings.py   # 为存量桶批量生成 embedding
python check_buckets.py         # 检查桶数据完整性
python write_memory.py          # 手动写入记忆（绕过 MCP）
python migrate_to_domains.py    # 平铺桶 → 域子目录迁移
```

---

## 架构总览

### 模块依赖关系

```
server.py  ←→  Claude（MCP）
    ├── bucket_manager.py   记忆桶 CRUD + 多维搜索 + 激活更新
    ├── dehydrator.py       LLM 脱水压缩 / 自动打标 / 合并 / 拆分
    ├── decay_engine.py     遗忘曲线计算 + 后台归档循环
    ├── embedding_engine.py 向量化 + SQLite 存储 + 余弦相似度
    ├── import_memory.py    历史对话导入（Claude/ChatGPT/DeepSeek/Markdown）
    └── utils.py            配置加载 / 路径安全 / ID 生成 / token 估算
```

`server.py` 是唯一入口，负责注册 6 个 MCP 工具（`breath/hold/grow/trace/pulse/dream`）和 17 个 Dashboard REST 端点。其他模块均不直接暴露 HTTP。

### 存储结构

```
buckets/
├── permanent/          # pinned/protected 桶，不衰减
├── dynamic/<domain>/   # 普通记忆桶，按主题域分子目录
├── archive/            # 衰减分低于阈值后自动移入
└── feel/               # Claude 自省感受桶，不浮现不衰减
embeddings.db           # SQLite，存向量（与 md 文件分离）
```

每个桶是一个 `.md` 文件，YAML frontmatter 含 `id`、`name`、`domain`、`tags`、`valence`、`arousal`、`importance`、`activation_count`、`resolved`、`digested`、`pinned`、`type`、`created`、`last_active`。

---

## 关键系统行为

### 记忆生命周期

1. **写入**：`hold()` → `dehydrator.analyze()` 自动打标 → 相似度 > 75 则 `dehydrator.merge()` 合并到旧桶，否则 `bucket_manager.create()` 新建 → `embedding_engine.generate_and_store()` 写向量
2. **检索**：`breath(query)` → rapidfuzz 关键词搜索 + Gemini embedding 向量搜索双通道，四维评分（topic×4 + emotion×2 + time×1.5 + importance×1），命中后 `touch()` 刷新 `last_active` + `activation_count += 1` + 触发时间涟漪（±48h 内邻近桶 +0.3）
3. **衰减**：后台每 24h 运行 `decay_engine.run_decay_cycle()`，公式 `Score = importance × activation_count^0.3 × e^(-λ×days) × combined_weight`；score < 0.3 自动移入 `archive/`
4. **消化**：`dream()` → `hold(feel=True, source_bucket=id)` 写感受 → 源桶标记 `digested=True`，decay 系数从 ×0.05 降至 ×0.02

### 衰减公式关键参数

- **短期（≤3天）**：time_weight × 0.7 + emotion_weight × 0.3
- **长期（>3天）**：emotion_weight × 0.7 + time_weight × 0.3
- 新鲜度加成：`1.0 + e^(-hours/36)`（入库即 ×2.0，36h 后 ×1.5，72h 后 ≈×1.0）
- 特殊固定分：pinned/permanent → 999.0；feel 桶 → 50.0；resolved → ×0.05；resolved+digested → ×0.02；arousal>0.7 且未解决 → ×1.5

### feel 桶与普通桶的分离

- `hold(feel=True)` 写入 `feel/` 目录，`domain=[]`（空列表，不填充「未分类」）
- feel 桶**不参与**普通 `breath()` 浮现、衰减、合并
- 只通过 `breath(domain="feel")` 单独读取
- `dream()` 做结晶检测：≥3 条 feel 相似度 > 0.7 → 提示升级为 pinned 准则

### resolved 的正确行为

`trace(bucket_id, resolved=1)` **只更新 frontmatter**，桶留在 `dynamic/` 目录，不移动文件。之后由 decay 引擎自然降权归档。这是 B-01 修复的核心：不应在 `update()` 中立即调用 `_move_bucket(archive_dir)`。

---

## 降级策略

| 场景 | 行为 |
|------|------|
| `dehydrator` API 不可用 | 直接抛 `RuntimeError`，**不静默降级**（设计决策：本地降级质量不足会产生错误分类记忆） |
| embedding API 不可用 | `logger.warning()` + 降级为纯 keyword 搜索 |
| `hold()` 自动打标失败 | 降级默认值：`domain=["未分类"], valence=0.5, arousal=0.3` |
| `grow()` 单条解析失败 | `try/except` 隔离，标注 `⚠️条目名`，其他条继续 |

---

## 配置与环境变量

优先级：**环境变量 > config.yaml > 硬编码默认值**

| 变量 | 用途 |
|------|------|
| `OMBRE_API_KEY` | LLM API 密钥（脱水/打标/embedding 共用） |
| `OMBRE_BASE_URL` | 覆盖 `config.yaml` 的 `dehydration.base_url` |
| `OMBRE_TRANSPORT` | `stdio` / `sse` / `streamable-http` |
| `OMBRE_BUCKETS_DIR` | 记忆桶根目录 |
| `OMBRE_DASHBOARD_PASSWORD` | 预设 Dashboard 密码（覆盖文件密码） |
| `OMBRE_HOOK_SKIP` | 设为 `1` 跳过 SessionStart 钩子 |

关键 `config.yaml` 参数：`merge_threshold`（默认 75，合并相似度阈值）、`decay.lambda`（默认 0.05）、`embedding.enabled`、`scoring_weights.*`。

---

## Dashboard 认证

- 密码 SHA-256 + salt 存于 `{buckets_dir}/.dashboard_auth.json`
- Session 存内存，重启失效；cookie `ombre_session`（HttpOnly, 7天）
- `/health`、`/breath-hook`、`/dream-hook`、`/mcp*` 不需认证；所有 `/api/*` 需认证

---

## Claude Code 集成

`.claude/hooks/session_breath.py` 在 Claude Code 会话启动/恢复时自动调用，依次 GET `/breath-hook` 和 `/dream-hook`，将结果打印为会话上下文。服务不可用时静默跳过。

---

## 参考文档

- `BEHAVIOR_SPEC.md`：12 个完整使用场景的逐步流程 + 降级行为表 + B-01~B-10 Bug 修复记录
- `INTERNALS.md`：环境变量清单、所有硬编码值、config.yaml 完整键表、核心设计决策（共 10 条）
- `CLAUDE_PROMPT.md`：Claude 模型端使用指南（对话启动流程、工具使用原则）
- `ENV_VARS.md`：Webhook 事件格式与推送规范
