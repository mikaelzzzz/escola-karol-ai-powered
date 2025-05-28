from pydantic import BaseModel

class GramaticaRequest(BaseModel):
    numero: str
    texto: str 