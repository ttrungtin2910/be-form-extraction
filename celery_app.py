import os
import sys
from celery import Celery
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def make_celery() -> Celery:
    """Create and configure a Celery application instance.

    Broker & result backend default to local Redis (docker-compose up -d redis).
    Override via REDIS_URL env variable.
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    app = Celery(
        "form_queue",
        broker=redis_url,
        backend=redis_url,
        include=["tasks"],
    )
    app.conf.update(
        task_track_started=True,
        result_expires=3600,  # 1 hour
        worker_send_task_events=True,
        task_send_sent_event=True,
    )

    # ---- Python 3.13 compatibility fallback ----
    # Celery / billiard có thể chưa ổn định trên 3.13 với prefork.
    # Tự động chuyển sang 'solo' nếu:
    #  - PYTHON >= 3.13 hoặc
    #  - đặt biến CELERY_FORCE_SOLO=1
    explicit_pool = os.getenv("CELERY_POOL")
    force_solo = os.getenv("CELERY_FORCE_SOLO") == "1" or (
        sys.version_info >= (3, 13) and not explicit_pool
    )
    if force_solo and not explicit_pool:
        # 'worker_pool' cấu hình nội bộ; tương đương tham số -P solo
        app.conf.worker_pool = "solo"
        os.environ.setdefault("CELERYD_FORCE_EXECV", "0")
    return app


celery_app = make_celery()

if celery_app.conf.get("worker_pool") == "solo":
    print(
        f"[Celery] Using SOLO pool (Python {sys.version_info.major}.{sys.version_info.minor}). Set CELERY_FORCE_SOLO=0 and use Python 3.12 for prefork."
    )
