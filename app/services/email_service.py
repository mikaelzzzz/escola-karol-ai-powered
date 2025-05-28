from app.core.config import settings
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class EmailService:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD

    async def send_inactivity_email(self, recipient: str, first_name: str):
        subject = "Aviso: seu acesso ao Flexge será bloqueado"
        html = f"""
        <html><body style='font-family:Montserrat;'>
        <h2 style='color:#113842;'>Hello Hello {first_name}!</h2>
        <p>Notamos que você não acessa o Flexge há alguns dias.</p>
        <p>Seu acesso será <strong>bloqueado em dois dias</strong>. Por favor, entre no app e evite isso.</p>
        <p style='margin-top:30px;'>Equipe Karol Elói Language Learning</p>
        </body></html>
        """
        
        msg = MIMEMultipart()
        msg['From'] = self.smtp_user
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(html, 'html'))
        
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print("Erro ao enviar email:", e)
            return False 