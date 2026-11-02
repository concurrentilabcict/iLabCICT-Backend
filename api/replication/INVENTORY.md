# Approved table inventory

Generated from migration state; verify physical catalogs before Stage B.
## api_user

Primary key: `id` (BigAutoField); sequence-backed: True.
Unique columns: username, email, user_code.
Unique groups: none; constraints: none.
Foreign keys: none.
## api_room

Primary key: `id` (BigAutoField); sequence-backed: True.
Unique columns: room_name.
Unique groups: none; constraints: none.
Foreign keys: `assigned_custodian_id` -> `api_user.id` (Django CASCADE); `assigned_technician_id` -> `api_user.id` (Django CASCADE).
## api_computer

Primary key: `id` (BigAutoField); sequence-backed: True.
Unique columns: computer_code.
Unique groups: none; constraints: [<UniqueConstraint: fields=('room', 'computer_number') name='unique_computer_number_per_room'>].
Foreign keys: `room_id` -> `api_room.id` (Django CASCADE).
## api_ticket

Primary key: `id` (BigAutoField); sequence-backed: True.
Unique columns: ticket_code.
Unique groups: none; constraints: none.
Foreign keys: `assigned_to_id` -> `api_user.id` (Django SET_NULL); `computer_id` -> `api_computer.id` (Django CASCADE); `reported_by_id` -> `api_user.id` (Django CASCADE); `room_id` -> `api_room.id` (Django CASCADE).
## api_repairlog

Primary key: `id` (BigAutoField); sequence-backed: True.
Unique columns: repair_log_code.
Unique groups: none; constraints: none.
Foreign keys: `technician_id` -> `api_user.id` (Django SET_NULL); `ticket_id` -> `api_ticket.id` (Django CASCADE).
## api_maintenancehistory

Primary key: `id` (BigAutoField); sequence-backed: True.
Unique columns: maintenance_history_code.
Unique groups: none; constraints: none.
Foreign keys: `computer_id` -> `api_computer.id` (Django CASCADE); `technician_id` -> `api_user.id` (Django SET_NULL); `repair_log_id` -> `api_repairlog.id` (Django CASCADE).
## api_report

Primary key: `id` (BigAutoField); sequence-backed: True.
Unique columns: report_code.
Unique groups: none; constraints: none.
Foreign keys: `technician_id` -> `api_user.id` (Django SET_NULL).
## api_requesthistory

Primary key: `id` (BigAutoField); sequence-backed: True.
Unique columns: request_history_code.
Unique groups: none; constraints: none.
Foreign keys: `room_id` -> `api_room.id` (Django CASCADE); `technician_id` -> `api_user.id` (Django SET_NULL); `ticket_id` -> `api_ticket.id` (Django CASCADE).
## api_notification

Primary key: `id` (BigAutoField); sequence-backed: True.
Unique columns: none.
Unique groups: none; constraints: none.
Foreign keys: `recipient_id_id` -> `api_user.id` (Django CASCADE).
## api_taskscheduler

Primary key: `id` (BigAutoField); sequence-backed: True.
Unique columns: none.
Unique groups: none; constraints: none.
Foreign keys: none.
## api_auditlogs

Primary key: `id` (BigAutoField); sequence-backed: True.
Unique columns: none.
Unique groups: none; constraints: none.
Foreign keys: `performed_by_id` -> `api_user.id` (Django SET_NULL).
## api_userpushtoken

Primary key: `id` (BigAutoField); sequence-backed: True.
Unique columns: expo_push_token.
Unique groups: none; constraints: none.
Foreign keys: `user_id` -> `api_user.id` (Django CASCADE).
## api_otpcode

Primary key: `id` (BigAutoField); sequence-backed: True.
Unique columns: token_id.
Unique groups: none; constraints: none.
Foreign keys: `user_id` -> `api_user.id` (Django CASCADE).
## api_printabletemplate

Primary key: `id` (BigAutoField); sequence-backed: True.
Unique columns: name.
Unique groups: none; constraints: none.
Foreign keys: `updated_by_id` -> `api_user.id` (Django SET_NULL).
## api_user_groups

Primary key: `id` (BigAutoField); sequence-backed: True.
Unique columns: none.
Unique groups: (('user', 'group'),); constraints: none.
Foreign keys: `user_id` -> `api_user.id` (Django CASCADE); `group_id` -> `auth_group.id` (Django CASCADE).
## api_user_user_permissions

Primary key: `id` (BigAutoField); sequence-backed: True.
Unique columns: none.
Unique groups: (('user', 'permission'),); constraints: none.
Foreign keys: `user_id` -> `api_user.id` (Django CASCADE); `permission_id` -> `auth_permission.id` (Django CASCADE).
## auth_group

Primary key: `id` (AutoField); sequence-backed: True.
Unique columns: name.
Unique groups: none; constraints: none.
Foreign keys: none.
## auth_permission

Primary key: `id` (AutoField); sequence-backed: True.
Unique columns: none.
Unique groups: {('content_type', 'codename')}; constraints: none.
Foreign keys: `content_type_id` -> `django_content_type.id` (Django CASCADE).
## auth_group_permissions

Primary key: `id` (BigAutoField); sequence-backed: True.
Unique columns: none.
Unique groups: (('group', 'permission'),); constraints: none.
Foreign keys: `group_id` -> `auth_group.id` (Django CASCADE); `permission_id` -> `auth_permission.id` (Django CASCADE).
## django_content_type

Primary key: `id` (AutoField); sequence-backed: True.
Unique columns: none.
Unique groups: {('app_label', 'model')}; constraints: none.
Foreign keys: none.
## django_admin_log

Primary key: `id` (AutoField); sequence-backed: True.
Unique columns: none.
Unique groups: none; constraints: none.
Foreign keys: `content_type_id` -> `django_content_type.id` (Django SET_NULL); `user_id` -> `api_user.id` (Django CASCADE).
## django_session

Primary key: `session_key` (CharField); sequence-backed: False.
Unique columns: none.
Unique groups: none; constraints: none.
Foreign keys: none.
