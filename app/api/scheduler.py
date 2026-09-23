import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.run import run_once

log = logging.getLogger("linkedin_agent.scheduler")
_scheduler = BackgroundScheduler()

def scheduled_job():
    log.info("Running scheduled job...")
    try:
        run_once()
        log.info("Scheduled job completed.")
    except Exception as e:
        log.error(f"Scheduled job failed: {e}")

def start_scheduler():
    settings = get_settings()
    
    # schedule_time format: "HH:MM"
    time_parts = settings.schedule_time.split(":")
    hour = int(time_parts[0]) if len(time_parts) > 0 else 8
    minute = int(time_parts[1]) if len(time_parts) > 1 else 0
    
    trigger = CronTrigger(hour=hour, minute=minute, timezone=settings.timezone)
    _scheduler.add_job(scheduled_job, trigger=trigger)
    _scheduler.start()
    log.info(f"Scheduler started. Next run at {hour:02d}:{minute:02d} {settings.timezone}")

def stop_scheduler():
    _scheduler.shutdown()
    log.info("Scheduler stopped.")
