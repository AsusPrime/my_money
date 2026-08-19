from fastapi import APIRouter
from fastapi import status
from loguru import logger

from src.schemas.category import CategoryCreateSchema
from src.schemas.category import CategoryListResponseSchema
from src.schemas.category import CategoryResponseSchema
from src.schemas.category import CategoryUpdateSchema
from src.services.dependencies.category_dep import CategoryServiceDep
from src.utils.dependencies.uow_dep import UOWDep

router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
)


@router.get(
    "",
    response_model=CategoryListResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_categories_api(uow: UOWDep, category_service: CategoryServiceDep):
    return await category_service.get_all_categories(uow=uow)


@router.get(
    "/{category_id}",
    response_model=CategoryResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_category_api(
    category_id: int, uow: UOWDep, category_service: CategoryServiceDep
):
    return await category_service.get_category_by_id(uow=uow, category_id=category_id)


@router.post(
    "",
    response_model=CategoryResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_category_api(
    body: CategoryCreateSchema, uow: UOWDep, category_service: CategoryServiceDep
):
    new_category = await category_service.create_category(uow=uow, category_data=body)
    logger.info(f"Category created: {new_category.id}")
    return new_category


@router.patch(
    "/{category_id}",
    response_model=CategoryResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_category_api(
    category_id: int,
    body: CategoryUpdateSchema,
    uow: UOWDep,
    category_service: CategoryServiceDep,
):
    updated_category = await category_service.update_category_by_id(
        uow=uow, category_id=category_id, category_data=body
    )
    logger.info(f"Category updated: {category_id}")
    return updated_category


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_category_api(
    category_id: int, uow: UOWDep, category_service: CategoryServiceDep
):
    await category_service.delete_category_by_id(uow=uow, category_id=category_id)
