from sqlalchemy import select
from src.models.category import Category
from src.utils.repository.repository import SQLAlchemyRepository


class CategoryRepository(SQLAlchemyRepository):

    model = Category
