# iLabCICT Backend Documentation

## 1. Project overview

iLabCICT is the backend for the Laboratory Maintenance and Technical Support Management System of the College of Information and Communications Technology (CICT), Bulacan State University Main Campus. It provides a JSON REST API and WebSocket channels used by the web and mobile clients to manage laboratory rooms, computers, maintenance work, support tickets, reports, notifications, and users.

The project is a Django application organized by feature under `api/`. Each feature package typically contains models, serializers, views, services, and URL configuration:

- **Views** handle HTTP requests, parsing, and permissions.
- **Serializers** validate and shape data.
- **Services** hold business rules, persistence, notifications, audit logging, and real-time broadcasts.

## 2. Technology stack

| Technology | Use in this project |
|---|---|
| Python | Backend language |
| Django 6 | Web framework, ORM, admin, sessions |
| Django REST Framework | JSON API views, serializers, throttling |
| Simple JWT (`djangorestframework-simplejwt`) | Access and refresh token authentication |
| PostgreSQL | Relational database; connection read from `DATABASE_URL` |
| Neon | PostgreSQL hosting named in the project README |
| Django Channels + Daphne | ASGI and WebSocket support, channel groups for real-time events |
| `InMemoryChannelLayer` | Currently configured channel layer (single-process only) |
| `channels_redis` / `redis` | Installed in `requirements.txt`; the Redis layer is not currently configured in settings |
| Cloudinary + `django-cloudinary-storage` | Media storage (profile/ticket images) and printable templates |
| Groq | LLM provider for the technician chatbot and AI report summaries |
| drf-yasg | Swagger and ReDoc API documentation UIs |
| django-cors-headers | CORS for configured frontend origins |
| WhiteNoise | Static-file serving |
| python-dotenv | Loads environment values from `.env` |
| openpyxl | Reads Excel files for computer import |
| better-profanity | Chat input filtering (plus custom Tagalog words from the environment) |
| argon2-cffi | Password hashing (custom tuned Argon2 hasher, PBKDF2 fallback) |
| Gunicorn / Uvicorn | Application servers (the `Procfile` uses Gunicorn with the WSGI app) |
| requests / httpx | Outbound HTTP calls (email service, etc.) |

Pinned dependencies are listed in `requirements.txt`.

## 3. Architecture and request flow

### HTTP request flow

1. Django routes the request through `ilabcict/urls.py` to `/api/` (`api/urls.py`).
2. The feature URL module selects a view.
3. DRF authentication (JWT), permission classes, throttling, parsing, and serializer validation run.
4. The view calls a feature service for business operations.
5. The ORM reads or writes PostgreSQL. Operations may also use Cloudinary, the email service, or Groq.
6. A JSON response is returned.

### Real-time flow

1. A client opens a WebSocket with a JWT in the query string.
2. `JWTAuthMiddleware` resolves the user and attaches it to the connection scope.
3. The consumer joins user and role channel groups.
4. Services call `channel_layer.group_send(...)` after create/update/delete operations, and consumers forward events as JSON.

### Feature packages

| Package | Responsibility |
|---|---|
| `api/user` | Accounts, profiles, login, password change/reset, profile statistics |
| `api/otp_code` | OTP generation and verification for password reset |
| `api/room` | Rooms, room computers, transfer, spreadsheet import |
| `api/computer` | Inventory, peripherals, archive, maintenance details |
| `api/ticket` | Report/request tickets, assignment, status, archive |
| `api/repair_log` | Technician repair records tied to tickets |
| `api/maintenance_history` | Work performed on computers |
| `api/request_history` | Records of completed request tickets |
| `api/report` | Weekly/monthly/assignment reports, AI summaries |
| `api/notification` | In-app notifications, read/archive state |
| `api/audit_logs` | Audit trail and admin live feed |
| `api/task_scheduler` | Scheduled report generation |
| `api/printable_template` | Cloudinary-backed printable templates |
| `api/chatbot` | Technician troubleshooting assistant |
| `api/user_push_token` | Expo push token registration |
| `api/middlewares` | WebSocket JWT authentication |
| `api/common` | Date validation, code generation, prompt loading |

