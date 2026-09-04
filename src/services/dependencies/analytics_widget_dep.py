from typing import Annotated

from fastapi import Depends

from src.services.analytics_widget_service import AnalyticsWidgetService


def get_analytics_widget_service() -> AnalyticsWidgetService:
    return AnalyticsWidgetService()


AnalyticsWidgetServiceDep = Annotated[
    AnalyticsWidgetService, Depends(get_analytics_widget_service)
]
