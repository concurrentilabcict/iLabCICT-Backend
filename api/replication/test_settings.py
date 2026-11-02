"""Standalone settings: cannot read .env or connect to Neon. Local disposable PG only."""
SECRET_KEY = "isolated-replication-test-key"
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.admin", "django.contrib.messages", "api", "api.replication",
    "rest_framework",
]
AUTH_USER_MODEL = "api.User"
DATABASES = {
    alias: {"ENGINE": "django.db.backends.postgresql", "HOST": "127.0.0.1", "PORT": "55483",
            "USER": "replication_test", "PASSWORD": "", "NAME": "postgres",
            "OPTIONS": {"connect_timeout": 2}, "TEST": {"NAME": name}}
    for alias, name in (("default", "test_ilab_replication_source"), ("recovery", "test_ilab_replication_target"))
}
USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
ROOT_URLCONF = "api.replication.test_urls"
MIDDLEWARE = []
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request"]}}]
SILENCED_SYSTEM_CHECKS = ["admin.E402", "admin.E404", "admin.E408", "admin.E409", "admin.E410"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
REPLICATION_ENABLED = True
REPLICATION_TOKEN = "test-only-" + "a" * 64
REPLICATION_BATCH_SIZE = 200
REPLICATION_TIME_BUDGET = 10
REPLICATION_MAX_ATTEMPTS = 3
REST_FRAMEWORK = {"UNAUTHENTICATED_USER": None}
