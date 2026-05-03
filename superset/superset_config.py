import os

SECRET_KEY = "travel-analytics-platform-superset-2026"

SQLALCHEMY_DATABASE_URI = (
    f"postgresql+psycopg2://"
    f"{os.environ.get('DB_USER', 'superset')}:"
    f"{os.environ.get('DB_PASS', 'superset')}@"
    f"{os.environ.get('DB_HOST', 'db')}:5432/"
    f"{os.environ.get('DB_NAME', 'superset')}"
)

_REDIS = f"redis://{os.environ.get('REDIS_HOST', 'redis')}:6379/0"

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_URL": _REDIS,
}
DATA_CACHE_CONFIG = {**CACHE_CONFIG, "CACHE_KEY_PREFIX": "superset_data_"}

SQLLAB_TIMEOUT = 300
SUPERSET_WEBSERVER_TIMEOUT = 300

FEATURE_FLAGS = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "EMBEDDED_SUPERSET": True,
}

GUEST_TOKEN_JWT_SECRET = "travel-analytics-guest-secret-2026"
GUEST_ROLE_NAME = "Public"
PUBLIC_ROLE_LIKE = "Gamma"

# Allow embedding in iframes from any origin
HTTP_HEADERS = {}
TALISMAN_CONFIG = {
    "content_security_policy": False,
    "force_https": False,
    "session_cookie_secure": False,
    "frame_options": "ALLOWALL",
}
