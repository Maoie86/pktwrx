from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from pywebpush import webpush, WebPushException

# Replace these with your actual VAPID keys
VAPID_PUBLIC_KEY = "BBVZvbk7RtjRhAQIprE7raKzbaowE8-O-PMUI4OvywZjqY4iC_zM9ZxhssOj-64oajBca8TpiXC5dCKlg5L8D4c"
VAPID_PRIVATE_KEY = "PTpBz-BB6SaBlpxH_w5IYcbqXzBDzl9Ku6Aud-F0L8M"
VAPID_CLAIMS = {"sub": "mailto:mu.florentino@packetworx.com"}

router = APIRouter()
# logger = logging.getLogger(__name__)

class PushSubscription(BaseModel):
    endpoint: str
    keys: dict

class NotificationPayload(BaseModel):
    title: str
    body: str

@router.post("/send-notification/", tags=['Notification API'])
async def send_notification(subscription: PushSubscription, payload: NotificationPayload):
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.keys["p256dh"],
                    "auth": subscription.keys["auth"],
                },
            },
            data=payload.json(),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS,
        )
        return {"message": "Notification sent successfully"}
    except WebPushException as ex:
        raise HTTPException(status_code=500, detail=f"Web Push failed: {ex}")


