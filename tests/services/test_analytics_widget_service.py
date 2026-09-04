import pytest

from src.core.exceptions.exceptions import AddRecordError
from src.core.exceptions.exceptions import BadRequestError
from src.core.exceptions.exceptions import NotFoundError
from src.core.messages.messages import Messages
from src.schemas.analytics_widget import AnalyticsWidgetCreateSchema
from src.schemas.analytics_widget import AnalyticsWidgetFiltersSchema
from src.schemas.analytics_widget import AnalyticsWidgetLayoutItemSchema
from src.schemas.analytics_widget import AnalyticsWidgetLayoutSchema
from src.schemas.analytics_widget import AnalyticsWidgetUpdateSchema
from src.services.analytics_widget_service import AnalyticsWidgetService
from tests.services.conftest import make_analytics_widget_row


class TestGetAllWidgets:
    async def test_returns_all_widgets(self, uow):
        uow.analytics_widgets.find_all.return_value = [
            make_analytics_widget_row(id=1, title="First"),
            make_analytics_widget_row(id=2, title="Second"),
        ]

        result = await AnalyticsWidgetService.get_all_widgets(uow=uow)

        assert [w.title for w in result.items] == ["First", "Second"]

    async def test_returns_empty_list_when_no_widgets(self, uow):
        uow.analytics_widgets.find_all.return_value = []

        result = await AnalyticsWidgetService.get_all_widgets(uow=uow)

        assert result.items == []


class TestCreateWidget:
    async def test_creates_widget_below_existing_ones(self, uow):
        uow.analytics_widgets.get_next_row_y.return_value = 8
        uow.analytics_widgets.add_one.return_value = make_analytics_widget_row(
            id=1, title="Spending", grid_y=8
        )

        result = await AnalyticsWidgetService.create_widget(
            uow=uow,
            widget_data=AnalyticsWidgetCreateSchema(
                title="Spending",
                chart_type="bar",
                group_by="category",
                metric="sum",
            ),
        )

        assert result.title == "Spending"
        assert result.grid_y == 8
        uow.analytics_widgets.add_one.assert_awaited_once_with(
            data={
                "title": "Spending",
                "chart_type": "bar",
                "group_by": "category",
                "metric": "sum",
                "filters": {},
                "grid_x": 0,
                "grid_y": 8,
                "grid_w": 6,
                "grid_h": 4,
            }
        )

    async def test_serializes_filters_to_json_compatible_dict(self, uow):
        uow.analytics_widgets.get_next_row_y.return_value = 0
        uow.analytics_widgets.add_one.return_value = make_analytics_widget_row(
            filters={"category_ids": [5, 6]}
        )

        await AnalyticsWidgetService.create_widget(
            uow=uow,
            widget_data=AnalyticsWidgetCreateSchema(
                title="Groceries",
                chart_type="pie",
                group_by="category",
                metric="sum",
                filters=AnalyticsWidgetFiltersSchema(category_ids=[5, 6]),
            ),
        )

        call_data = uow.analytics_widgets.add_one.call_args.kwargs["data"]
        assert call_data["filters"] == {"category_ids": [5, 6]}

    async def test_raises_add_record_error_when_insert_fails(self, uow):
        uow.analytics_widgets.get_next_row_y.return_value = 0
        uow.analytics_widgets.add_one.return_value = None

        with pytest.raises(AddRecordError) as exc_info:
            await AnalyticsWidgetService.create_widget(
                uow=uow,
                widget_data=AnalyticsWidgetCreateSchema(
                    title="Spending", chart_type="bar", group_by="category", metric="sum"
                ),
            )

        assert exc_info.value.message == Messages.ERROR_FILLED_TO_ADD_NEW_ANALYTICS_WIDGET

    async def test_accepts_a_valid_net_worth_widget(self, uow):
        uow.analytics_widgets.get_next_row_y.return_value = 0
        uow.analytics_widgets.add_one.return_value = make_analytics_widget_row(
            metric="net_worth", group_by="month", filters={"currency_ticker": "UAH"}
        )

        result = await AnalyticsWidgetService.create_widget(
            uow=uow,
            widget_data=AnalyticsWidgetCreateSchema(
                title="Net worth",
                chart_type="line",
                group_by="month",
                metric="net_worth",
                filters=AnalyticsWidgetFiltersSchema(currency_ticker="UAH"),
            ),
        )

        assert result.metric == "net_worth"

    async def test_rejects_net_worth_without_a_currency(self, uow):
        with pytest.raises(BadRequestError) as exc_info:
            await AnalyticsWidgetService.create_widget(
                uow=uow,
                widget_data=AnalyticsWidgetCreateSchema(
                    title="Net worth", chart_type="line", group_by="month", metric="net_worth"
                ),
            )

        assert exc_info.value.message == Messages.ANALYTICS_WIDGET_INVALID_NET_WORTH_CONFIG
        uow.analytics_widgets.add_one.assert_not_called()

    async def test_rejects_net_worth_with_a_non_time_bucket_group_by(self, uow):
        with pytest.raises(BadRequestError) as exc_info:
            await AnalyticsWidgetService.create_widget(
                uow=uow,
                widget_data=AnalyticsWidgetCreateSchema(
                    title="Net worth",
                    chart_type="line",
                    group_by="category",
                    metric="net_worth",
                    filters=AnalyticsWidgetFiltersSchema(currency_ticker="UAH"),
                ),
            )

        assert exc_info.value.message == Messages.ANALYTICS_WIDGET_INVALID_NET_WORTH_CONFIG
        uow.analytics_widgets.add_one.assert_not_called()


