from pydantic import BaseModel
from pydantic import ConfigDict


class CategoryResponseSchema(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class CategoryCreateSchema(BaseModel):
    name: str


class CategoryUpdateSchema(BaseModel):
    name: str | None = None


class CategoryListResponseSchema(BaseModel):
    items: list[CategoryResponseSchema]

    model_config = ConfigDict(from_attributes=True)
