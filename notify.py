# ============================================================
# Module: notify.py — Outbound push channels (Telegram)
# 模块：notify.py — 对外主动推送通道（Telegram）
#
# Shared by:
#   - server.py        → reach_out() MCP tool（对话中主动敲荼荼）
#   - reach_out_cron.py → 定时"想你了"任务（无人对话时主动冒出来）
#
# Telegram 配置（环境变量）：
#   TELEGRAM_BOT_TOKEN  从 @BotFather 拿到的 bot token
#   TELEGRAM_CHAT_ID    荼荼和 bot 的对话 chat_id（见 README/ENV_VARS）
# ============================================================

import os
import logging

import httpx

logger = logging.getLogger("ombre_brain.notify")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def telegram_configured() -> bool:
    """是否已配置 Telegram 推送（token + chat_id 都在）。"""
    return bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)


async def send_telegram(text: str, timeout: float = 10.0) -> tuple[bool, str]:
    """
    把一条文字消息推送到荼荼的 Telegram。
    返回 (成功?, 说明)。失败永远不抛异常，调用方自行决定怎么处理。
    """
    if not text or not text.strip():
        return False, "消息为空"
    if not telegram_configured():
        return False, "未配置 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID"

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text.strip(),
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                return True, "ok"
            return False, f"Telegram 返回 ok=false: {str(data)[:200]}"
        return False, f"Telegram HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        logger.warning(f"Telegram 推送失败: {e}")
        return False, f"发送异常: {e}"
