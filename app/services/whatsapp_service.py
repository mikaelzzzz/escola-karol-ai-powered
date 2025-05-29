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
import aiohttp
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)

# Cache simples: phone -> chat_id
chat_context_cache = defaultdict(lambda: None)

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
            
            # Sempre processar áudio se o campo existir
            if "audio" in webhook_data and webhook_data["audio"].get("audioUrl"):
                audio_url = webhook_data["audio"]["audioUrl"]
                message = await self.transcrever_audio(audio_url)
                message_type = "audio"
            # Sempre processar imagem se o campo existir
            elif "image" in webhook_data and webhook_data["image"].get("imageUrl"):
                url = webhook_data["image"]["imageUrl"]
                message, contexto = await self.extrair_texto_midia(url, "image")
                message_type = "image"
            elif message_type == "message":
                message = webhook_data.get("text", "")
            elif message_type in ["image", "document"]:
                url = webhook_data.get(message_type, {}).get("url")
                if not url:
                    return {"error": f"URL do {message_type} não encontrada"}
                message, contexto = await self.extrair_texto_midia(url, message_type)
            else:
                return {"error": "Tipo de mensagem não suportado"}
            
            # Validação: mensagem não pode ser vazia
            if not message or not message.strip():
                return {
                    "error": "Mensagem vazia",
                    "message": "Não consegui entender sua mensagem. Pode tentar novamente ou enviar em texto?"
                }
            
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
            logger.info(f"Iniciando processamento com Zaia. Mensagem: {message}, Contexto: {contexto}")
            
            # Se tiver contexto específico, tratar adequadamente
            if contexto == "comprovante_pagamento":
                return await self.processar_comprovante_pagamento(message, aluno), False
            elif contexto == "erro_flexge":
                return await self.processar_erro_flexge(message, aluno), False
            
            message_lower = message.lower()
            logger.info(f"Mensagem normalizada: {message_lower}")
            logger.info("Processando com API da Zaia (novo fluxo)")
            
            url_chat = f"{settings.ZAIA_API_URL}/v1.1/api/external-generative-chat/create"
            url_message = f"{settings.ZAIA_API_URL}/v1.1/api/external-generative-message/create"
            url_retrieve = f"{settings.ZAIA_API_URL}/v1.1/api/external-generative-message/retrieve-multiple"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.ZAIA_API_KEY}"
            }
            
            # Se a mensagem for um e-mail e já houver chat_id, reutilize
            if "@" in message and "." in message and chat_context_cache[phone]:
                chat_id = chat_context_cache[phone]
                logger.info(f"Reutilizando chat_id existente para {phone}: {chat_id}")
            else:
                # 1. Criar o chat
                payload_chat = {
                    "agentId": settings.ZAIA_AGENT_ID
                }
                logger.info(f"Criando chat na Zaia: {url_chat} | Payload: {payload_chat}")
                async with aiohttp.ClientSession() as session:
                    async with session.post(url_chat, headers=headers, json=payload_chat) as resp_chat:
                        chat_data = await resp_chat.json()
                        logger.info(f"Resposta da criação do chat: {chat_data}")
                        chat_id = chat_data.get("id")
                        if not chat_id:
                            return "Erro ao criar chat na Zaia.", False
                        # Salva o chat_id no cache
                        chat_context_cache[phone] = chat_id
            # 2. Criar a mensagem
            # Buscar histórico do chat antes de enviar nova mensagem
            historico = await self.buscar_historico_zaia(chat_id)
            contexto = ""
            for msg in historico[-5:]:  # Pega as últimas 5 mensagens
                if msg["origin"] == "user":
                    contexto += f"Usuário: {msg['text']}\n"
                elif msg["origin"] == "assistant":
                    contexto += f"Assistente: {msg['text']}\n"
            prompt_com_contexto = f"{contexto}Usuário: {message}"
            payload_message = {
                "agentId": settings.ZAIA_AGENT_ID,
                "externalGenerativeChatId": chat_id,
                "prompt": prompt_com_contexto,
                "custom": {"whatsapp": phone}
            }
            logger.info(f"Enviando mensagem para Zaia: {url_message} | Payload: {payload_message}")
            async with aiohttp.ClientSession() as session:
                async with session.post(url_message, headers=headers, json=payload_message) as resp_msg:
                    msg_data = await resp_msg.json()
                    logger.info(f"Resposta do envio da mensagem: {msg_data}")
                # 3. Buscar a resposta
                for _ in range(10):
                    retrieve_url = f"{url_retrieve}?externalGenerativeChatIds={chat_id}"
                    async with session.get(retrieve_url, headers=headers) as resp_retrieve:
                        try:
                            retrieve_data = await resp_retrieve.json()
                            logger.info(f"Buscando resposta da Zaia. Chat ID: {chat_id}, Resposta: {retrieve_data}")
                            chats = retrieve_data.get("externalGenerativeChats", [])
                            if chats:
                                messages = chats[0].get("externalGenerativeMessages", [])
                                for msg in reversed(messages):
                                    if msg.get("origin") == "assistant" and msg.get("text"):
                                        return msg["text"], False
                        except Exception as e:
                            raw_text = await resp_retrieve.text()
                            logger.error(f"Erro ao decodificar JSON da resposta da Zaia (status {resp_retrieve.status}): {raw_text}")
                            break
                    await asyncio.sleep(2)
            return "Desculpe, estou com dificuldades para processar sua mensagem no momento. Por favor, tente novamente em alguns instantes.", False
        except Exception as e:
            logger.error(f"Erro ao processar mensagem com Zaia: {str(e)}")
            return "Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente em alguns instantes.", False
            
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

    async def buscar_historico_zaia(self, chat_id: int) -> list:
        """
        Busca o histórico completo de mensagens de um chat na Zaia.
        Retorna uma lista de dicionários com origin e text.
        """
        url_retrieve = f"{settings.ZAIA_API_URL}/v1.1/api/external-generative-message/retrieve-multiple?externalGenerativeChatIds={chat_id}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.ZAIA_API_KEY}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url_retrieve, headers=headers) as resp:
                try:
                    data = await resp.json()
                    chats = data.get("externalGenerativeChats", [])
                    if chats:
                        messages = chats[0].get("externalGenerativeMessages", [])
                        return [{"origin": m.get("origin"), "text": m.get("text")} for m in messages]
                    return []
                except Exception as e:
                    raw_text = await resp.text()
                    logger.error(f"Erro ao buscar histórico da Zaia (status {resp.status}): {raw_text}")
                    return [] 