from sqlalchemy.orm import declarative_base

# Base for all ORM models
Base = declarative_base()

# You can also define a common base class for all models if you need shared columns like id, created_at, updated_at
# For example:
# from sqlalchemy import Column, Integer, DateTime
# from sqlalchemy.sql import func
# class TimestampedBase(Base):
#     __abstract__ = True # This ensures SQLAlchemy doesn't try to create a table for TimestampedBase
#     id = Column(Integer, primary_key=True, index=True)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now())
#
# Then your models would inherit from TimestampedBase instead of Base directly.
# For now, we'll use the simple Base.