## 4. API conventions

The API is mounted under `/api`. The Django admin is at `/admin/`. All endpoint paths below are relative to `/api`.

JSON is used unless an endpoint uploads a file (multipart form data). Protected requests send:

```http
Authorization: Bearer <access-token>
```

- Dates in filters use `YYYY-MM-DD`.
- `q` is a free-text search. On most list endpoints it cannot be combined with other filters (the API returns a validation error).
- Pagination is not uniform. Notifications and audit logs return `{"results": [...], "next": "<url>"}`. Most other lists return a plain JSON array.

### Token lifetimes and sessions

- Access token: 2 hours. Refresh token: 7 days.
- Chat session inactivity timeout: 20 minutes.
- Chat prompt history: the last three user/assistant exchanges plus the current message.

### Roles

| Role | Typical capability |
|---|---|
| `admin` | User management, all data, assignment, scheduling, templates, audit logs |
| `technician` | Works assigned and open tickets, repair logs, computers, reports, chatbot |
| `faculty` | Creates tickets, sees their own tickets, can archive/unarchive them |

"Staff" in the tables below means any authenticated user with one of the three roles.

### Throttling

| Scope | Rate |
|---|---|
| Anonymous (default) | 20/minute |
| Authenticated (default) | 120/minute |
| Login | 5/minute |
| Password-reset endpoints | 3/minute |

## 5. API endpoint reference

### 5.1 Health and schema

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/ping/` | Public | Returns `{"ok": true}` |
| GET | `/swagger/` | Public | Swagger UI |
| GET | `/redoc/` | Public | ReDoc UI |

### 5.2 Authentication and push tokens

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/auth/login/` | Public, throttled | Returns `access`, `refresh`, and user data (`id`, `role`, `first_name`, `last_name`, `email`, `is_active`, `profile_image`). Tokens carry `first_name`, `last_name`, `role` claims. |
| POST | `/auth/refresh/` | Public | Body `{"refresh": "..."}` returns a new access token |
| GET | `/auth/push-token/` | Authenticated | List the current user's push tokens |
| POST | `/auth/push-token/` | Authenticated | Register a token: `{"expo_push_token": "..."}` |
| DELETE | `/auth/push-token/` | Authenticated | Remove a token: `{"expo_push_token": "..."}` |

Successful and failed logins are recorded in the audit log.

### 5.3 Users and passwords

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/users/` | Admin | List users. Filters: `role`, `is-active` (`true`/`false`) |
| POST | `/users/` | Admin | Create a user. A random 12-character temporary password is generated and emailed |
| GET | `/users/{id}/` | Admin or profile owner | Profile with optional stats via `include` |
| PUT/PATCH | `/users/{id}/` | Admin or profile owner | Update profile (JSON or multipart for `profile_image`) |
| DELETE | `/users/{id}/` | Admin | Delete a user |
| PATCH | `/users/reset-password/{id}/` | Profile owner | Change password: `old_password`, `password` |
| GET | `/users/available-custodian/` | Admin | Faculty not yet assigned as a custodian; optional `include=<user id>` keeps a current custodian in the list |
| GET | `/users/available-technician/` | Admin | List technicians |
| POST | `/users/forgot-password/send-email/` | Public, throttled | Email a reset link: `{"email": "..."}` |
| POST | `/users/forgot-password/reset-password/` | Public, throttled | `token`, `password`, `confirm_password` |
| POST | `/users/forgot-password/otp/send-email/` | Public, throttled | Email a one-time code: `{"email": "..."}` |
| POST | `/users/forgot-password/otp/verify-otp/` | Public, throttled | `email`, 6-character `code`; returns `reset_token` |
| POST | `/users/forgot-password/otp/reset-password/` | Public, throttled | `reset_token`, `new_password` (validated by Django password validators) |

Profile statistics: `include=faculty-stats` (faculty) returns tickets submitted today, tickets per day for the last 7 days, and totals. `include=technician-stats` (technician) returns assigned totals by type, today's totals, resolved tickets per day for 7 days, and today's status breakdown. Weekday labels are `M, T, W, TH, F, SA, SU`; day grouping uses `Asia/Manila`.

Reset flows:

- **Link flow:** a signed token (purpose `password_reset`, 15-minute lifetime) is emailed as a link to the web app.
- **OTP flow:** request a code, verify it to receive a reset token, then submit the new password. OTP codes and reset tokens are stored hashed, with attempt counting, expiry, and single-use tracking (`OTPCode` model).

### 5.4 Rooms

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/rooms/` | Staff | List rooms. Filters: `status`, `building`, `room`, `date`, `q`, `include=computers` |
| POST | `/rooms/` | Admin | Create a room |
| GET | `/rooms/{id}/` | Staff | Room detail with computer counts |
| PUT/PATCH | `/rooms/{id}/` | Admin | Update a room |
| DELETE | `/rooms/{id}/` | Admin | Delete a room |
| GET | `/rooms/{id}/computers/` | Staff | Room with its computers. Filters: `q`, `status`, `date` |
| GET | `/rooms/{id}/computers/archive/` | Admin, technician | Archived computers in the room |
| GET | `/rooms/{id}/computers/{computer-code}/` | Staff | One computer by code |
| GET | `/rooms/{room-name}/computers/` | Staff | Room with computers by room name |
| GET | `/rooms/{room-name}/computers/{computer-code}/` | Staff | One computer by room name and code |
| POST | `/rooms/{room-id}/computers/import/` | No role check declared | Import computers from an Excel file (multipart field `file`) |
| POST | `/rooms/{old-room-id}/transfer-computers/` | No role check declared | Move all non-archived computers: `{"destination_room_id": 2}` |

