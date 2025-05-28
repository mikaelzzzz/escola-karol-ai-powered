from app.utils.zapi_utils import enviar_mensagem_zapi, enviar_audio_zapi
from app.core.config import settings
from app.services.elevenlabs_service import text_to_speech
from app.services.notion_service import NotionService
import requests
import json
from typing import Dict, Optional, Tuple
from app.services.flexge_service import FlexgeService
from app.services.asaas_service import AsaasService
import base64
import openai

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
            print(f"Erro ao extrair texto da mídia: {str(e)}")
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
            elif any(greeting in message_lower for greeting in ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite"]):
                # Resposta de saudação personalizada
                nome = aluno.get("nome", "").split()[0] if aluno else ""
                return f"Olá {nome}! 😊 Sou a Karol, sua assistente virtual. Como posso ajudar você hoje? Posso auxiliar com:\n\n📚 Dúvidas sobre o Flexge\n📝 Informações sobre suas provas\n💳 Questões sobre pagamentos\n📖 Explicações gramaticais\n\nÉ só me dizer o que precisa!", False
            else:
                # Tentar processar com Zaia
                try:
                    # Usar a API da Zaia para gerar resposta
                    url = f"{settings.ZAIA_API_URL}/v1.1/api/external-generative-message/create"
                    
                    # Criar um ID único para o chat baseado no número do WhatsApp
                    chat_external_id = f"whatsapp_{aluno.get('telefone', 'unknown')}" if aluno else f"whatsapp_{phone or 'unknown'}"
                    
                    payload = {
                        "agentId": settings.ZAIA_AGENT_ID,
                        "externalGenerativeChatId": hash(chat_external_id) % 1000000,  # Gerar um ID numérico baseado no telefone
                        "externalGenerativeChatExternalId": chat_external_id,
                        "prompt": message,
                        "streaming": False,
                        "asMarkdown": False,
                        "custom": {
                            "whatsapp": aluno.get("telefone", "") if aluno else "",
                            "nome": aluno.get("nome", "") if aluno else "",
                            "email": aluno.get("email", "") if aluno else ""
                        }
                    }
                    
                    headers = {
                        "Authorization": f"Bearer {settings.ZAIA_API_KEY}",
                        "Content-Type": "application/json"
                    }
                    
                    response = requests.post(url, json=payload, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        # A resposta pode estar em diferentes campos dependendo da configuração
                        resposta_texto = response_data.get("message", "") or response_data.get("content", "") or response_data.get("response", "")
                        if resposta_texto:
                            return resposta_texto, True
                    
                    # Se não conseguiu com a Zaia, usar GPT-4 como fallback
                    nome = aluno.get("nome", "").split()[0] if aluno else ""
                    prompt = f"""Você é a Karol, assistente virtual da Escola Karol Language Learning.
                    Aluno: {nome}
                    Mensagem do aluno: {message}
                    
                    Responda de forma amigável e profissional, sempre tentando ajudar.
                    Se não souber responder, sugira opções como: verificar provas, boletos, dúvidas sobre o Flexge, etc."""
                    
                    response = self.openai_client.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "Você é a Karol, assistente virtual educacional. Seja amigável, profissional e sempre tente ajudar."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=300
                    )
                    
                    return response.choices[0].message.content, False
                    
                except Exception as e:
                    print(f"Erro ao processar mensagem: {str(e)}")
                    # Se tudo falhar, usar resposta padrão
                    return "Desculpe, estou com dificuldades técnicas no momento. Por favor, tente novamente em alguns instantes ou seja mais específico sobre o que precisa (ex: 'quero ver minha prova', 'preciso do boleto', etc.)", False
                
        except Exception as e:
            print(f"Erro ao processar com Zaia: {str(e)}")
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
            with open(temp_file_path, "rb") as audio_file:
                transcript = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            
            # Limpar arquivo temporário
            import os
            os.unlink(temp_file_path)
            
            return transcript.text
            
        except Exception as e:
            print(f"Erro ao transcrever áudio: {str(e)}")
            return "Desculpe, não consegui transcrever o áudio. Por favor, envie sua mensagem como texto."
            
    async def processar_duvida_prova(self, message: str, aluno: Dict) -> str:
        """
        Processa dúvida específica sobre prova
        """
        try:
            if not aluno or not aluno.get("email"):
                return "Desculpe, não consegui identificar seus dados de aluno."
                
            flexge_service = FlexgeService()
            provas = await flexge_service.buscar_detalhes_prova(aluno["email"])
            
            if not provas:
                return "Não encontrei registros recentes de provas no seu histórico."
                
            # Formatar resposta
            ultima_prova = provas[0]
            resposta = f"Olá! Encontrei sua última prova: {ultima_prova['test_name']}\n"
            resposta += f"Data: {ultima_prova['test_date']}\n"
            resposta += f"Nota: {ultima_prova['score']}\n"
            resposta += f"Acertos: {ultima_prova['correct_answers']} de {ultima_prova['total_questions']}\n\n"
            
            # Adicionar detalhes de erros se houver
            erros = [q for q in ultima_prova['questions'] if not q['is_correct']]
            if erros:
                resposta += "Aqui estão as questões que você errou:\n\n"
                for erro in erros[:3]:  # Mostrar até 3 erros
                    resposta += f"Pergunta: {erro['question']}\n"
                    resposta += f"Sua resposta: {erro['student_answer']}\n"
                    resposta += f"Resposta correta: {erro['correct_answer']}\n\n"
                    
            return resposta
            
        except Exception as e:
            print(f"Erro ao processar dúvida de prova: {str(e)}")
            return "Desculpe, não consegui recuperar os detalhes da sua prova no momento."
            
    async def processar_duvida_boleto(self, message: str, aluno: Dict) -> str:
        """
        Processa dúvida específica sobre boleto
        """
        try:
            if not aluno:
                return "Desculpe, não consegui identificar seus dados de aluno."
                
            asaas_service = AsaasService()
            cobranca = await asaas_service.buscar_proxima_cobranca(aluno)
            
            if not cobranca:
                return "Não encontrei nenhuma cobrança em aberto no seu nome."
                
            # Formatar resposta
            resposta = f"Olá {aluno['nome']}, encontrei sua próxima cobrança:\n\n"
            resposta += f"Valor: R$ {cobranca['valor']:.2f}\n"
            resposta += f"Vencimento: {cobranca['vencimento']}\n\n"
            
            if cobranca['link']:
                resposta += f"Você pode acessar o boleto aqui: {cobranca['link']}\n"
            if cobranca['codigo_barras']:
                resposta += f"Código de barras: {cobranca['codigo_barras']}\n"
                
            return resposta
            
        except Exception as e:
            print(f"Erro ao processar dúvida de boleto: {str(e)}")
            return "Desculpe, não consegui recuperar as informações do seu boleto no momento."
            
    async def processar_comprovante_pagamento(self, message: str, aluno: Dict) -> str:
        """
        Processa comprovante de pagamento
        """
        try:
            # Extrair informações do comprovante do message (que já está formatado)
            linhas = message.split('\n')
            valor = next((l.split(': ')[1] for l in linhas if 'Valor:' in l), None)
            data = next((l.split(': ')[1] for l in linhas if 'Data:' in l), None)
            
            if not aluno or not aluno.get("email"):
                return "Desculpe, não consegui identificar seus dados de aluno para verificar o pagamento."
                
            asaas_service = AsaasService()
            cobrancas = await asaas_service.buscar_cobrancas_por_email(aluno["email"])
            
            if not cobrancas:
                return "Não encontrei cobranças registradas para verificar seu pagamento."
                
            # Tentar encontrar a cobrança correspondente
            for cobranca in cobrancas:
                if (valor and str(cobranca["valor"]) in valor) or (data and data in cobranca["vencimento"]):
                    if cobranca["status"] == "RECEIVED":
                        return "Seu pagamento já foi identificado e processado! Está tudo certo."
                    elif cobranca["status"] == "PENDING":
                        return "Recebi seu comprovante! O pagamento ainda está sendo processado. Assim que for confirmado, será automaticamente registrado no sistema."
            
            return "Recebi seu comprovante! Vou encaminhar para nossa equipe financeira verificar e dar baixa no pagamento."
            
        except Exception as e:
            print(f"Erro ao processar comprovante: {str(e)}")
            return "Desculpe, tive um problema ao processar seu comprovante. Por favor, entre em contato com nosso suporte."

    async def processar_erro_flexge(self, message: str, aluno: Dict) -> str:
        """
        Processa screenshot de erro do Flexge
        """
        try:
            # Extrair informações do erro do message (que já está formatado)
            linhas = message.split('\n')
            tipo_erro = next((l.split(': ')[1] for l in linhas if 'Tipo:' in l), None)
            mensagem_erro = next((l.split(': ')[1] for l in linhas if 'Mensagem:' in l), None)
            
            # Processar com GPT para gerar uma resposta mais amigável
            prompt = f"""
            Com base neste erro do Flexge:
            Tipo: {tipo_erro}
            Mensagem: {mensagem_erro}
            
            Gere uma resposta amigável explicando:
            1. O que pode ter causado o erro
            2. Como o aluno pode resolver
            3. Se precisar de suporte, o que fazer
            
            Mantenha a resposta curta e direta."""
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Você é um especialista em suporte técnico do Flexge, sempre claro e objetivo."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Erro ao processar erro Flexge: {str(e)}")
            return "Desculpe, não consegui analisar completamente o erro. Por favor, tente novamente ou entre em contato com nosso suporte técnico."
            
    async def enviar_mensagem_texto(self, phone: str, message: str):
        """
        Envia mensagem de texto via Z-API
        """
        try:
            url = f"{self.base_url}/send-text"
            headers = {
                "Content-Type": "application/json",
                "Client-Token": settings.ZAPI_SECURITY_TOKEN
            }
            payload = {
                "phone": phone,
                "message": message
            }
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Erro ao enviar mensagem: {str(e)}")
            return False
            
    async def enviar_audio(self, phone: str, audio_data: bytes):
        """
        Envia mensagem de áudio via Z-API
        """
        try:
            url = f"{self.base_url}/send-audio"
            headers = {
                "Content-Type": "application/json",
                "Client-Token": settings.ZAPI_SECURITY_TOKEN
            }
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            payload = {
                "phone": phone,
                "audio": audio_base64
            }
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Erro ao enviar áudio: {str(e)}")
            return False

    async def get_phone_number_id(self, numero: str) -> Optional[str]:
        """
        Verifica se um número está registrado no WhatsApp
        """
        try:
            url = f"{self.base_url}/phone-exists"
            payload = {"phone": numero}
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data.get("exists", False)
        except Exception as e:
            print(f"Erro ao verificar número: {str(e)}")
            return None
    
    async def handle_incoming_message(self, webhook_data):
        """
        Processa mensagens recebidas via webhook do Z-API
        """
        try:
            # Extrair informações da mensagem
            phone = webhook_data.get('phone')
            message = webhook_data.get('message')
            
            if not phone or not message:
                return {"error": "Dados incompletos"}
            
            # Processar com o agente da Zaia
            zaia_response = await self.process_with_zaia(message)
            
            # Converter resposta em áudio usando ElevenLabs
            audio_data = await text_to_speech(text=zaia_response)
            
            # Enviar áudio via WhatsApp
            await self.send_voice_message(phone, audio_data)
            
            return {"success": True}
            
        except Exception as e:
            return {"error": str(e)}
    
    async def enviar_resposta(self, phone: str, resposta: str, tipo_mensagem_original: str):
        """
        Envia resposta de acordo com o tipo de mensagem original
        """
        try:
            # Se a mensagem original foi áudio, responder com áudio
            if tipo_mensagem_original == "audio":
                audio_data = await text_to_speech(text=resposta)
                return await self.enviar_audio(phone, audio_data)
            # Para outros tipos, responder com texto
            else:
                return await self.enviar_mensagem_texto(phone, resposta)
                
        except Exception as e:
            print(f"Erro ao enviar resposta: {str(e)}")
            return False 