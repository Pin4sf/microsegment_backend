from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Create an async engine
# The echo=True argument is useful for debugging, it logs all SQL statements.
# Set pool_pre_ping=True to enable SQLAlchemy to check connections for liveness before using them.
engine = create_async_engine(
    settings.DATABASE_URL, echo=True, pool_pre_ping=True)

# Create a session factory
# expire_on_commit=False prevents attributes from being expired after commit,
# which can be useful in async contexts or if you need to access data after a session is closed.
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency to get a DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # Commits transaction if all operations succeed
        except Exception:
            await session.rollback()  # Rolls back in case of an error
            raise
        finally:
            await session.close()
