"""
order_service/sqs_publisher.py
Publishes OrderPlaced and OrderCancelled event messages to AWS SQS queue.

Environment variables:
  SQS_QUEUE_URL          — Full SQS queue URL
  INVENTORY_SERVICE_URL  — Base URL for Inventory Service (default: http://localhost:8004)
  AWS_REGION             — AWS region (default: eu-west-1)

Fallback Mechanism:
  If SQS_QUEUE_URL is not configured or AWS credentials/SQS publishing fails,
  it makes direct HTTP requests to the Inventory Service fallback endpoint or restock API
  to guarantee data consistency in local dev/testing environments.
"""

import json
import logging
import os
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
import requests

logger = logging.getLogger("order_service.sqs")

AWS_REGION: str = os.environ.get("AWS_REGION", "eu-west-1")
SQS_QUEUE_URL: Optional[str] = os.environ.get("SQS_QUEUE_URL")
INVENTORY_SERVICE_URL: str = os.environ.get("INVENTORY_SERVICE_URL", "http://localhost:8004")


def _get_sqs_client():
    return boto3.client("sqs", region_name=AWS_REGION)


def _http_fallback_order_placed(order_id: int, user_id: int, items: list) -> bool:
    """
    Makes a standard HTTP POST request to local Inventory Service fallback endpoint
    when SQS is not available.
    """
    url = f"{INVENTORY_SERVICE_URL.rstrip('/')}/events/order-placed"
    payload = {
        "order_id": order_id,
        "user_id": user_id,
        "items": items,
    }
    logger.warning(
        "[SQS Fallback] AWS credentials/Queue not configured. Making HTTP POST to %s for order #%d",
        url, order_id,
    )
    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            logger.info(
                "[SQS Fallback HTTP] Successfully delivered OrderPlaced event to Inventory Service for order #%d",
                order_id,
            )
            return True
        else:
            logger.error(
                "[SQS Fallback HTTP] Failed with status %d: %s",
                resp.status_code, resp.text,
            )
            return False
    except Exception as err:
        logger.error(
            "[SQS Fallback HTTP] Error calling Inventory Service fallback endpoint: %s",
            err,
        )
        return False


def _http_fallback_order_cancelled(order_id: int, items: list) -> bool:
    """
    Compensating Saga Transaction: HTTP fallback restock for cancelled order items.
    """
    logger.warning(
        "[SQS Fallback] Restocking items via HTTP fallback for cancelled order #%d",
        order_id,
    )
    success = True
    for item in items:
        product_id = item.get("product_id") if isinstance(item, dict) else getattr(item, "product_id", None)
        quantity = item.get("quantity") if isinstance(item, dict) else getattr(item, "quantity", 0)
        if product_id and quantity > 0:
            url = f"{INVENTORY_SERVICE_URL.rstrip('/')}/inventory/{product_id}/restock?quantity={quantity}"
            try:
                resp = requests.patch(url, timeout=5)
                if resp.status_code == 200:
                    logger.info(
                        "[Saga Compensating Tx] Successfully restocked %d unit(s) of product #%d (order #%d cancelled)",
                        quantity, product_id, order_id,
                    )
                else:
                    logger.error(
                        "[Saga Compensating Tx] Restock failed for product #%d (status %d): %s",
                        product_id, resp.status_code, resp.text,
                    )
                    success = False
            except Exception as err:
                logger.error(
                    "[Saga Compensating Tx] Error calling restock endpoint for product #%d: %s",
                    product_id, err,
                )
                success = False
    return success


def publish_order_placed_event(order_id: int, user_id: int, items: list) -> bool:
    """
    Sends an OrderPlacedEvent JSON message to the configured SQS queue.
    If SQS is missing or fails, triggers HTTP fallback logic.
    """
    if not SQS_QUEUE_URL:
        return _http_fallback_order_placed(order_id, user_id, items)

    message_body = json.dumps({
        "event_type": "OrderPlaced",
        "order_id": order_id,
        "user_id": user_id,
        "items": items,
    })

    try:
        sqs = _get_sqs_client()
        response = sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=message_body,
            MessageAttributes={
                "event_type": {
                    "DataType": "String",
                    "StringValue": "OrderPlaced",
                }
            },
        )
        logger.info(
            "[SQS] OrderPlaced event published for order #%d. MessageId: %s",
            order_id, response.get("MessageId", "unknown"),
        )
        return True

    except (NoCredentialsError, BotoCoreError, ClientError) as exc:
        logger.warning(
            "[SQS] SQS publish failed for order #%d (%s). Falling back to HTTP.",
            order_id, exc,
        )
        return _http_fallback_order_placed(order_id, user_id, items)


def publish_order_cancelled_event(order_id: int, items: list) -> bool:
    """
    Sends an OrderCancelled event message to SQS or performs HTTP compensating restock.
    """
    if not SQS_QUEUE_URL:
        return _http_fallback_order_cancelled(order_id, items)

    message_body = json.dumps({
        "event_type": "OrderCancelled",
        "order_id": order_id,
        "items": items,
    })

    try:
        sqs = _get_sqs_client()
        response = sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=message_body,
            MessageAttributes={
                "event_type": {
                    "DataType": "String",
                    "StringValue": "OrderCancelled",
                }
            },
        )
        logger.info(
            "[SQS] OrderCancelled event published for order #%d. MessageId: %s",
            order_id, response.get("MessageId", "unknown"),
        )
        return True

    except (NoCredentialsError, BotoCoreError, ClientError) as exc:
        logger.warning(
            "[SQS] OrderCancelled publish failed for order #%d (%s). Falling back to HTTP restock.",
            order_id, exc,
        )
        return _http_fallback_order_cancelled(order_id, items)
