"""
inventory_service/sqs_consumer.py
Background SQS long-polling worker for the Inventory Service.

Runs as a daemon thread started during FastAPI's startup event.
Continuously polls the SmartRetailX-OrderEvents SQS queue and deducts stock
when OrderPlaced messages arrive.

Environment variables:
  SQS_QUEUE_URL  — Full SQS queue URL
  AWS_REGION     — AWS region (default: eu-west-1)

When SQS_QUEUE_URL is not set, the worker logs a warning and exits immediately —
the service starts normally for local testing without AWS configured.
"""

import json
import logging
import os
import threading
import time

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from inventory_service.database import SessionLocal
from inventory_service.models import InventoryItem

logger = logging.getLogger("inventory_service.sqs_consumer")

AWS_REGION: str = os.environ.get("AWS_REGION", "eu-west-1")
SQS_QUEUE_URL: str | None = os.environ.get("SQS_QUEUE_URL")

_MAX_BACKOFF: int = 60


def _process_order_placed_event(body: dict, db) -> None:
    """
    Deducts stock for each item listed in an OrderPlaced event body.
    Commits per-item so partial deductions are persisted even on mid-event errors.
    """
    order_id = body.get("order_id", "?")
    items = body.get("items", [])
    logger.info("Processing OrderPlaced event for order #%s (%d items)", order_id, len(items))

    for item in items:
        product_id = item.get("product_id")
        quantity = item.get("quantity", 0)

        if not product_id or quantity <= 0:
            logger.warning("Skipping malformed item in order #%s: %s", order_id, item)
            continue

        inv = db.query(InventoryItem).filter(InventoryItem.product_id == product_id).first()
        if inv is None:
            logger.warning(
                "No inventory record for product #%d in order #%s — skipping deduction.",
                product_id, order_id,
            )
            continue

        if inv.stock_quantity < quantity:
            logger.warning(
                "Insufficient stock for product #%d (order #%s): have %d, need %d.",
                product_id, order_id, inv.stock_quantity, quantity,
            )
            continue

        inv.stock_quantity -= quantity
        db.commit()
        logger.info(
            "Deducted %d unit(s) of product #%d (order #%s). Remaining: %d.",
            quantity, product_id, order_id, inv.stock_quantity,
        )


def _process_order_cancelled_event(body: dict, db) -> None:
    """
    Restocks inventory items when an OrderCancelled event body is received.
    """
    order_id = body.get("order_id", "?")
    items = body.get("items", [])
    logger.info("Processing OrderCancelled event for order #%s (%d items)", order_id, len(items))

    for item in items:
        product_id = item.get("product_id")
        quantity = item.get("quantity", 0)

        if not product_id or quantity <= 0:
            continue

        inv = db.query(InventoryItem).filter(InventoryItem.product_id == product_id).first()
        if inv is None:
            logger.warning(
                "No inventory record for product #%d in cancelled order #%s.",
                product_id, order_id,
            )
            continue

        inv.stock_quantity += quantity
        db.commit()
        logger.info(
            "Restocked %d unit(s) of product #%d (order #%s cancelled). New stock: %d.",
            quantity, product_id, order_id, inv.stock_quantity,
        )


def _get_sqs_client():
    aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    aws_region = os.environ.get("AWS_REGION", "eu-west-1")

    kwargs = {"region_name": aws_region}
    if aws_access_key and aws_secret_key:
        kwargs["aws_access_key_id"] = aws_access_key
        kwargs["aws_secret_access_key"] = aws_secret_key

    return boto3.client("sqs", **kwargs)


def _poll_loop() -> None:
    """Main SQS polling loop — runs in a daemon thread."""
    if not SQS_QUEUE_URL:
        logger.warning(
            "[SQS Consumer] Queue URL missing. Consumer idle (waiting for AWS configuration). "
            "Set SQS_QUEUE_URL environment variable to enable real-time order event processing. "
            "Use POST /events/order-placed for local testing."
        )
        return

    logger.info("[SQS Consumer] Starting. Polling: %s", SQS_QUEUE_URL)
    sqs = _get_sqs_client()
    backoff = 2

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,
                MessageAttributeNames=["All"],
                VisibilityTimeout=30,
            )
            backoff = 2

            messages = response.get("Messages", [])
            if not messages:
                continue

            db = SessionLocal()
            try:
                for msg in messages:
                    receipt_handle = msg["ReceiptHandle"]
                    try:
                        body = json.loads(msg["Body"])
                        event_type = body.get("event_type")
                        if event_type == "OrderPlaced":
                            _process_order_placed_event(body, db)
                        elif event_type == "OrderCancelled":
                            _process_order_cancelled_event(body, db)
                        else:
                            logger.debug("Ignoring event type: %s", event_type)
                        sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt_handle)
                    except (json.JSONDecodeError, KeyError) as parse_err:
                        logger.error("Failed to parse SQS message: %s — %s", msg.get("Body"), parse_err)
                        sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt_handle)
            finally:
                db.close()

        except (BotoCoreError, ClientError) as aws_err:
            logger.error("[SQS Consumer] AWS error: %s — retrying in %ds", aws_err, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, _MAX_BACKOFF)
        except Exception as unexpected:
            logger.exception("[SQS Consumer] Unexpected error: %s", unexpected)
            time.sleep(backoff)
            backoff = min(backoff * 2, _MAX_BACKOFF)


def start_consumer_thread() -> threading.Thread:
    """Starts the SQS polling loop as a background daemon thread."""
    thread = threading.Thread(target=_poll_loop, name="sqs-consumer", daemon=True)
    thread.start()
    return thread
