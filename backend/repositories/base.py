from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete
from sqlalchemy.engine import Result
from pydantic import BaseModel

# Define generic type for SQLAlchemy Models
ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType]):
    """
    Base generic repository implementing common CRUD operations
    """
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, id: Any) -> Optional[ModelType]:
        query = select(self.model).where(self.model.id == id)
        result: Result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        query = select(self.model).offset(skip).limit(limit)
        result: Result = await self.db.execute(query)
        return result.scalars().all()

    async def create(self, **kwargs) -> ModelType:
        obj = self.model(**kwargs)
        self.db.add(obj)
        await self.db.flush() # flush to get ID, commit should be handled by UnitOfWork or Service
        return obj

    async def update(self, id: Any, **kwargs) -> Optional[ModelType]:
        query = update(self.model).where(self.model.id == id).values(**kwargs).returning(self.model)
        result = await self.db.execute(query)
        await self.db.flush()
        return result.scalar_one_or_none()

    async def delete(self, id: Any) -> bool:
        query = delete(self.model).where(self.model.id == id)
        result = await self.db.execute(query)
        await self.db.flush()
        return result.rowcount > 0
