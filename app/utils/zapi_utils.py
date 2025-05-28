import requests
from app.core.config import settings

def enviar_mensagem_zapi(numero, mensagem):
    """
    Envia uma mensagem de texto via Z-API.
    """
    url = f"https://api.z-api.io/instances/{settings.ZAPI_INSTANCE_ID}/token/{settings.ZAPI_TOKEN}/send-text"
    payload = {
        "phone": numero,
        "message": mensagem
    }
    headers = {
        "Content-Type": "application/json",
        "Client-Token": settings.ZAPI_SECURITY_TOKEN,
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"Mensagem enviada para {numero}")
    else:
        print(f"Erro ao enviar mensagem para {numero}: {response.text}")

def enviar_audio_zapi(numero, audio_bytes):
    """
    Envia um áudio (mp3) via Z-API.
    """
    url = f"https://api.z-api.io/instances/{settings.ZAPI_INSTANCE_ID}/token/{settings.ZAPI_TOKEN}/send-audio"
    files = {
        "audio": ("resposta.mp3", audio_bytes, "audio/mpeg")
    }
    data = {
        "phone": numero
    }
    headers = {
        "Client-Token": settings.ZAPI_SECURITY_TOKEN,
    }
    response = requests.post(url, headers=headers, data=data, files=files)
    if response.status_code == 200:
        print(f"Áudio enviado para {numero}")
    else:
        print(f"Erro ao enviar áudio para {numero}: {response.text}")        