Values: room `status` is `operational`, `maintenance`, or `out_of_service`; `building` is `pimentel`, `law`, or `acad`.

Transfers run in a transaction. Source and destination must differ and exist. If computer numbers would collide in the destination room, the moved computers are renumbered to the next free `PC-<n>`. The transfer and renumbering are audit-logged, and `computer_transferred_out` / `computer_transferred_in` events are broadcast to both rooms' channel groups.

### 5.5 Computers

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/computers/` | Staff | List computers (filters handled by the computer service) |
| POST | `/computers/` | Admin, technician | Create computers; `quantity` creates several at once |
| GET | `/computers/{id}/` | Staff | Detail by database ID |
| PUT/PATCH | `/computers/{id}/` | Admin, technician | Update |
| DELETE | `/computers/{id}/` | Admin | Delete |
| GET | `/computers/{computer-code}/` | Staff | Detail by code; `include=maintenance-history` adds history |
| GET | `/computers/archive/` | Admin, technician | Archived computers |
| POST | `/computers/{id}/archive/` | No role check declared | Archive |
| POST | `/computers/{id}/unarchive/` | No role check declared | Restore |
| GET | `/computers/active/` | No role check declared | Active computers |
| GET | `/computers/active/peripherals/all/` | No role check declared | Active computers with active peripherals |
| GET | `/computers/active/peripherals/` | No role check declared | Filter by peripheral `type` and `status` |
| GET | `/computers/active/peripherals/none/` | No role check declared | Active computers with no peripherals |

Fields: room, generated `computer_code` (`PC` + digits), room-local `computer_number` (unique per room), `operating_system`, `gpu`, `cpu`, `ram_size_installed` / `ram_unit`, `disk_size_installed` / `disk_unit`, `build_version`, `motherboard`, `computer_status`, `is_archived`, and `monitor_status`, `mouse_status`, `keyboard_status`, `ups_status`.

Computer status: `active`, `unserviceable`, `pending`. Peripheral status: `none`, `active`, `unserviceable`, `pending`.

### 5.6 Tickets

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/tickets/` | Staff | List tickets (role-scoped). Filters: `q`, `type`, `status`, `date` |
| POST | `/tickets/` | Faculty | Create a ticket; the caller becomes `reported_by` |
| GET | `/tickets/paginated/` | Staff | Same listing as `/tickets/` |
| GET | `/tickets/{id}/` | Admin, assigned technician, reporting faculty | Ticket detail |
| PATCH | `/tickets/{id}/` | Admin, technician | Update `status` / assignment |
| DELETE | `/tickets/{id}/` | Admin | Delete |
| GET | `/tickets/archive/` | Admin, faculty | Archived tickets |
| POST | `/tickets/{id}/archive/` | Admin, faculty | Archive an `open` ticket |
| POST | `/tickets/{id}/unarchive/` | Admin, faculty | Restore an archived ticket |
| POST | `/tickets/{id}/reassign/` | Admin | `{"assigned_to": <technician id>}` |

