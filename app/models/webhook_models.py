from pydantic import BaseModel

class WebhookPayload(BaseModel):
    from_: str
    type: str
    body: str = None
    audio_url: str = None
    image_url: str = None 