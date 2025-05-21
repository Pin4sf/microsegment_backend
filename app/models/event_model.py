from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB 
from app.db.base import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False, index=True)
    account_id = Column(String, ForeignKey("extensions.account_id"), nullable=False, index=True)
    event_name = Column(String, nullable=False, index=True)
    payload = Column(JSONB) 
    received_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    shop = relationship("Shop")
    extension = relationship("Extension")