Values: `type` is `report` or `request`; `status` is `open`, `ongoing`, or `resolved`.

List scoping: admins see all tickets; technicians see tickets assigned to them **plus all open tickets**; faculty see tickets they reported. Results are ordered by status (open, ongoing, resolved), then newest first.

Business rules enforced on update: resolved tickets cannot be changed; ongoing tickets cannot return to open; report tickets cannot be resolved manually (they resolve through the repair-log workflow). A request ticket cannot reference a computer.

Ticket changes create notifications, may write request history for resolved request tickets, are audit-logged, and are broadcast to ticket WebSocket groups.

### 5.7 Repair logs and maintenance history

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/repair-logs/` | Admin, technician | List (technicians see their own). Filters: `q`, `date`, `technician_id` |
| POST | `/repair-logs/` | Technician | Create a repair log |
| GET | `/repair-logs/{id}/` | Admin, technician | Detail |
| GET | `/maintenance-history/` | Staff | List. Filters: `type`, `computer-code`, `computer-id`, `technician-id`, `date` |
| GET | `/maintenance-history/{id}/` | Staff | Detail |

A repair log links a ticket and technician, with a generated `RL` code, title, notes, and archive flag. Resolving a report ticket through this workflow marks the ticket resolved, creates a maintenance-history record for the computer, notifies the reporter, writes an audit entry, and broadcasts the ticket update.

Maintenance history types: `repair`, `replace`, `installation`.

### 5.8 Reports

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/reports/` | Admin, technician | List (technicians see their own). Filters: `q`, `date`, `technician_id`, `status` |
| POST | `/reports/` | Admin, technician | Generate a report |
| GET/PUT/PATCH/DELETE | `/reports/{id}/` | Admin, technician | Report detail operations |
| GET | `/reports/test/` | `X-Scheduler-Token` | Trigger monthly report generation |
| POST | `/reports/assignment/` | Admin | Assignment report: `technician_id`, `month_date` |

Report `status` is `read` or `unread`. Report entries are immutable at the model level: technician, code, title, content, and creation time cannot change after creation; only `status` can.

Scheduled generation gathers each technician's non-archived repair logs for the period (last 7 days for weekly, month-to-date for monthly), asks Groq for a summary, stores the report, notifies the technician, and broadcasts it. Technicians with no repair logs in the period are skipped.

### 5.9 Notifications

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/notifications/user/` | Authenticated | Current user's notifications (`cursor`), returns `results` and `next` |
| GET/PUT/PATCH | `/notifications/{id}/` | Admin, owner | Detail / update |
| POST | `/notifications/{id}/read/` | Admin, owner | Mark read for the current user |
| POST | `/notifications/{id}/archive/` | Admin, owner | Archive for the current user |

Notifications reference an `entity_type` (`ticket`, `weekly-report`, `computer`, `user`, `maintenance_history`, `room`, `request_history`, `repair_log`) and `entity_id`. Event types are `multicast-technician`, `multicast-faculty`, `unicast-technician`, `unicast-faculty`. Read and archive state is stored per user as ID lists (`read_by`, `archived_by`).

### 5.10 Request history and audit logs

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/request-history/` | Staff | List; filter `room-id` |
| GET | `/request-history/{id}/` | Staff | Detail |
| GET | `/audit-logs/` | Admin | List (`cursor`, `q`), returns `results` and `next` |

