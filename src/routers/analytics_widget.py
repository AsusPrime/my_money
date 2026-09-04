from fastapi import APIRouter
from fastapi import status
from loguru import logger

from src.schemas.analytics_widget import AnalyticsWidgetCreateSchema
from src.schemas.analytics_widget import AnalyticsWidgetLayoutSchema
from src.schemas.analytics_widget import AnalyticsWidgetListResponseSchema
from src.schemas.analytics_widget import AnalyticsWidgetResponseSchema
from src.schemas.analytics_widget import AnalyticsWidgetUpdateSchema
from src.services.dependencies.analytics_widget_dep import AnalyticsWidgetServiceDep
from src.utils.dependencies.uow_dep import UOWDep

router = APIRouter(
    prefix="/analytics/widgets",
    tags=["Analytics Widgets"],
)


@router.get(
    "",
    response_model=AnalyticsWidgetListResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def get_widgets_api(uow: UOWDep, widget_service: AnalyticsWidgetServiceDep):
    return await widget_service.get_all_widgets(uow=uow)


@router.post(
    "",
    response_model=AnalyticsWidgetResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_widget_api(
    body: AnalyticsWidgetCreateSchema, uow: UOWDep, widget_service: AnalyticsWidgetServiceDep
):
    new_widget = await widget_service.create_widget(uow=uow, widget_data=body)
    logger.info(f"Analytics widget created: {new_widget.id}")
    return new_widget


@router.patch(
    "/layout",
    response_model=AnalyticsWidgetListResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_widgets_layout_api(
    body: AnalyticsWidgetLayoutSchema, uow: UOWDep, widget_service: AnalyticsWidgetServiceDep
):
    return await widget_service.update_layout(uow=uow, layout_data=body)


@router.patch(
    "/{widget_id}",
    response_model=AnalyticsWidgetResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_widget_api(
    widget_id: int,
    body: AnalyticsWidgetUpdateSchema,
    uow: UOWDep,
    widget_service: AnalyticsWidgetServiceDep,
):
    updated_widget = await widget_service.update_widget_by_id(
        uow=uow, widget_id=widget_id, widget_data=body
    )
    logger.info(f"Analytics widget updated: {widget_id}")
    return updated_widget


@router.delete(
    "/{widget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_widget_api(
    widget_id: int, uow: UOWDep, widget_service: AnalyticsWidgetServiceDep
):
    await widget_service.delete_widget_by_id(uow=uow, widget_id=widget_id)
    logger.info(f"Analytics widget deleted: {widget_id}")
