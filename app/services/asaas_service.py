from app.core.config import settings
import requests
from typing import Optional, Dict, List
from datetime import datetime

class AsaasService:
    def __init__(self):
        self.api_key = settings.ASAAS_API_KEY
        self.base_url = settings.ASAAS_BASE
        
    def _get_headers(self):
        return {
            "access_token": self.api_key,
            "Content-Type": "application/json"
        }
        
    async def buscar_cliente(self, aluno: Dict) -> Optional[str]:
        """
        Busca um cliente no Asaas usando CPF ou email
        Retorna o ID do cliente se encontrado
        """
        try:
            # Tentar buscar por CPF primeiro
            if aluno.get("cpf"):
                cpf = ''.join(filter(str.isdigit, aluno["cpf"]))
                url = f"{self.base_url}/customers?cpfCnpj={cpf}"
                resp = requests.get(url, headers=self._get_headers())
                resp.raise_for_status()
                data = resp.json()
                
                if data.get("data"):
                    return data["data"][0]["id"]
            
            # Se não encontrou por CPF, tentar por email
            if aluno.get("email"):
                url = f"{self.base_url}/customers?email={aluno['email']}"
                resp = requests.get(url, headers=self._get_headers())
                resp.raise_for_status()
                data = resp.json()
                
                if data.get("data"):
                    return data["data"][0]["id"]
            
            return None
            
        except Exception as e:
            print(f"Erro ao buscar cliente no Asaas: {str(e)}")
            return None
            
    async def buscar_cobrancas_por_customer_id(self, customer_id: str) -> Optional[List[Dict]]:
        """
        Busca cobranças de um cliente pelo ID
        """
        try:
            url_payments = f"{self.base_url}/payments?customer={customer_id}"
            resp_payments = requests.get(
                url_payments,
                headers=self._get_headers()
            )
            resp_payments.raise_for_status()
            
            data_payments = resp_payments.json()
            
            # Formatar as cobranças
            cobrancas = []
            for payment in data_payments.get("data", []):
                cobrancas.append({
                    "id": payment["id"],
                    "valor": payment["value"],
                    "vencimento": payment["dueDate"],
                    "status": payment["status"],
                    "link": payment.get("invoiceUrl", ""),
                    "codigo_barras": payment.get("bankSlipUrl", "")
                })
                
            return cobrancas
            
        except Exception as e:
            print(f"Erro ao buscar cobranças no Asaas: {str(e)}")
            return None
            
    async def buscar_proxima_cobranca(self, aluno: Dict) -> Optional[Dict]:
        """
        Busca a próxima cobrança em aberto do cliente
        Tenta encontrar o cliente por CPF ou email
        """
        try:
            # Buscar o ID do cliente
            customer_id = await self.buscar_cliente(aluno)
            if not customer_id:
                return None
                
            # Buscar cobranças do cliente
            cobrancas = await self.buscar_cobrancas_por_customer_id(customer_id)
            if not cobrancas:
                return None
                
            # Filtrar cobranças em aberto e ordenar por data de vencimento
            cobrancas_abertas = [
                c for c in cobrancas 
                if c["status"] in ["PENDING", "RECEIVED"] and 
                datetime.strptime(c["vencimento"], "%Y-%m-%d") >= datetime.now()
            ]
            
            if not cobrancas_abertas:
                return None
                
            # Retornar a cobrança mais próxima
            return min(
                cobrancas_abertas,
                key=lambda x: datetime.strptime(x["vencimento"], "%Y-%m-%d")
            )
            
        except Exception as e:
            print(f"Erro ao buscar próxima cobrança no Asaas: {str(e)}")
            return None 