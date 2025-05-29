from app.utils.zapi_utils import enviar_mensagem_zapi, enviar_audio_zapi
from app.core.config import settings
from app.services.voice_service import text_to_speech
from app.services.notion_service import NotionService
import requests
import json
from typing import Dict, Optional, Tuple
from app.services.flexge_service import FlexgeService
from app.services.asaas_service import AsaasService
import base64
import openai
import logging

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.instance = settings.ZAPI_INSTANCE_ID
        self.token = settings.ZAPI_TOKEN
        self.base_url = f"https://api.z-api.io/instances/{self.instance}/token/{self.token}"
        self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.notion_service = NotionService()
        
    async def processar_webhook(self, webhook_data: Dict) -> Dict:
        """
        Processa webhook do Z-API
        """
        try:
            phone = webhook_data.get("phone", "")
            message_type = webhook_data.get("type", "")
            message = ""
            contexto = None
            
            # Buscar dados do aluno no Notion
            aluno = await self.notion_service.buscar_aluno_por_whatsapp(phone)
            if not aluno:
                return {
                    "error": "Aluno não encontrado",
                    "message": "Desculpe, não consegui identificar seu cadastro. Por favor, entre em contato com a secretaria."
                }
            
            # Processar diferentes tipos de mensagem
            if message_type == "message":
                message = webhook_data.get("text", "")
            elif message_type == "audio":
                audio_url = webhook_data.get("audio", {}).get("url")
                if not audio_url:
                    return {"error": "URL do áudio não encontrada"}
                message = await self.transcrever_audio(audio_url)
            elif message_type in ["image", "document"]:
                url = webhook_data.get(message_type, {}).get("url")
                if not url:
                    return {"error": f"URL do {message_type} não encontrada"}
                message, contexto = await self.extrair_texto_midia(url, message_type)
            else:
                return {"error": "Tipo de mensagem não suportado"}
                
            return {
                "phone": phone,
                "message": message,
                "type": message_type,
                "contexto": contexto,
                "aluno": aluno
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar webhook: {str(e)}")
            return {"error": str(e)}

    async def extrair_texto_midia(self, url: str, tipo: str) -> Tuple[str, str]:
        """
        Extrai texto de imagens ou documentos usando GPT-4 Vision e identifica o contexto
        Retorna uma tupla (texto_extraido, contexto)
        """
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text", 
                                "text": """Analise esta imagem/documento e me diga:
                                1. Que tipo de documento é este? (comprovante de pagamento, screenshot de erro, etc)
                                2. Extraia as informações relevantes.
                                3. Se for um comprovante de pagamento, extraia: valor, data, tipo de pagamento
                                4. Se for um screenshot de erro do Flexge, extraia: tipo de erro, mensagem de erro, contexto
                                Responda em formato JSON com as chaves: tipo_documento, informacoes_extraidas"""
                            },
                            {
                                "type": "image_url",
                                "image_url": url,
                            },
                        ],
                    }
                ],
                max_tokens=500,
            )
            
            # Tentar parsear a resposta como JSON
            try:
                analise = json.loads(response.choices[0].message.content)
                tipo_documento = analise.get("tipo_documento", "").lower()
                informacoes = analise.get("informacoes_extraidas", {})
                
                if "comprovante" in tipo_documento or "pagamento" in tipo_documento:
                    texto_formatado = f"""Comprovante de Pagamento:
                    Valor: {informacoes.get('valor', 'não identificado')}
                    Data: {informacoes.get('data', 'não identificada')}
                    Tipo: {informacoes.get('tipo_pagamento', 'não identificado')}"""
                    return texto_formatado, "comprovante_pagamento"
                    
                elif "erro" in tipo_documento or "screenshot" in tipo_documento:
                    texto_formatado = f"""Erro no Flexge:
                    Tipo: {informacoes.get('tipo_erro', 'não identificado')}
                    Mensagem: {informacoes.get('mensagem_erro', 'não identificada')}
                    Contexto: {informacoes.get('contexto', 'não identificado')}"""
                    return texto_formatado, "erro_flexge"
                    
                else:
                    return response.choices[0].message.content, "outro"
                    
            except json.JSONDecodeError:
                return response.choices[0].message.content, "outro"
                
        except Exception as e:
            logger.error(f"Erro ao extrair texto da mídia: {str(e)}")
            return f"Recebi seu {tipo}, mas não consegui analisar o conteúdo. Pode me explicar do que se trata?", "erro"
            
    async def process_with_zaia(self, message: str, aluno: Optional[Dict] = None, contexto: Optional[str] = None, phone: Optional[str] = None) -> Tuple[str, bool]:
        """
        Processa mensagem com a Zaia e retorna resposta contextualizada
        Retorna uma tupla (resposta, usar_audio)
        """
        try:
            # Se tiver contexto específico, tratar adequadamente
            if contexto == "comprovante_pagamento":
                return await self.processar_comprovante_pagamento(message, aluno), False
            elif contexto == "erro_flexge":
                return await self.processar_erro_flexge(message, aluno), False
            
            # Identificar intenção da mensagem
            message_lower = message.lower()
            
            # Verificar intenções específicas
            if "prova" in message_lower or "teste" in message_lower or "mastery" in message_lower:
                return await self.processar_duvida_prova(message, aluno), False
            elif "boleto" in message_lower or "pagamento" in message_lower:
                return await self.processar_duvida_boleto(message, aluno), False
            else:
                # Processar com Zaia
                try:
                    # Criar um ID único para o chat baseado no número do WhatsApp
                    chat_external_id = f"whatsapp_{aluno.get('telefone', 'unknown')}" if aluno else f"whatsapp_{phone or 'unknown'}"
                    
                    # Primeiro, criar ou recuperar o chat externo
                    chat_url = f"{settings.ZAIA_API_URL}/external-generative-chat/create"
                    chat_payload = {
                        "agentId": settings.ZAIA_AGENT_ID,
                        "userPhone": phone,  # Usar o número do telefone do usuário
                        "message": message,  # Texto da mensagem recebida
                        "history": []  # Pode ser preenchido com contexto se necessário
                    }
                    
                    headers = {
                        "Authorization": f"Bearer {settings.ZAIA_API_KEY}",
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                    
                    # Criar ou recuperar o chat
                    chat_response = requests.post(chat_url, json=chat_payload, headers=headers, timeout=30)
                    chat_response.raise_for_status()
                    chat_data = chat_response.json()
                    
                    # Retornar False para usar_audio em mensagens de texto normais
                    return chat_data.get("text", ""), False
                    
                except Exception as e:
                    logger.error(f"Erro ao processar mensagem: {str(e)}")
                    # Se tudo falhar, usar resposta padrão
                    return "Desculpe, estou com dificuldades técnicas no momento. Por favor, tente novamente em alguns instantes ou seja mais específico sobre o que precisa (ex: 'quero ver minha prova', 'preciso do boleto', etc.)", False
                
        except Exception as e:
            logger.error(f"Erro ao processar com Zaia: {str(e)}")
            return "Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.", False
            
    async def transcrever_audio(self, audio_url: str) -> str:
        """
        Transcreve áudio usando OpenAI Whisper
        """
        try:
            # Baixar o áudio
            response = requests.get(audio_url)
            response.raise_for_status()
            
            # Salvar temporariamente
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
            
            # Transcrever usando OpenAI
            try:
                with open(temp_file_path, "rb") as audio_file:
                    transcript = self.openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="pt"
                    )
                    return transcript.text
            finally:
                # Limpar arquivo temporário
                try:
                    os.remove(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Erro ao transcrever áudio: {str(e)}")
            return "Desculpe, não consegui entender o áudio. Pode tentar novamente ou enviar sua mensagem por texto?"
            
    async def processar_duvida_prova(self, message: str, aluno: Dict) -> str:
        """
        Processa dúvidas relacionadas a provas/testes no Flexge
        """
        try:
            flexge = FlexgeService()
            info_provas = await flexge.get_student_tests(aluno.get("flexge_id"))
            return f"Aqui está o status das suas provas:\n{info_provas}"
        except Exception as e:
            logger.error(f"Erro ao processar dúvida de prova: {str(e)}")
            return "Desculpe, não consegui acessar as informações das suas provas no momento. Por favor, tente novamente em alguns instantes."
            
    async def processar_duvida_boleto(self, message: str, aluno: Dict) -> str:
        """
        Processa dúvidas relacionadas a boletos/pagamentos
        """
        try:
            asaas = AsaasService()
            info_pagamento = await asaas.get_payment_info(aluno.get("asaas_id"))
            return f"Aqui está o status do seu pagamento:\n{info_pagamento}"
        except Exception as e:
            logger.error(f"Erro ao processar dúvida de boleto: {str(e)}")
            return "Desculpe, não consegui acessar as informações do seu pagamento no momento. Por favor, tente novamente em alguns instantes."
            
    async def processar_comprovante_pagamento(self, message: str, aluno: Dict) -> str:
        """
        Processa comprovantes de pagamento enviados
        """
        try:
            # Aqui você pode implementar a lógica para processar o comprovante
            # Por exemplo, enviar para um sistema de validação ou notificar um administrador
            return "Obrigado por enviar seu comprovante! Vou analisar e confirmar o pagamento em breve."
        except Exception as e:
            logger.error(f"Erro ao processar comprovante: {str(e)}")
            return "Desculpe, ocorreu um erro ao processar seu comprovante. Por favor, tente novamente ou entre em contato com a secretaria."
            
    async def processar_erro_flexge(self, message: str, aluno: Dict) -> str:
        """
        Processa erros do Flexge reportados pelos alunos
        """
        try:
            # Aqui você pode implementar a lógica para processar o erro
            # Por exemplo, registrar em um sistema de tickets ou notificar suporte
            return "Entendi o erro que você está enfrentando. Vou analisar e retornar com uma solução em breve."
        except Exception as e:
            logger.error(f"Erro ao processar erro Flexge: {str(e)}")
            return "Desculpe, não consegui processar o erro reportado. Por favor, tente novamente ou entre em contato com o suporte."
            
    async def enviar_mensagem_texto(self, phone: str, message: str):
        """
        Envia uma mensagem de texto via Z-API
        """
        try:
            result = await enviar_mensagem_zapi(phone, message)
            if result.get("error"):
                logger.error(f"Erro ao enviar mensagem: {result['error']}")
                raise Exception(result["error"])
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {str(e)}")
            raise
            
    async def enviar_audio(self, phone: str, audio_data: bytes):
        """
        Envia áudio via Z-API
        """
        try:
            # Enviar áudio
            result = await enviar_audio_zapi(phone, audio_data)
            if result.get("error"):
                logger.error(f"Erro ao enviar áudio: {result['error']}")
                raise Exception(result["error"])
                
        except Exception as e:
            logger.error(f"Erro ao enviar áudio: {str(e)}")
            raise
            
    async def get_phone_number_id(self, numero: str) -> Optional[str]:
        """
        Obtém o ID do número de telefone no WhatsApp
        """
        try:
            url = f"{self.base_url}/phone-id/{numero}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("id")
            return None
        except Exception as e:
            logger.error(f"Erro ao obter ID do telefone: {str(e)}")
            return None
            
    async def handle_incoming_message(self, webhook_data):
        """
        Processa mensagens recebidas e envia resposta
        """
        try:
            # Processar webhook
            processed_data = await self.processar_webhook(webhook_data)
            if processed_data.get("error"):
                return {"error": processed_data["error"]}
                
            # Processar mensagem com Zaia
            resposta, usar_audio = await self.process_with_zaia(
                processed_data["message"],
                processed_data["aluno"],
                processed_data.get("contexto"),
                processed_data["phone"]
            )
            
            # Enviar resposta
            await self.enviar_resposta(processed_data["phone"], resposta, processed_data["type"])
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {str(e)}")
            return {"error": str(e)}
            
    async def enviar_resposta(self, phone: str, resposta: str, tipo_mensagem_original: str):
        """
        Envia resposta ao usuário, decidindo entre texto ou áudio
        """
        try:
            # Se a mensagem original foi um áudio, responder com áudio
            if tipo_mensagem_original == "audio":
                audio_data = await text_to_speech(resposta)
                await self.enviar_audio(phone, audio_data)
            else:
                await self.enviar_mensagem_texto(phone, resposta)
        except Exception as e:
            logger.error(f"Erro ao enviar resposta: {str(e)}")
            # Se falhar ao enviar áudio, tentar enviar como texto
            if tipo_mensagem_original == "audio":
                try:
                    await self.enviar_mensagem_texto(phone, resposta)
                except Exception as e2:
                    logger.error(f"Erro ao enviar resposta como texto: {str(e2)}")
                    raise e2
            else:
                raise e 