"""Cron-driven background scheduler.

Runs the product reindex on a schedule defined by the `REINDEX_PRODUCTS_CRON`
env var (standard 5-field crontab syntax, e.g. ``0 3 * * *`` for daily at
03:00). When the var is unset or empty, no scheduler is started and reindexing
remains purely on-demand via `/admin/reindex-products`.
"""

import asyncio
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.server.services.product_reindex import reindex_products

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _run_reindex_job() -> None:
    """Run the (synchronous, blocking) reindex off the event loop thread."""
    logger.info("Scheduled product reindex starting")
    try:
        stats = await asyncio.to_thread(reindex_products)
        logger.info("Scheduled product reindex finished: %s", stats)
    except Exception:
        logger.exception("Scheduled product reindex failed")


def start_scheduler() -> AsyncIOScheduler | None:
    """Start the reindex scheduler if `REINDEX_PRODUCTS_CRON` is configured.

    Returns the running scheduler, or None when no cron is configured.
    """
    global _scheduler

    cron = os.getenv("REINDEX_PRODUCTS_CRON", "").strip()
    if not cron:
        logger.info("REINDEX_PRODUCTS_CRON not set — product reindex scheduler disabled")
        return None

    timezone = os.getenv("REINDEX_PRODUCTS_TZ", "UTC").strip() or "UTC"

    try:
        trigger = CronTrigger.from_crontab(cron, timezone=timezone)
    except ValueError as e:
        logger.error("Invalid REINDEX_PRODUCTS_CRON %r: %s — scheduler disabled", cron, e)
        return None

    scheduler = AsyncIOScheduler(timezone=timezone)
    scheduler.add_job(
        _run_reindex_job,
        trigger=trigger,
        id="reindex_products",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("Product reindex scheduler started (cron=%r, tz=%s)", cron, timezone)
    return scheduler


def shutdown_scheduler() -> None:
    """Stop the scheduler if it is running."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Product reindex scheduler stopped")
