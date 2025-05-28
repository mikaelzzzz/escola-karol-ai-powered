from pydantic import BaseModel
from typing import Optional, Dict, Any

class WebhookPayload(BaseModel):
    phone: str
    type: str
    text: Optional[str] = None
    audio: Optional[Dict[str, Any]] = None
    image: Optional[Dict[str, Any]] = None
    document: Optional[Dict[str, Any]] = None
    instanceId: Optional[str] = None
    messageId: Optional[str] = None
    timestamp: Optional[int] = None 