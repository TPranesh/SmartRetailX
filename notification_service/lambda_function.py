import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    AWS Lambda Handler for processing incoming SQS/SNS Order Event notifications.
    Simulates email and SMS dispatch for SmartRetailX order events.
    """
    records = event.get('Records', [])
    logger.info(f"Notification Service triggered with {len(records)} record(s).")
    
    processed_count = 0
    for record in records:
        body_str = record.get('body', '{}')
        try:
            body = json.loads(body_str)
        except Exception:
            body = {"raw_message": body_str}
        
        event_type = body.get('event_type', 'ORDER_EVENT')
        order_id = body.get('order_id', 'UNKNOWN')
        user_email = body.get('user_email', 'customer@smartretailx.com')
        total_amount = body.get('total_amount', 0.0)
        
        logger.info(
            f"[MOCK DISPATCH SUCCESS] Event: {event_type} | "
            f"Order ID: {order_id} | Total: ${total_amount} | "
            f"Notification dispatched via Email/SMS to: {user_email}"
        )
        processed_count += 1

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Notifications processed successfully',
            'processed_count': processed_count
        })
    }