Audit entries store an optional actor, a title, a summary, JSON metadata, and a timestamp. They are written for logins (including failures), profile and password changes, password resets, room/computer operations, chatbot computer lookups, scheduler runs, and ticket/repair activity. New entries are pushed to admins over `/ws/audit-logs/`.

### 5.11 Chatbot ("iLabAssist")

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/chat/` | Technician | `{"message": "..."}`; returns `{"reply": "...", "error": false}` |
| POST | `/chat/reset/` | Technician | Clears the chat session |

Behavior:

- Empty messages are rejected.
- Messages are checked for profanity (English plus `TAGALOG_PROFANITY_WORDS`); flagged messages return `{"reply": "Please keep the conversation professional.", "error": true}`.
- History is kept in the Django session and expires after 20 minutes of inactivity.
- The system prompt is loaded from `prompts/chat-rules.md`; it restricts the assistant to technical troubleshooting and resists prompt injection.
- If the message contains a computer code (`PC` followed by 9 digits) that exists, its specs, room, building, and statuses are added as context and the lookup is audit-logged.
- Groq models are tried in order (`openai/gpt-oss-120b`, `qwen/qwen3.6-27b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`), skipping unavailable or rate-limited ones.

### 5.12 Scheduler

| Method | Endpoint | Access | Description |
|---|---|---|---|
| POST | `/scheduler/` | Admin | Create a schedule |
| GET/PUT/PATCH | `/scheduler/{id}/` | Admin | Retrieve / update |
| GET | `/scheduler/reports/` | `X-Scheduler-Token` | Execute due schedules (intended to be pinged by an external cron) |

Schedule fields: `type`, `enabled`, `frequency` (`once`, `daily`, `weekly`, `monthly`), `weekday`, `monthday`, `execution_time`, `next_execution`, `last_execution`. Next-run times are computed in `Asia/Manila` and stored in UTC. A due `report` schedule runs weekly or monthly report generation. Each run is audit-logged.

### 5.13 Printable templates

| Method | Endpoint | Access | Description |
|---|---|---|---|
| GET | `/templates/` | Admin | List templates |
| POST | `/templates/upload/` | Admin | Upload or replace by `name` and `file` |
| GET | `/templates/{template-name}/` | Authenticated | Active template metadata and URL |
| DELETE | `/templates/{template-name}/delete/` | Admin | Delete record and Cloudinary asset |

Uploads are stored in Cloudinary under `ilabcict/printable-templates/<name>`; re-uploading the same name overwrites the asset.

## 6. WebSocket API

Connect with a JWT access token in the query string:

```text
ws://<host>/ws/tickets/?token=<access-token>
```

Anonymous connections are closed with code `4001`; non-admins on the audit feed are closed with `4003`.

| Route | Description |
|---|---|
| `/ws/tickets/` | Initial tickets, then `ticket_created`, `ticket_updated`, `ticket_deleted`, `ticket_reassigned`, `ticket_archived`, `ticket_unarchived` |
| `/ws/notifications/user/` | Initial notifications, then `notification_created`, `notification_updated`, `notification_archived` |
| `/ws/rooms/` | Initial rooms (optional `include` query param), then room created/updated events |
| `/ws/rooms/{room_id}/computers/` | Room with computers, then computer created/updated/archived/unarchived/transferred events |
| `/ws/reports/` | Report events (`report_created`) |
| `/ws/repair-logs/` | Repair log events (`repair_log_created`) |
| `/ws/audit-logs/` | Admin only: initial logs, then `audit_log_created` |

On connect, consumers send `{"message": "connected"}` followed by an `initial_*` event. Ticket and audit-log sockets answer `{"type": "ping"}` with `{"type": "pong"}`.

Channel groups: `tickets_user_<id>`, `tickets_admin`, `tickets_technicians`, `notification_user_<id>`, `notification_admins`, `notification_technicians`, `rooms_all`, `room_<id>`, `reports_user_<id>`, `reports_admin`, `repair_logs_user_<id>`, `repair_logs_admin`, `audit_logs_admin`.

The configured channel layer is in-memory, so events are delivered only within a single server process.

## 7. Data model summary

| Model | Key fields |
|---|---|
| User | Django user + `user_code` (`US`), unique `email`, `role`, `profile_image` |
| Room | `building_name`, unique `room_name`, `floor_number`, `status`, `assigned_custodian`, `assigned_technician` |
| Computer | `room`, `computer_code` (`PC`), `computer_number`, hardware fields, statuses, `is_archived` |
| Ticket | `ticket_code` (`TK`), `reported_by`, `assigned_to`, `room`, `computer`, `type`, `title`, `complaint_description`, `issue_image`, `status`, `is_archived` |
| RepairLog | `repair_log_code` (`RL`), `ticket`, `technician`, `title`, `repair_notes`, `is_archived` |
| MaintenanceHistory | `maintenance_history_code` (`MH`), `computer`, `technician`, `repair_log`, `maintenance_type`, `maintenance_notes`, `date_performed` |
| RequestHistory | `request_history_code` (`RH`), `room`, `technician`, `ticket`, `date_performed` |
| Report | `report_code` (`RP`), `technician`, `title`, JSON `content`, `status` |
| Notification | `recipient_id`, `entity_type`, `entity_id`, `event_type`, `title`, `activity_summary`, `read_by`, `archived_by` |
| AuditLogs | `performed_by`, `action_title`, `action_summary`, JSON `metadata` |
| TaskScheduler | `type`, `enabled`, `frequency`, `weekday`, `monthday`, `execution_time`, `next_execution`, `last_execution` |
| PrintableTemplate | `name`, `template_url`, `cloudinary_public_id`, `is_active`, `updated_by` |
| UserPushToken | `user`, unique `expo_push_token` |
| OTPCode | `user`, `code_hash`, `expires_at`, `attempts`, `verified_at`, `used_at`, reset-token hash and expiry |

Human-readable codes are generated on first save with retry on collision (up to five attempts).

Relationships: a Room has many Computers; Tickets belong to a Room and optionally a Computer; RepairLogs belong to Tickets; MaintenanceHistory links a Computer, Technician, and optional RepairLog.

## 8. Configuration and integrations

Settings are loaded from environment variables (`.env` via `python-dotenv`).

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DATABASE_URL` | PostgreSQL connection URL |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | Cloudinary credentials |
| `GROQ_API_KEY` | Groq access |
| `TAGALOG_PROFANITY_WORDS` | Comma-separated custom profanity words (required at startup by the chatbot service) |
| `EMAIL_API_KEY` | API key for the external email service |
| `EMAIL_HOST`, `EMAIL_KEY` | Gmail SMTP account and password |
| `BREVO_KEY` | Brevo key (configured in settings) |
| `SCHEDULER_TOKEN` | Expected value of the `X-Scheduler-Token` header |
| `ENV` | `development` uses `http://127.0.0.1:8000` as the API base URL; anything else uses the Render URL |

