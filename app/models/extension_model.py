from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Extension(Base):
    __tablename__ = "extensions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, ForeignKey("shops.id"), nullable=False, index=True)
    shopify_extension_id = Column(String, unique=True, index=True, nullable=True)
    account_id = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, nullable=False, default='inactive')
    version = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    shop = relationship("Shop", back_populates="extensions")
