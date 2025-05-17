# Added Integer for a potential ID
from sqlalchemy import Column, String, Boolean, Text, Integer, DateTime
from sqlalchemy.dialects.postgresql import ARRAY  # For storing scopes as an array
from sqlalchemy.sql import func

from app.db.base import Base


class Shop(Base):
    __tablename__ = "shops"

    # Using a simple auto-incrementing integer ID as primary key for now
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    shop_domain = Column(String, unique=True, index=True, nullable=False)
    # This field will store the access token. It should be encrypted in a production environment.
    # Changed to Text for potentially long encrypted tokens
    access_token = Column(Text, nullable=False)

    shopify_scopes = Column(ARRAY(String), nullable=True)
    is_installed = Column(Boolean, default=True, nullable=False)
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        onupdate=func.now(), server_default=func.now())
    # You might want to add other fields like:
    # created_at = Column(DateTime(timezone=True), server_default=func.now())
    # updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    # uninstall_date = Column(DateTime(timezone=True), nullable=True)
    # plan_name = Column(String, nullable=True)

    def __repr__(self):
        return f"<Shop(id={self.id}, shop_domain='{self.shop_domain}', is_installed={self.is_installed})>"
