from src.core.exceptions.exceptions import AddRecordError, ConflictError, NotFoundError
from src.core.messages.messages import Messages
from src.entities.category import CategoryEntity
from src.schemas.category import CategoryCreateSchema
from src.schemas.category import CategoryListResponseSchema
from src.schemas.category import CategoryResponseSchema
from src.schemas.category import CategoryUpdateSchema
from src.utils.uow.unitofwork import IUnitOfWork


class CategoryService:

    @staticmethod
    async def get_all_categories(uow: IUnitOfWork) -> CategoryListResponseSchema:
        categories = await uow.categories.find_all()
        response = CategoryListResponseSchema(
            items=[CategoryResponseSchema.model_validate(category) for category in categories]
        )

        return response

    @staticmethod
    async def get_category_by_id(
        uow: IUnitOfWork, category_id: int
    ) -> CategoryResponseSchema:
        category = await uow.categories.find_one_or_none(id=category_id)
        if not category:
            raise NotFoundError(Messages.CATEGORY_NOT_FOUND)

        response = CategoryResponseSchema.model_validate(category)

        return response

    @staticmethod
    async def create_category(
        uow: IUnitOfWork, category_data: CategoryCreateSchema
    ) -> CategoryResponseSchema:
        new_category = await uow.categories.add_one(data=category_data.model_dump())
        if not new_category:
            raise AddRecordError(Messages.ERROR_FILLED_TO_ADD_NEW_CATEGORY)
        
        return CategoryResponseSchema.model_validate(new_category)

    @staticmethod
    async def update_category_by_id(
        uow: IUnitOfWork, category_id: int, category_data: CategoryUpdateSchema
    ) -> CategoryResponseSchema:
        updated_category = await uow.categories.edit_one(id=category_id, data=category_data.model_dump())

        if not updated_category:
            raise NotFoundError(Messages.CATEGORY_NOT_FOUND)
        
        return CategoryResponseSchema.model_validate(updated_category)

    @staticmethod
    async def delete_category_by_id(uow: IUnitOfWork, category_id: int) -> None:
        category = await uow.categories.find_one_or_none(id=category_id)
        if not category:
            raise NotFoundError(Messages.CATEGORY_NOT_FOUND)

        category_entity = CategoryEntity(category=category, uow=uow)
        if await category_entity.is_in_use():
            raise ConflictError(Messages.CATEGORY_IN_USE)

        await uow.categories.delete_one(_id=category_id)
