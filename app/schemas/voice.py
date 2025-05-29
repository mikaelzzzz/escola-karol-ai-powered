from pydantic import BaseModel

class VoiceRequest(BaseModel):
    text: str

class VoiceResponse(BaseModel):
    audio: bytes 