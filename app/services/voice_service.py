import aiohttp
import tempfile
import os
import subprocess
import base64
from app.core.config import settings
import logging
import re

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Configurações fixas
VOICE_ID = "ie5yJLYeLpsuijLaojmF"          # Voz profissional da Karol
MODEL_ID = "eleven_multilingual_v1"         # Modelo multilingual v1
LANGUAGE_CODE = "pt-BR"                     # Forçar português brasileiro
OUTPUT_FORMAT = "mp3_44100_128"            # MP3 a 44 kHz/128 kbps
# -------------------------------------------------------------------

def format_multilingual_text(text: str) -> str:
    """
    Marca trechos em inglês para pronúncia correta.
    Ex.: Como se diz "table" em inglês? -> Como se diz [English: table] em inglês?
    """
    pattern = (
        r'(?i)(?:em inglês|in english|como (se )?diz|how (do you )?say|'
        r'tradução|translation|significa).*?[?:]?\s*["""]?([^"""\n]+)["""]?'
    )
    
    def repl(match):
        english_part = match.group(3).strip()
        return match.group(0).replace(english_part, f'[English: {english_part}]')
    
    return re.sub(pattern, repl, text)

async def text_to_speech(text: str) -> bytes:
    """
    Converte texto para áudio usando ElevenLabs.
    Retorna os bytes do áudio em formato OGG.
    """
    # Formata o texto para lidar com palavras em inglês
    formatted_text = format_multilingual_text(text)
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": settings.ELEVENLABS_API_KEY
    }
    
    payload = {
        "text": formatted_text,
        "model_id": MODEL_ID,
        "voice_settings": {
            "stability": 0.85,  # Aumentado para mais estabilidade
            "similarity_boost": 0.85,  # Aumentado para manter mais características da voz original
            "style": 0.35,
            "use_speaker_boost": True,
            "speed": 1.12
        }
    }

    # Log das configurações sendo usadas
    logger.info(f"Gerando áudio com: Modelo={MODEL_ID}, Voice={VOICE_ID}")
    logger.info(f"Configurações de voz: {payload['voice_settings']}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    # Log de sucesso
                    logger.info("Áudio gerado com sucesso!")
                    
                    # Receber o áudio em MP3
                    audio_mp3 = await response.read()
                    
                    # Criar arquivo temporário MP3
                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as mp3_temp:
                        mp3_temp.write(audio_mp3)
                        mp3_path = mp3_temp.name
                        
                    # Criar nome para arquivo OGG
                    ogg_path = mp3_path.replace('.mp3', '.ogg')
                    
                    try:
                        # Converter MP3 para OGG usando ffmpeg com configurações otimizadas
                        subprocess.run(
                            ['ffmpeg', '-loglevel', 'error',
                             '-i', mp3_path,
                             '-c:a', 'libvorbis', '-q:a', '4',
                             ogg_path],
                            check=True, capture_output=True
                        )
                        
                        # Ler o arquivo OGG
                        with open(ogg_path, 'rb') as ogg_file:
                            audio_ogg = ogg_file.read()
                            
                        return audio_ogg
                        
                    except subprocess.CalledProcessError as e:
                        logger.error(f"Erro ao converter áudio: {e.stderr.decode()}")
                        raise Exception("Erro na conversão do áudio")
                    finally:
                        # Limpar arquivos temporários
                        for p in (mp3_path, ogg_path):
                            if os.path.exists(p):
                                try:
                                    os.remove(p)
                                except:
                                    pass
                else:
                    error_text = await response.text()
                    logger.error(f"Erro ao gerar áudio: {error_text}")
                    raise Exception(f"Erro ao gerar áudio: {error_text}")
                    
    except Exception as e:
        logger.error(f"Exceção ao gerar áudio: {str(e)}")
        raise 