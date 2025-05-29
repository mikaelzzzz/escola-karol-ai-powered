from app.core.config import settings
import requests
import json
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class NotionService:
    def __init__(self):
        self.api_key = settings.NOTION_API_KEY
        self.database_id = settings.NOTION_DATABASE_ID
        self.base_url = "https://api.notion.com/v1"
        
    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
    async def buscar_aluno_por_whatsapp(self, phone: str) -> Optional[Dict]:
        """
        Busca dados do aluno pelo número do WhatsApp no banco do Notion
        """
        try:
            # Formatar número para garantir consistência (remover caracteres especiais)
            phone_formatted = ''.join(filter(str.isdigit, phone))
            logger.info(f"Buscando aluno no Notion com telefone: {phone} -> formatado: {phone_formatted}")
            
            # Construir a query para o Notion
            url = f"{self.base_url}/databases/{self.database_id}/query"
            payload = {
                "filter": {
                    "property": "Telefone",
                    "rich_text": {
                        "contains": phone_formatted
                    }
                }
            }
            
            logger.debug(f"URL da consulta: {url}")
            logger.debug(f"Payload da consulta: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload
            )
            
            logger.info(f"Status da resposta: {response.status_code}")
            logger.debug(f"Resposta completa: {response.text}")
            
            response.raise_for_status()
            
            data = response.json()
            if not data.get("results"):
                logger.info("Nenhum resultado encontrado no Notion")
                return None
                
            # Pegar o primeiro resultado
            student = data["results"][0]
            properties = student.get("properties", {})
            
            logger.debug(f"Propriedades encontradas: {list(properties.keys())}")
            
            # Extrair dados com tratamento de erro para cada campo
            def get_rich_text_content(prop_name):
                try:
                    rich_text = properties.get(prop_name, {}).get("rich_text", [])
                    return rich_text[0].get("text", {}).get("content", "") if rich_text else ""
                except (IndexError, KeyError, TypeError):
                    logger.warning(f"Erro ao extrair {prop_name}")
                    return ""
                    
            def get_title_content(prop_name):
                try:
                    title = properties.get(prop_name, {}).get("title", [])
                    return title[0].get("text", {}).get("content", "") if title else ""
                except (IndexError, KeyError, TypeError):
                    logger.warning(f"Erro ao extrair {prop_name}")
                    return ""
                    
            def get_select_name(prop_name):
                try:
                    select = properties.get(prop_name, {}).get("select", {})
                    return select.get("name", "") if select else ""
                except (KeyError, TypeError):
                    logger.warning(f"Erro ao extrair {prop_name}")
                    return ""
            
            # Mapear os dados do aluno com os campos corretos
            aluno_data = {
                "id": student.get("id", ""),
                "nome": get_title_content("Student Name"),
                "email": properties.get("Email", {}).get("email", ""),
                "telefone": get_rich_text_content("Telefone"),
                "cpf": get_rich_text_content("CPF"),
                "plano": get_select_name("Plano"),
                "endereco": get_rich_text_content("Endereço Completo"),
                "nivel": get_select_name("Nível"),
                "status": get_select_name("Status")
            }
            
            logger.info(f"Dados do aluno extraídos com sucesso: {aluno_data['nome']}")
            return aluno_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição ao Notion: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar aluno no Notion: {str(e)}")
            return None
            
    async def buscar_aluno_por_email(self, email: str) -> Optional[Dict]:
        """
        Busca um aluno no banco de dados do Notion pelo email
        """
        try:
            url = f"{self.base_url}/databases/{self.database_id}/query"
            payload = {
                "filter": {
                    "property": "Email",
                    "email": {
                        "equals": email.lower()
                    }
                }
            }
            
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            if not data.get("results"):
                logger.info(f"Nenhum aluno encontrado com o email: {email}")
                return None
                
            # Pegar o primeiro resultado
            student = data["results"][0]
            properties = student.get("properties", {})
            
            # Extrair dados com tratamento de erro para cada campo
            def get_rich_text_content(prop_name):
                try:
                    rich_text = properties.get(prop_name, {}).get("rich_text", [])
                    return rich_text[0].get("text", {}).get("content", "") if rich_text else ""
                except (IndexError, KeyError, TypeError):
                    logger.warning(f"Erro ao extrair {prop_name}")
                    return ""
                    
            def get_title_content(prop_name):
                try:
                    title = properties.get(prop_name, {}).get("title", [])
                    return title[0].get("text", {}).get("content", "") if title else ""
                except (IndexError, KeyError, TypeError):
                    logger.warning(f"Erro ao extrair {prop_name}")
                    return ""
                    
            def get_select_name(prop_name):
                try:
                    select = properties.get(prop_name, {}).get("select", {})
                    return select.get("name", "") if select else ""
                except (KeyError, TypeError):
                    logger.warning(f"Erro ao extrair {prop_name}")
                    return ""
            
            # Mapear os dados do aluno com os campos corretos
            aluno_data = {
                "id": student.get("id", ""),
                "nome": get_title_content("Student Name"),
                "email": properties.get("Email", {}).get("email", ""),
                "telefone": get_rich_text_content("Telefone"),
                "cpf": get_rich_text_content("CPF"),
                "plano": get_select_name("Plano"),
                "endereco": get_rich_text_content("Endereço Completo"),
                "nivel": get_select_name("Nível"),
                "status": get_select_name("Status")
            }
            
            logger.info(f"Dados do aluno extraídos com sucesso: {aluno_data['nome']}")
            return aluno_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição ao Notion: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar aluno no Notion: {str(e)}")
            return None 