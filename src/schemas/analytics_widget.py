from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict

from src.enums.enums import (
    AnalyticsWidgetMetricEnum,
    ChartTypeEnum,
    DateRangePresetEnum,
    LedgerReportGroupByEnum,
)


class AnalyticsWidgetFiltersSchema(BaseModel):
    date_range_preset: DateRangePresetEnum | None = None
    date_start: datetime | None = None
    date_end: datetime | None = None
    operation_types: list[str] | None = None
    currency_ticker: str | None = None
    category_ids: list[int] | None = None
    balance_ids: list[int] | None = None
    account_id: int | None = None


class AnalyticsWidgetResponseSchema(BaseModel):
    id: int
    title: str
    chart_type: ChartTypeEnum
    group_by: LedgerReportGroupByEnum
    metric: AnalyticsWidgetMetricEnum
    filters: AnalyticsWidgetFiltersSchema
    grid_x: int
    grid_y: int
    grid_w: int
    grid_h: int

    model_config = ConfigDict(from_attributes=True)


class AnalyticsWidgetListResponseSchema(BaseModel):
    items: list[AnalyticsWidgetResponseSchema]

    model_config = ConfigDict(from_attributes=True)


class AnalyticsWidgetCreateSchema(BaseModel):
    title: str
    chart_type: ChartTypeEnum
    group_by: LedgerReportGroupByEnum
    metric: AnalyticsWidgetMetricEnum
    filters: AnalyticsWidgetFiltersSchema = AnalyticsWidgetFiltersSchema()


class AnalyticsWidgetUpdateSchema(BaseModel):
    title: str | None = None
    chart_type: ChartTypeEnum | None = None
    group_by: LedgerReportGroupByEnum | None = None
    metric: AnalyticsWidgetMetricEnum | None = None
    filters: AnalyticsWidgetFiltersSchema | None = None


class AnalyticsWidgetLayoutItemSchema(BaseModel):
    id: int
    x: int
    y: int
    w: int
    h: int


class AnalyticsWidgetLayoutSchema(BaseModel):
    items: list[AnalyticsWidgetLayoutItemSchema]
