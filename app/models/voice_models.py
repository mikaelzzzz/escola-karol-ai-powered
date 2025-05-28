from pydantic import BaseModel

class VoiceRequest(BaseModel):
    numero: str
    texto: str 