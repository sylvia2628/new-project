# MUSE AI OS 建置待辦與部署路線圖

更新日期：2026-07-16

## 建置目標

建立慕舍設計內部使用的 AI 工作中心。系統需先能在桌機與手機操作，之後可搬移到 Cloudflare 或公司 NAS，不讓目前的 GitHub Pages 架構限制後續發展。

## 目前安全狀態

- GitHub Pages 目前只適合作為介面展示，不適合放正式客戶、財務、合約或完整行事曆資料。
- 正式上線前，GitHub repository 應設為 Private，並關閉公開 Pages 預覽。
- 前端不可直接保存正式資料；正式資料必須放在受登入保護的 API 與資料庫。
- 網域限制不能取代登入驗證；正式入口需使用 Cloudflare Access、VPN 或 NAS 內網權限。

## 完成階段

### Phase 0：展示版與安全收斂

- [x] Git repository 建立與版本管理
- [x] GitHub Pages 介面展示
- [x] 桌機固定導航與手機快速切換
- [ ] GitHub repository 改為 Private
- [ ] 關閉公開 GitHub Pages，避免內部資料外洩
- [ ] 建立資料分級：公開、內部、機密、極機密
- [ ] 從展示資料中移除真實客戶與敏感財務資料

### Phase 1：可操作 MVP

- [ ] 首頁：今日摘要、本週風險、待審核項目
- [ ] CRM：新增、編輯、搜尋、追蹤日期、客戶摘要
- [ ] 案件：案件建立、階段、百分比、負責人、下一步與逾期
- [ ] 待辦：新增、指派、截止日、優先級、完成狀態
- [x] 行程：人工匯入、確認時間、案件關聯與提醒（目前完成手動新增與確認狀態；外部日曆同步另列 Phase 4）
- [ ] 作品：素材、設計理念、公開狀態、文案草稿
- [ ] 知識庫：公司規則、服務、收費與 FAQ 查詢
- [x] AI 草稿：客戶回覆、案件摘要、工作排序與作品文案（目前為規則式草稿引擎，外部 AI provider 另列 Phase 3）
- [x] 所有對外發送與發布都必須人工確認（API 已限制核准後才能發布，尚未串接外部平台）

### Phase 2：帳號、權限與資料安全

- [ ] 登入與登出
- [ ] 管理者、設計師、助理、工務、財務、行政角色
- [ ] 依案件、模組與欄位限制讀寫權限
- [ ] MFA / Google Workspace / Cloudflare Access
- [ ] 操作紀錄、登入紀錄、資料異動紀錄
- [ ] 備份、還原、刪除保留期與災難復原
- [ ] 機密資料不進 Git、不出現在前端原始碼

### Phase 3：檔案與 AI 工作流

- [ ] 私有檔案儲存：照片、PDF、CAD、合約、估價
- [ ] 案件資料夾自動分類
- [ ] 圖片、LINE 對話、語音文字的人工確認流程
- [ ] AI 產生官網、Facebook、Instagram、Google 商家與短影音草稿
- [ ] 發文審核佇列、版本、退回修改與發布紀錄
- [ ] 作品公開前的個資、地址與合約資訊檢查

### Phase 4：外部平台串接

- [ ] LINE Official Account API
- [ ] Google Drive API
- [ ] Google Calendar API
- [ ] Gmail API
- [ ] TimeTree 同步可行性研究
- [ ] Facebook / Instagram API
- [ ] 官網表單與 Webhook
- [ ] 串接錯誤重試、權杖更新與撤銷流程

### Phase 5：部署選項

#### Cloudflare 路線

- 前端部署到 Cloudflare Pages 或其他受保護的靜態主機
- API 與資料庫獨立部署
- 自訂公司子網域，例如 `ai.mus-design.com.tw`
- Cloudflare Access 限制公司 Email、群組、MFA 與設備狀態
- 高敏感資料再加 WARP、VPN 或裝置姿態檢查

#### NAS 路線

- NAS 上以 Docker / Container 部署前端、API 與資料庫
- 資料庫與檔案只保留在公司內部網路
- 外部連線使用 Cloudflare Tunnel，不直接暴露 NAS 管理介面
- 使用 Cloudflare Access 或 VPN 做身份驗證
- 建立 NAS 快照、異地備份與還原演練

## 正式完成條件

1. 未登入者不能看到任何內部頁面或 API 資料。
2. 不同角色只能讀寫被授權的模組與欄位。
3. 客戶、財務、合約、作品原始素材不會進入公開 GitHub Pages。
4. 所有 AI 對外訊息與發文都能被管理者審核、修改、拒絕並留下紀錄。
5. Cloudflare 與 NAS 至少各有一份可執行部署說明。
6. 有備份、還原、權限撤銷與離職人員停權流程。

## 建議順序

先完成本機可操作 MVP，再接登入與資料庫，最後決定 Cloudflare 或 NAS。不要先把正式資料放進目前的公開 GitHub Pages。
