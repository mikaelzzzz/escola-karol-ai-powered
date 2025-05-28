# Escola Karol AI POWERED

Sistema de atendimento automatizado via WhatsApp para a Escola Karol, integrando diversos serviços como Flexge, Z-API, ElevenLabs, Zaia, Asaas e Notion.

## Configuração do Ambiente

1. Clone o repositório
2. Instale as dependências:
```bash
pip install -r requirements.txt
```
3. Configure as variáveis de ambiente em um arquivo `.env`:

```env
FLEXGE_API_BASE=https://partner-api.flexge.com/external
FLEXGE_API_KEY=seu_api_key
OPENAI_API_KEY=seu_api_key
ZAIA_API_KEY=seu_api_key
ZAIA_API_URL=https://api.zaia.app/v1.1/api
ZAIA_AGENT_ID=34790
ASAAS_API_KEY=seu_api_key
ASAAS_BASE=https://api.asaas.com/v3
ELEVENLABS_API_KEY=seu_api_key
ELEVENLABS_VOICE_ID=seu_voice_id
ZAPI_INSTANCE_ID=seu_instance_id
ZAPI_TOKEN=seu_token
ZAPI_SECURITY_TOKEN=seu_security_token
NOTION_API_KEY=seu_api_key
NOTION_DATABASE_ID=seu_database_id
```

## Deploy no Render

1. Faça push do código para um repositório GitHub
2. No Render:
   - Crie um novo Web Service
   - Conecte ao repositório GitHub
   - Selecione a branch principal
   - Configure o ambiente:
     - Runtime: Python
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Adicione todas as variáveis de ambiente listadas acima
3. Clique em "Create Web Service"

## Desenvolvimento Local

Para rodar localmente:

```bash
uvicorn app.main:app --reload
```

## Estrutura do Projeto

- `app/`: Código principal da aplicação
  - `core/`: Configurações e utilitários core
  - `services/`: Serviços de integração
  - `utils/`: Utilitários gerais
- `requirements.txt`: Dependências do projeto
- `Procfile`: Configuração para deploy
- `runtime.txt`: Versão do Python 