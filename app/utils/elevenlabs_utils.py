from app.core.config import settings
from elevenlabs import generate, voices, Voice, VoiceSettings

def text_to_speech(text, voice_name="Adam"):
    """
    Converte texto em fala usando a API da ElevenLabs.
    """
    try:
        # Gerar o áudio
        audio = generate(
            api_key=settings.ELEVENLABS_API_KEY,
            text=text,
            voice=voice_name,
            model="eleven_multilingual_v2"
        )
        return audio
    except Exception as e:
        print(f"Erro ao gerar áudio: {str(e)}")
        return None

def list_available_voices():
    """
    Lista todas as vozes disponíveis na conta.
    """
    try:
        available_voices = voices(api_key=settings.ELEVENLABS_API_KEY)
        return available_voices
    except Exception as e:
        print(f"Erro ao listar vozes: {str(e)}")
        return None 