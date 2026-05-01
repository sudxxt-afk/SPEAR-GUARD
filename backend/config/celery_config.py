from celery import Celery
from celery.schedules import crontab
import os
import logging

logger = logging.getLogger(__name__)

# Get configuration from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# Create Celery application
celery_app = Celery(
    "spearguard",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "tasks.registry_tasks",
        "tasks.mail_sync",
        "tasks.analysis_tasks",
        "tasks.threat_intel_tasks",   # Threat Intelligence periodic sync
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3000,  # 50 minutes soft limit

    # Result backend settings
    result_expires=86400,  # Results expire after 24 hours
    result_backend_transport_options={
        "master_name": "mymaster",
        "visibility_timeout": 3600,
    },

    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,

    # Beat scheduler settings (for periodic tasks)
    beat_schedule={
        # Auto-populate registry from historical emails (daily at 2 AM)
        "auto-populate-registry-daily": {
            "task": "tasks.registry_tasks.auto_populate_registry_task",
            "schedule": crontab(hour=2, minute=0),  # 02:00 every day
            "kwargs": {
                "months_back": 6,
                "min_emails": 10,
                "min_reply_rate": 30.0,
                "dry_run": False
            },
            "options": {
                "expires": 3600,  # Task expires if not executed within 1 hour
            }
        },

        # Update trust scores for existing entries (daily at 3 AM)
        "update-trust-scores-daily": {
            "task": "tasks.registry_tasks.update_trust_scores_task",
            "schedule": crontab(hour=3, minute=0),  # 03:00 every day
            "options": {
                "expires": 3600,
            }
        },

        # Import from Active Directory (weekly on Monday at 1 AM)
        "import-ad-weekly": {
            "task": "tasks.registry_tasks.import_from_ad_task",
            "schedule": crontab(hour=1, minute=0, day_of_week=1),  # Monday 01:00
            "kwargs": {
                "organizations": None,  # Import all organizations
                "dry_run": False
            },
            "options": {
                "expires": 7200,  # 2 hours
            }
        },

        # Import from EGRUL (monthly on 1st day at 1 AM)
        "import-egrul-monthly": {
            "task": "tasks.registry_tasks.import_from_egrul_task",
            "schedule": crontab(hour=1, minute=0, day_of_month=1),  # 1st day of month 01:00
            "kwargs": {
                "min_contract_count": 5,
                "dry_run": False
            },
            "options": {
                "expires": 7200,
            }
        },

        # Monitor user mail accounts (every 5 minutes)
        "monitor-mail-accounts": {
            "task": "tasks.mail_sync.monitor_all_accounts",
            "schedule": 300.0,  # Every 5 minutes (300 seconds)
            "options": {
                "expires": 240,  # Expire before next run
            }
        },

        # Threat Intelligence: sync feeds every 15 minutes
        "threat-intel-sync": {
            "task": "tasks.threat_intel.sync_threat_intel",
            "schedule": 900.0,  # Every 15 minutes
            "options": {
                "expires": 600,  # Expire if not done before next run
            }
        },

        # Threat Intelligence: cleanup expired entries every 6 hours
        "threat-intel-cleanup": {
            "task": "tasks.threat_intel.cleanup_expired_ti",
            "schedule": crontab(minute=0),  # Top of every hour
            "options": {
                "expires": 3600,
            }
        },
    },

    # Logging
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s",
)

logger.info(f"Celery configured with broker: {CELERY_BROKER_URL}")
