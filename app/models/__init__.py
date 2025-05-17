# Ensure Base is imported so Alembic can find it via models package
from app.db.base import Base
from .shop_model import Shop  # Import your models here so Alembic can find them
