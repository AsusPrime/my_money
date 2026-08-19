from src.models import Category
from src.utils.uow.unitofwork import IUnitOfWork


class CategoryEntity:
    def __init__(self, category: Category, uow: IUnitOfWork) -> None:
        self._category = category
        self._uow = uow

    async def is_in_use(self) -> bool:
        return await self._uow.ledgers.count_all(category_id=self._category.id) > 0
