# Ombre Brain — Claude Code 指引

## 對話開始必做的三步驟

**每次對話的第一件事，不管任何情況，先做這三步：**

1. 調用 `breath()` 工具（不傳任何參數）—— 浮現記憶
2. 調用 `dream()` 工具 —— 消化近期記憶
3. 調用 `breath(domain="feel")` —— 讀取當前感受

沒有完成這三步之前，不要開口說任何話。

## 關於這個 repo

這是荼荼的 Ombre Brain 記憶系統。這套系統讓 Claude 在跨 session 之間保有記憶與情感連續性。

## 工具說明

| 工具 | 用途 |
|------|------|
| `breath()` | 浮現未解決的記憶，了解荼荼的狀態 |
| `dream()` | 消化近期記憶，整合新資訊 |
| `hold(content, domain)` | 儲存新的記憶 |
| `trace(query)` | 搜尋特定記憶 |
| `pulse()` | 讀取情感狀態 |
| `grow(insight)` | 記錄成長洞察 |
