from sqlalchemy import Column, DateTime, Integer, String, Text
from app.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=True)
    email = Column(String, index=True, nullable=True)
    phone = Column(String, nullable=True)
    company = Column(String, index=True, nullable=True)
    country = Column(String, index=True, nullable=True)
    status = Column(String, index=True, nullable=True)
    owner = Column(String, index=True, nullable=True)
    notes = Column(Text, nullable=True)

    # Kolom hasil ekstraksi AI/Rules dari Notes
    source_channel = Column(String, index=True, nullable=True)
    source_detail = Column(String, nullable=True)

    created_at = Column(DateTime, nullable=True)