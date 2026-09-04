from src.core.exceptions.exceptions import AddRecordError, BadRequestError, NotFoundError
from src.core.messages.messages import Messages
from src.enums.enums import AnalyticsWidgetMetricEnum, NetWorthBucketEnum
from src.schemas.analytics_widget import AnalyticsWidgetCreateSchema
from src.schemas.analytics_widget import AnalyticsWidgetLayoutSchema
from src.schemas.analytics_widget import AnalyticsWidgetListResponseSchema
from src.schemas.analytics_widget import AnalyticsWidgetResponseSchema
from src.schemas.analytics_widget import AnalyticsWidgetUpdateSchema
from src.utils.uow.unitofwork import IUnitOfWork

_NET_WORTH_GROUP_BYS = {b.value for b in NetWorthBucketEnum}
_DEFAULT_WIDGET_WIDTH = 6
_DEFAULT_WIDGET_HEIGHT = 4


class AnalyticsWidgetService:

    @staticmethod
    async def get_all_widgets(uow: IUnitOfWork) -> AnalyticsWidgetListResponseSchema:
        widgets = await uow.analytics_widgets.find_all()

        return AnalyticsWidgetListResponseSchema(
            items=[AnalyticsWidgetResponseSchema.model_validate(w) for w in widgets]
        )

    @staticmethod
    async def create_widget(
        uow: IUnitOfWork, widget_data: AnalyticsWidgetCreateSchema
    ) -> AnalyticsWidgetResponseSchema:
        AnalyticsWidgetService._validate_net_worth_combo(
            metric=widget_data.metric,
            group_by=widget_data.group_by.value,
            currency_ticker=widget_data.filters.currency_ticker,
        )

        next_y = await uow.analytics_widgets.get_next_row_y()

        data = widget_data.model_dump(exclude={"filters"})
        data["filters"] = widget_data.filters.model_dump(mode="json", exclude_none=True)
        data["grid_x"] = 0
        data["grid_y"] = next_y
        data["grid_w"] = _DEFAULT_WIDGET_WIDTH
        data["grid_h"] = _DEFAULT_WIDGET_HEIGHT

        new_widget = await uow.analytics_widgets.add_one(data=data)

        if new_widget is None:
            raise AddRecordError(Messages.ERROR_FILLED_TO_ADD_NEW_ANALYTICS_WIDGET)

        return AnalyticsWidgetResponseSchema.model_validate(new_widget)

    @staticmethod
    async def update_widget_by_id(
        uow: IUnitOfWork, widget_id: int, widget_data: AnalyticsWidgetUpdateSchema
    ) -> AnalyticsWidgetResponseSchema:
        if widget_data.metric is not None or widget_data.group_by is not None or (
            widget_data.filters is not None
        ):
            existing = await uow.analytics_widgets.find_one_or_none(id=widget_id)
            if existing is None:
                raise NotFoundError(Messages.ANALYTICS_WIDGET_NOT_FOUND)

            metric = widget_data.metric or existing.metric
            resolved_group_by = widget_data.group_by or existing.group_by
            group_by = getattr(resolved_group_by, "value", resolved_group_by)
            currency_ticker = (
                widget_data.filters.currency_ticker
                if widget_data.filters is not None
                else existing.filters.get("currency_ticker")
            )
            AnalyticsWidgetService._validate_net_worth_combo(
                metric=metric, group_by=group_by, currency_ticker=currency_ticker
            )

        data = widget_data.model_dump(exclude_unset=True, exclude={"filters"})
        if widget_data.filters is not None:
            data["filters"] = widget_data.filters.model_dump(mode="json", exclude_none=True)

        updated_widget = await uow.analytics_widgets.edit_one(id=widget_id, data=data)

        if updated_widget is None:
            raise NotFoundError(Messages.ANALYTICS_WIDGET_NOT_FOUND)

        return AnalyticsWidgetResponseSchema.model_validate(updated_widget)

    @staticmethod
    async def delete_widget_by_id(uow: IUnitOfWork, widget_id: int) -> None:
        deleted_widget = await uow.analytics_widgets.delete_one(_id=widget_id)

        if deleted_widget is None:
            raise NotFoundError(Messages.ANALYTICS_WIDGET_NOT_FOUND)

    @staticmethod
    async def update_layout(
        uow: IUnitOfWork, layout_data: AnalyticsWidgetLayoutSchema
    ) -> AnalyticsWidgetListResponseSchema:
        for item in layout_data.items:
            updated = await uow.analytics_widgets.edit_one(
                id=item.id,
                data={"grid_x": item.x, "grid_y": item.y, "grid_w": item.w, "grid_h": item.h},
            )
            if updated is None:
                raise NotFoundError(Messages.ANALYTICS_WIDGET_NOT_FOUND)

        return await AnalyticsWidgetService.get_all_widgets(uow)

    @staticmethod
    def _validate_net_worth_combo(*, metric, group_by: str, currency_ticker: str | None) -> None:
        if metric != AnalyticsWidgetMetricEnum.NET_WORTH:
            return
        if group_by not in _NET_WORTH_GROUP_BYS or not currency_ticker:
            raise BadRequestError(Messages.ANALYTICS_WIDGET_INVALID_NET_WORTH_CONFIG)
