from typing import Annotated

from fastapi import Depends

from src.services.category_service import CategoryService


def get_category_service() -> CategoryService:
    return CategoryService()


CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]
