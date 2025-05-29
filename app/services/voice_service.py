import aiohttp
import tempfile
import os
import subprocess
import base64
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

async def text_to_speech(text: str) -> bytes:
    """
    Converte texto para áudio usando ElevenLabs.
    Retorna os bytes do áudio em formato OGG.
    """
    # Karol Pro Voice
    url = "https://api.elevenlabs.io/v1/text-to-speech/ie5yJLYeLpsuijLaojmF"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": settings.ELEVENLABS_API_KEY
    }
    
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.95,
            "style": 0,
            "use_speaker_boost": True,
            "speed": 1.12
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    # Receber o áudio em MP3
                    audio_mp3 = await response.read()
                    
                    # Criar arquivo temporário MP3
                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as mp3_temp:
                        mp3_temp.write(audio_mp3)
                        mp3_path = mp3_temp.name
                        
                    # Criar nome para arquivo OGG
                    ogg_path = mp3_path.replace('.mp3', '.ogg')
                    
                    try:
                        # Converter MP3 para OGG usando ffmpeg
                        subprocess.run(
                            ['ffmpeg', '-i', mp3_path, '-c:a', 'libvorbis', '-q:a', '4', ogg_path],
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
                        try:
                            os.remove(mp3_path)
                            os.remove(ogg_path)
                        except:
                            pass
                else:
                    error_text = await response.text()
                    logger.error(f"Erro ao gerar áudio: {error_text}")
                    raise Exception(f"Erro ao gerar áudio: {error_text}")
                    
    except Exception as e:
        logger.error(f"Exceção ao gerar áudio: {str(e)}")
        raise 