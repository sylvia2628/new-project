# Cloudflare 與 NAS 部署說明

這份文件先定義可搬移的部署邊界；正式部署前仍需依公司網域、NAS 型號、Google Workspace 與備份策略補齊實際值。

## 共通要求

- 前端、API、資料庫、檔案儲存分離。
- GitHub repository 設為 Private，禁止把 `.env`、Token、客戶原始資料提交進 Git。
- 所有正式流量使用 HTTPS。
- Access／VPN 驗證在 API 之前；API 仍需再次檢查使用者角色。
- 資料庫每日備份，至少保留一份不在 NAS 本機的備份。
- 每次部署保留版本號與還原方式。

## Cloudflare 路線

```text
ai.mus-design.com.tw
  ↓ Cloudflare Access
Cloudflare Pages / 前端
  ↓ HTTPS API
API 主機
  ├─ PostgreSQL / SQLite（依規模）
  └─ 私有物件儲存
```

建議順序：

1. 建立專用子網域，不使用公開展示網址。
2. 建立 Cloudflare Access application。
3. Allow 只允許公司 Email 或 Google Workspace 群組。
4. 啟用 MFA；敏感模組再要求 WARP／裝置姿態或 VPN。
5. 前端只保存短期 session，不保存 API secret。
6. 將 API、資料庫與檔案儲存放在可備份的主機，不依賴 Pages localStorage。

## NAS 路線

```text
公司內部網路
  ↓
NAS Docker Compose
  ├─ frontend
  ├─ api
  ├─ database
  └─ private files
        ↑
Cloudflare Tunnel / VPN（外部需要時）
```

建議順序：

1. 確認 NAS 支援 Container / Docker、磁碟快照與排程備份。
2. API、資料庫、檔案儲存使用不同 volume。
3. NAS 管理介面不得直接暴露在網際網路。
4. 外部存取使用 Cloudflare Tunnel 或 VPN，不開放 router port forwarding 到 NAS 管理介面。
5. 先用測試資料驗證還原，再放正式資料。
6. 建立人員離職、帳號撤銷、備份遺失與 NAS 故障的處理流程。

## 不可接受的部署方式

- 把正式客戶資料寫進公開 GitHub Pages 的 HTML 或 JavaScript。
- 只靠「網址很難猜」當作安全機制。
- 把 NAS 管理介面直接轉發到公開網路。
- 把 API Token、Google Client Secret 或資料庫密碼提交到 Git。
- 只做登入畫面，卻沒有 API 端的角色授權。
