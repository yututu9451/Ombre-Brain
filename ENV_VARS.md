# 环境变量参考

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `OMBRE_API_KEY` | 是 | — | Gemini / OpenAI-compatible API Key，用于脱水(dehydration)和向量嵌入 |
| `OMBRE_BASE_URL` | 否 | `https://generativelanguage.googleapis.com/v1beta/openai/` | API Base URL（可替换为代理或兼容接口） |
| `OMBRE_TRANSPORT` | 否 | `stdio` | MCP 传输模式：`stdio` / `sse` / `streamable-http` |
| `OMBRE_PORT` | 否 | `8000` | HTTP/SSE 模式监听端口（仅 `sse` / `streamable-http` 生效） |
| `OMBRE_BUCKETS_DIR` | 否 | `./buckets` | 记忆桶文件存放目录（绑定 Docker Volume 时务必设置） |
| `OMBRE_HOOK_URL` | 否 | — | Breath/Dream Webhook 推送地址（POST JSON），留空则不推送 |
| `OMBRE_HOOK_SKIP` | 否 | `false` | 设为 `true`/`1`/`yes` 跳过 Webhook 推送（即使 `OMBRE_HOOK_URL` 已设置） |
| `OMBRE_DASHBOARD_PASSWORD` | 否 | — | 预设 Dashboard 访问密码；设置后覆盖文件存储的密码，首次访问不弹设置向导 |
| `OMBRE_DEHYDRATION_MODEL` | 否 | `deepseek-chat` | 脱水/打标/合并/拆分用的 LLM 模型名（覆盖 `dehydration.model`） |
| `OMBRE_DEHYDRATION_BASE_URL` | 否 | `https://api.deepseek.com/v1` | 脱水模型的 API Base URL（覆盖 `dehydration.base_url`） |
| `OMBRE_MODEL` | 否 | — | `OMBRE_DEHYDRATION_MODEL` 的别名（前者优先） |
| `OMBRE_EMBEDDING_MODEL` | 否 | `gemini-embedding-001` | 向量嵌入模型名（覆盖 `embedding.model`） |
| `OMBRE_EMBEDDING_BASE_URL` | 否 | — | 向量嵌入的 API Base URL（覆盖 `embedding.base_url`；留空则复用脱水配置） |
| `TELEGRAM_BOT_TOKEN` | 否 | — | Telegram bot token（@BotFather 获取）。配置后 `reach_out` 工具与"想你了"背景循环才能真的推送 |
| `TELEGRAM_CHAT_ID` | 否 | — | 荼荼和 bot 的对话 chat_id（私聊 bot 后访问 `https://api.telegram.org/bot<token>/getUpdates` 可看到） |
| `REACH_OUT_ENABLED` | 否 | `false` | 设为 `true`/`1`/`yes` 时，在远程(sse/streamable-http)模式下启动"想你了"背景循环 |
| `REACH_OUT_INTERVAL_SECONDS` | 否 | `10800` | 背景循环判断间隔（秒），默认 3 小时 |
| `REACH_OUT_PROBABILITY` | 否 | `0.5` | 每次判断真正发出的概率（0~1），避免太频繁 |
| `REACH_OUT_TZ` | 否 | `Asia/Taipei` | 判断安静时段用的时区 |
| `REACH_OUT_QUIET_START` | 否 | `2` | 安静时段开始小时(含)，此区间内不主动打扰 |
| `REACH_OUT_QUIET_END` | 否 | `11` | 安静时段结束小时(不含) |
| `REACH_OUT_FORCE` | 否 | `false` | `reach_out_cron.py` 独立运行时跳过概率+安静时段（测试用） |
| `REACH_OUT_DRY_RUN` | 否 | `false` | `reach_out_cron.py` 独立运行时只生成不发送（测试用） |
| `REACH_OUT_MODEL` | 否 | — | 撰写"想你了"消息用的模型（默认复用脱水模型） |
| `REACH_OUT_API_KEY` | 否 | — | 撰写"想你了"消息用的独立 API Key。设置后单独建客户端（不复用脱水 key），可指向"真 Claude"。需同时设 `REACH_OUT_MODEL` |
| `REACH_OUT_BASE_URL` | 否 | — | 上述独立客户端的 Base URL（OpenAI 兼容）。例：OpenRouter `https://openrouter.ai/api/v1`，模型填 `anthropic/claude-...`，即可让消息由真 Claude 撰写 |

## 说明

- `OMBRE_API_KEY` 也可在 `config.yaml` 的 `dehydration.api_key` / `embedding.api_key` 中设置，但**强烈建议**通过环境变量传入，避免密钥写入文件。
- `OMBRE_DASHBOARD_PASSWORD` 设置后，Dashboard 的"修改密码"功能将被禁用（显示提示，建议直接修改环境变量）。未设置则密码存储在 `{buckets_dir}/.dashboard_auth.json`（SHA-256 + salt）。

## Webhook 推送格式 (`OMBRE_HOOK_URL`)

设置 `OMBRE_HOOK_URL` 后，Ombre Brain 会在以下事件发生时**异步**（fire-and-forget，5 秒超时）`POST` JSON 到该 URL：

| 事件名 (`event`) | 触发时机 | `payload` 字段 |
|------------------|----------|----------------|
| `breath` | MCP 工具 `breath()` 返回时 | `mode` (`ok`/`empty`), `matches`, `chars` |
| `dream` | MCP 工具 `dream()` 返回时 | `recent`, `chars` |
| `breath_hook` | HTTP `GET /breath-hook` 命中（SessionStart 钩子） | `surfaced`, `chars` |
| `dream_hook` | HTTP `GET /dream-hook` 命中 | `surfaced`, `chars` |

请求体结构（JSON）：

```json
{
  "event": "breath",
  "timestamp": 1730000000.123,
  "payload": { "...": "..." }
}
```

Webhook 推送失败仅在服务日志中以 WARNING 级别记录，**不会影响 MCP 工具的正常返回**。
