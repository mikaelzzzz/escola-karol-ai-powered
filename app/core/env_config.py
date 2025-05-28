"""
Environment variables configuration template.
Copy this file to .env and replace the values with your actual credentials.
"""

ENV_TEMPLATE = """
# Flexge API Configuration
FLEXGE_API_BASE=https://api.flexge.com/v2
FLEXGE_API_KEY=your_flexge_api_key

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# ElevenLabs Configuration
ELEVENLABS_API_KEY=sk_473d93800f7d635eefb5296c18afb4eec418cd3e

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_specific_password

# Zaia Configuration
ZAIA_API_KEY=d0763f89-7e72-4da2-9172-6d10494d22aa
ZAIA_API_URL=https://api.zaia.app
ZAIA_AGENT_ID=34790

# Asaas Configuration
ASAAS_API_KEY=your_asaas_api_key
ASAAS_BASE=https://sandbox.asaas.com/api/v3

# Z-API (WhatsApp) Configuration
ZAPI_INSTANCE_ID=your_zapi_instance_id
ZAPI_TOKEN=your_zapi_token
ZAPI_SECURITY_TOKEN=your_zapi_security_token

# Notion Configuration
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_notion_database_id
"""

def create_env_file():
    """Create a new .env file with template values."""
    with open('.env', 'w') as f:
        f.write(ENV_TEMPLATE.strip())

if __name__ == '__main__':
    create_env_file() 