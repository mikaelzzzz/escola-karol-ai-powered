import requests
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurações
ZAIA_API_KEY = os.getenv("ZAIA_API_KEY")
ZAIA_API_URL = os.getenv("ZAIA_API_URL", "https://api.zaia.app")
ZAIA_AGENT_ID = int(os.getenv("ZAIA_AGENT_ID", "34790"))

def test_zaia_api():
    # URL do endpoint
    chat_url = f"{ZAIA_API_URL}/v1/api/external-generative-chat/create"
    
    # Payload
    chat_payload = {
        "agentId": ZAIA_AGENT_ID,
        "userPhone": "+5511999999999",  # Número de teste
        "message": "Olá, teste da API",
        "history": []
    }
    
    # Headers
    headers = {
        "Authorization": f"Bearer {ZAIA_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # Fazer a requisição
        response = requests.post(chat_url, json=chat_payload, headers=headers)
        
        # Imprimir detalhes da resposta
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        print(f"Response Body: {response.text}")
        
        # Verificar se deu erro
        response.raise_for_status()
        
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {str(e)}")

if __name__ == "__main__":
    test_zaia_api() 