General settings: time zone `Asia/Manila`, CORS allowed for the deployed web frontends and `http://localhost:5173`, session and CSRF cookies set `SameSite=None; Secure`, and static files served by WhiteNoise.

External services:

- **PostgreSQL (Neon):** primary data store.
- **Cloudinary:** image and template storage.
- **Email service:** a separate HTTP service (`i-lab-cict-email-service.vercel.app`) sends welcome, password-reset-link, and OTP emails, authenticated with `X-API-Key`.
- **Groq:** chatbot and report summarization.

## 9. Running and deployment

Local development:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

A `.env` file with the variables above is required (at minimum `SECRET_KEY` and `DATABASE_URL`; `TAGALOG_PROFANITY_WORDS` must be defined for the chatbot module to import).

The `Procfile` runs:

```text
web: gunicorn ilabcict.wsgi:application
```

WebSockets are served only by the ASGI application (`ilabcict.asgi:application`). To serve WebSocket routes, run an ASGI server such as Daphne or Uvicorn against that module. The WSGI entry point serves HTTP only.

Scheduled reports require an external caller (for example a cron service) to send `GET /api/scheduler/reports/` with the `X-Scheduler-Token` header at regular intervals.

Interactive API documentation is available at `/api/swagger/` and `/api/redoc/`.
