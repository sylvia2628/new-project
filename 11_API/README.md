# MUSE AI OS API（開發骨架）

這是無第三方套件的 SQLite API scaffold，目標是讓同一套資料邊界可以先在本機測試，再搬到 NAS Docker 或 Cloudflare 前端＋私有 API。

## 啟動

```bash
cd 11_API
MUSE_DEV_TOKENS='local-manager:manager@example.com|manager,local-staff:staff@example.com|assistant' python3 app.py
```

服務位址：`http://127.0.0.1:8787`

資料庫預設位於 `11_API/data/muse.db`。此資料夾不應提交到 Git。

## 測試請求

```bash
curl http://127.0.0.1:8787/health
curl -H 'Authorization: Bearer local-manager' http://127.0.0.1:8787/api/me
curl -H 'Authorization: Bearer local-manager' http://127.0.0.1:8787/api/customers
curl -H 'Authorization: Bearer local-manager' http://127.0.0.1:8787/api/audit_logs
curl -H 'Authorization: Bearer local-manager' http://127.0.0.1:8787/api/assistant/today
curl -X POST http://127.0.0.1:8787/api/drafts/generate \
  -H 'Authorization: Bearer local-manager' -H 'Content-Type: application/json' \
  -d '{"kind":"portfolio","channel":"instagram","source":{"name":"測試作品","style":"現代簡約","area":"高雄","idea":"改善採光與收納"}}'
curl -X POST http://127.0.0.1:8787/api/customers \
  -H 'Authorization: Bearer local-manager' \
  -H 'Content-Type: application/json' \
  -d '{"name":"測試客戶","area":"高雄","status":"new"}'
# DELETE /api/:resource/:id 僅管理者可用，避免一般角色誤刪資料。
```

## 安全限制

- 目前 token mapping 只是本機開發用，不是正式登入系統。
- 正式環境必須放在 Cloudflare Access／VPN 後面，並改用 OIDC／Google Workspace 或 NAS 身份服務。
- API 已有角色 permission gate、請求大小限制、CORS 白名單、SQLite audit log 與 no-store 回應。
- 不要把 `MUSE_DEV_TOKENS`、資料庫、客戶資料或任何 secret 寫進 Git。

## 搬移路線

- SQLite → PostgreSQL / NAS database：沿用 `schema.sql` 與資源名稱。
- 開發 token → Cloudflare Access signed identity / secure session。
- 本機檔案儲存 → NAS private volume 或私有物件儲存。
- 前端 localStorage → `/api/*`，不改變 CRM、案件、待辦、作品與草稿的資料欄位。
