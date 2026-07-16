# MUSE AI OS 資料模型與 API 邊界

更新日期：2026-07-16

## 設計原則

- 前端只負責畫面與操作，不保存正式資料。
- API 負責身份驗證、角色授權、資料驗證與操作紀錄。
- 資料庫與檔案儲存可在 Cloudflare、NAS 或其他私有主機替換。
- AI 只讀取被授權的資料，只產生草稿，不直接對外發送或發布。

## 核心實體

### users

`id`, `email`, `display_name`, `role`, `status`, `last_login_at`, `created_at`

角色：`manager`, `designer`, `assistant`, `site_manager`, `finance`, `admin`, `worker`

### customers

`id`, `name`, `phone`, `email`, `line_name`, `area`, `source`, `type`, `size_range`, `budget_range`, `style`, `needs_summary`, `owner_id`, `status`, `last_contact_at`, `next_follow_up_at`, `created_at`, `updated_at`

### cases

`id`, `name`, `customer_id`, `designer_id`, `site_manager_id`, `address`, `stage`, `progress`, `budget_range`, `next_action`, `due_at`, `risk_status`, `notes`, `created_at`, `updated_at`

### tasks

`id`, `title`, `case_id`, `assignee_id`, `priority`, `status`, `due_at`, `next_action`, `created_by`, `created_at`, `completed_at`

### schedules

`id`, `source`, `event_date`, `event_time`, `title`, `category`, `case_id`, `location`, `owner_id`, `confirmation_status`, `notes`, `created_at`, `updated_at`

### portfolios

`id`, `name`, `case_id`, `category`, `style`, `size`, `area`, `year`, `design_idea`, `public_status`, `publish_status`, `created_by`, `created_at`, `updated_at`

### assets

`id`, `portfolio_id`, `case_id`, `storage_key`, `asset_type`, `visibility`, `checksum`, `uploaded_by`, `created_at`

正式檔案不可用公開網址直接暴露；下載應由 API 驗證後產生限時連結。

### drafts

`id`, `kind`, `channel`, `source_type`, `source_id`, `content`, `status`, `created_by_ai`, `reviewed_by`, `reviewed_at`, `published_at`, `created_at`, `updated_at`

狀態：`draft`, `in_review`, `approved`, `rejected`, `published`, `cancelled`

### audit_logs

`id`, `actor_id`, `action`, `resource_type`, `resource_id`, `before_json`, `after_json`, `ip_hash`, `created_at`

## API 邊界

### 身份與權限

- `GET /api/me`
- `GET /api/users`
- `PATCH /api/users/:id/role`
- `POST /api/auth/logout`

### CRM 與案件

- `GET /api/customers`
- `POST /api/customers`
- `PATCH /api/customers/:id`
- `GET /api/cases`
- `POST /api/cases`
- `PATCH /api/cases/:id`

### 待辦與行程

- `GET /api/tasks`
- `POST /api/tasks`
- `PATCH /api/tasks/:id`
- `GET /api/schedules`
- `POST /api/schedules/import`

### 作品、檔案與草稿

- `GET /api/portfolios`
- `POST /api/portfolios`
- `POST /api/assets/upload-url`
- `POST /api/drafts/generate`
- `PATCH /api/drafts/:id/review`
- `POST /api/drafts/:id/publish`（必須再次檢查管理者權限）

### AI 秘書

- `GET /api/assistant/today`
- `GET /api/assistant/weekly`
- `POST /api/assistant/summarize`

## 正式資料流程

```text
瀏覽器／手機
  ↓ HTTPS + Access / VPN
前端
  ↓ Bearer session / secure cookie
API
  ├─ 角色與欄位授權
  ├─ 資料庫
  ├─ 私有檔案儲存
  ├─ AI provider
  └─ audit_logs
```

目前 GitHub Pages 的 localStorage 只作為介面開發暫存，不能直接升級成正式資料層。