class TestUpdateWidgetById:
    async def test_updates_widget(self, uow):
        uow.analytics_widgets.edit_one.return_value = make_analytics_widget_row(
            id=1, title="Renamed"
        )

        result = await AnalyticsWidgetService.update_widget_by_id(
            uow=uow, widget_id=1, widget_data=AnalyticsWidgetUpdateSchema(title="Renamed")
        )

        assert result.title == "Renamed"
        uow.analytics_widgets.edit_one.assert_awaited_once_with(
            id=1, data={"title": "Renamed"}
        )
        uow.analytics_widgets.find_one_or_none.assert_not_called()

    async def test_only_sends_explicitly_set_fields(self, uow):
        uow.analytics_widgets.edit_one.return_value = make_analytics_widget_row(id=1)

        await AnalyticsWidgetService.update_widget_by_id(
            uow=uow, widget_id=1, widget_data=AnalyticsWidgetUpdateSchema(title="Renamed")
        )

        uow.analytics_widgets.edit_one.assert_awaited_once_with(id=1, data={"title": "Renamed"})

    async def test_raises_not_found_when_missing(self, uow):
        uow.analytics_widgets.edit_one.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await AnalyticsWidgetService.update_widget_by_id(
                uow=uow, widget_id=999, widget_data=AnalyticsWidgetUpdateSchema(title="X")
            )

        assert exc_info.value.message == Messages.ANALYTICS_WIDGET_NOT_FOUND

    async def test_revalidates_net_worth_combo_when_changing_metric(self, uow):
        uow.analytics_widgets.find_one_or_none.return_value = make_analytics_widget_row(
            id=1, group_by="category", filters={}
        )

        with pytest.raises(BadRequestError) as exc_info:
            await AnalyticsWidgetService.update_widget_by_id(
                uow=uow, widget_id=1, widget_data=AnalyticsWidgetUpdateSchema(metric="net_worth")
            )

        assert exc_info.value.message == Messages.ANALYTICS_WIDGET_INVALID_NET_WORTH_CONFIG
        uow.analytics_widgets.edit_one.assert_not_called()

    async def test_allows_changing_metric_to_net_worth_when_already_time_bucketed(self, uow):
        uow.analytics_widgets.find_one_or_none.return_value = make_analytics_widget_row(
            id=1, group_by="month", filters={"currency_ticker": "UAH"}
        )
        uow.analytics_widgets.edit_one.return_value = make_analytics_widget_row(
            id=1, metric="net_worth", group_by="month", filters={"currency_ticker": "UAH"}
        )

        result = await AnalyticsWidgetService.update_widget_by_id(
            uow=uow, widget_id=1, widget_data=AnalyticsWidgetUpdateSchema(metric="net_worth")
        )

        assert result.metric == "net_worth"

    async def test_raises_not_found_when_missing_and_revalidation_is_needed(self, uow):
        uow.analytics_widgets.find_one_or_none.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await AnalyticsWidgetService.update_widget_by_id(
                uow=uow, widget_id=999, widget_data=AnalyticsWidgetUpdateSchema(metric="sum")
            )

        assert exc_info.value.message == Messages.ANALYTICS_WIDGET_NOT_FOUND
        uow.analytics_widgets.edit_one.assert_not_called()


class TestDeleteWidgetById:
    async def test_deletes_widget(self, uow):
        uow.analytics_widgets.delete_one.return_value = make_analytics_widget_row(id=1)

        await AnalyticsWidgetService.delete_widget_by_id(uow=uow, widget_id=1)

        uow.analytics_widgets.delete_one.assert_awaited_once_with(_id=1)

    async def test_raises_not_found_when_missing(self, uow):
        uow.analytics_widgets.delete_one.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await AnalyticsWidgetService.delete_widget_by_id(uow=uow, widget_id=999)

        assert exc_info.value.message == Messages.ANALYTICS_WIDGET_NOT_FOUND


class TestUpdateLayout:
    async def test_updates_grid_placement_for_every_item(self, uow):
        uow.analytics_widgets.edit_one.side_effect = [
            make_analytics_widget_row(id=1, grid_x=6, grid_y=0),
            make_analytics_widget_row(id=2, grid_x=0, grid_y=0),
        ]
        uow.analytics_widgets.find_all.return_value = [
            make_analytics_widget_row(id=2, grid_x=0, grid_y=0),
            make_analytics_widget_row(id=1, grid_x=6, grid_y=0),
        ]

        result = await AnalyticsWidgetService.update_layout(
            uow=uow,
            layout_data=AnalyticsWidgetLayoutSchema(
                items=[
                    AnalyticsWidgetLayoutItemSchema(id=1, x=6, y=0, w=6, h=4),
                    AnalyticsWidgetLayoutItemSchema(id=2, x=0, y=0, w=6, h=4),
                ]
            ),
        )

        uow.analytics_widgets.edit_one.assert_any_call(
            id=1, data={"grid_x": 6, "grid_y": 0, "grid_w": 6, "grid_h": 4}
        )
        assert [w.id for w in result.items] == [2, 1]

    async def test_raises_not_found_when_an_id_does_not_exist(self, uow):
        uow.analytics_widgets.edit_one.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await AnalyticsWidgetService.update_layout(
                uow=uow,
                layout_data=AnalyticsWidgetLayoutSchema(
                    items=[AnalyticsWidgetLayoutItemSchema(id=999, x=0, y=0, w=6, h=4)]
                ),
            )

        assert exc_info.value.message == Messages.ANALYTICS_WIDGET_NOT_FOUND
