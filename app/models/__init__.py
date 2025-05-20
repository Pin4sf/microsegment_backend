# Ensure Base is imported so Alembic can find it via models package
from app.db.base import Base
from .shop_model import Shop  # Import your models here so Alembic can find them
from .extension_model import Extension  # Import the new Extension model
from .event_model import Event  # Import the new Event model
