from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.db.base_class import Base

class WhatsAppMapping(Base):
    __tablename__ = "whatsapp_mappings"

    phone = Column(String, primary_key=True, index=True)
    email = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 