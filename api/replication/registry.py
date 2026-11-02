"""Reviewed physical public-schema tables. Never extend from an HTTP payload."""

TABLES = (
    "api_user", "api_room", "api_computer", "api_ticket", "api_repairlog",
    "api_maintenancehistory", "api_report", "api_requesthistory", "api_notification",
    "api_taskscheduler", "api_auditlogs", "api_userpushtoken", "api_otpcode",
    "api_printabletemplate", "api_user_groups", "api_user_user_permissions",
    "auth_group", "auth_permission", "auth_group_permissions", "django_content_type",
    "django_admin_log", "django_session",
)

# Different lock namespaces: capture transactions and processors must not block each other.
CAPTURE_LOCK = 73481001
PROCESS_LOCK = 73481002
TRIGGERS = ("ilab_order", "ilab_capture", "ilab_no_truncate")
INFRA_TABLES = ("replication_replicationevent", "replication_appliedreplicationevent", "replication_replicationrun")
