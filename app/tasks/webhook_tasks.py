# app/tasks/webhook_tasks.py
from app.core.celery_app import celery_app
from app.core.cache import redis_client
from celery import states


@celery_app.task(bind=True, max_retries=3)
def process_webhook(self, webhook_data: dict):
    try:
        self.update_state(state=states.STARTED, meta={'status': 'Processing'})
        # Webhook processing logic here
        self.update_state(state=states.SUCCESS, meta={'status': 'Completed'})
    except Exception as exc:
        self.update_state(state=states.FAILURE, meta={'status': 'Failed'})
        self.retry(exc=exc, countdown=60)  # Retry after 1 minute


@celery_app.task
def process_webpixel_event(self, event_data: dict):
    # Rate limiting using Redis
    key = f"rate_limit:{event_data['shop']}"
    if redis_client.incr(key) > 100:  # 100 requests per minute
        return {"status": "rate_limited"}
    redis_client.expire(key, 60)  # Reset after 1 minute

    # Process event
    pass
