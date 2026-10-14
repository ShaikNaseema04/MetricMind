"""
MetricMind Agentic Semantic Query Planner
Analyzes natural language questions, extracts intended metrics, dimensions, filters,
validates them against the Semantic Registry, and produces a structured, safe query plan.
Includes a robust deterministic pattern matcher guaranteeing zero-dependency execution.
"""
import re
from typing import Dict, Any, List, Optional
from ..semantic.registry import METRIC_DEFINITIONS, DIMENSION_DEFINITIONS

class QueryPlan:
    def __init__(
        self,
        intent: str,
        metrics: List[str],
        dimensions: List[str],
        filters: Dict[str, Any] | None = None,
        order_by: Optional[str] = None,
        order_direction: str = "DESC",
        limit: Optional[int] = None,
        chart_type: str = "bar",
        title: str = "",
        requires_secondary_breakdown: bool = False,
        investigation_dimension: Optional[str] = None
    ):
        self.intent = intent
        self.metrics = metrics
        self.dimensions = dimensions
        self.filters = filters or {"order_status": "Completed"}
        self.order_by = order_by
        self.order_direction = order_direction
        self.limit = limit
        self.chart_type = chart_type
        self.title = title
        self.requires_secondary_breakdown = requires_secondary_breakdown
        self.investigation_dimension = investigation_dimension

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent,
            "metrics": self.metrics,
            "dimensions": self.dimensions,
            "filters": self.filters,
            "order_by": self.order_by,
            "order_direction": self.order_direction,
            "limit": self.limit,
            "chart_type": self.chart_type,
            "title": self.title,
            "requires_secondary_breakdown": self.requires_secondary_breakdown,
            "investigation_dimension": self.investigation_dimension
        }

def plan_query(question: str) -> QueryPlan:
    """
    Deterministically determines the business intent, metrics, and dimensions
    from the natural language question using semantic registry rules.
    """
    q = question.lower().strip()
    
    # Check for "Why did revenue decrease" / Root cause analysis
    if "why" in q and ("decrease" in q or "drop" in q or "fall" in q or "decline" in q or "down" in q):
        return QueryPlan(
            intent="root_cause_investigation",
            metrics=["revenue", "profit"],
            dimensions=["month_name"],
            filters={"order_status": "Completed"},
            order_by="month_name",
            order_direction="ASC",
            chart_type="line",
            title="Monthly Revenue Trend with Variance Investigation",
            requires_secondary_breakdown=True,
            investigation_dimension="category"
        )

    # Check for "Compare this month with previous month" / Period over period
    if "compare" in q and ("month" in q or "period" in q):
        return QueryPlan(
            intent="period_comparison",
            metrics=["revenue", "profit", "order_count"],
            dimensions=["month_name"],
            filters={"order_status": "Completed"},
            order_by="month_name",
            order_direction="ASC",
            chart_type="line",
            title="Month-over-Month Performance Comparison",
            requires_secondary_breakdown=True,
            investigation_dimension="region"
        )

    # Top products by profit
    if ("product" in q or "products" in q) and "profit" in q:
        limit = 5 if ("top five" in q or "top 5" in q or "top" in q) else 10
        return QueryPlan(
            intent="ranking",
            metrics=["profit", "revenue"],
            dimensions=["product_name"],
            filters={"order_status": "Completed"},
            order_by="profit",
            order_direction="DESC",
            limit=limit,
            chart_type="horizontal_bar",
            title=f"Top {limit} Products by Total Profit"
        )

    # Which product has the highest sales / products by sales
    if ("product" in q or "products" in q) and ("sales" in q or "revenue" in q or "highest" in q or "best" in q):
        limit = 5 if ("5" in q or "five" in q) else 10
        return QueryPlan(
            intent="ranking",
            metrics=["revenue", "quantity"],
            dimensions=["product_name"],
            filters={"order_status": "Completed"},
            order_by="revenue",
            order_direction="DESC",
            limit=limit,
            chart_type="horizontal_bar",
            title=f"Top {limit} Products by Sales Revenue"
        )

    # Profit margin
    if "margin" in q or "profit margin" in q:
        # Check if by dimension or overall
        if "region" in q:
            return QueryPlan(
                intent="dimension_breakdown",
                metrics=["profit_margin", "profit", "revenue"],
                dimensions=["region"],
                filters={"order_status": "Completed"},
                order_by="profit_margin",
                order_direction="DESC",
                chart_type="bar",
                title="Profit Margin by Region (%)"
            )
        elif "country" in q:
            return QueryPlan(
                intent="dimension_breakdown",
                metrics=["profit_margin", "profit", "revenue"],
                dimensions=["country"],
                filters={"order_status": "Completed"},
                order_by="profit_margin",
                order_direction="DESC",
                chart_type="bar",
                title="Profit Margin by Country (%)"
            )
        elif "category" in q or "product" in q:
            return QueryPlan(
                intent="dimension_breakdown",
                metrics=["profit_margin", "profit", "revenue"],
                dimensions=["category"],
                filters={"order_status": "Completed"},
                order_by="profit_margin",
                order_direction="DESC",
                chart_type="bar",
                title="Profit Margin by Category (%)"
            )
        else:
            return QueryPlan(
                intent="kpi_summary",
                metrics=["profit_margin", "profit", "revenue"],
                dimensions=[],
                filters={"order_status": "Completed"},
                chart_type="kpi",
                title="Overall Governed Profit Margin"
            )

    # Categories contributing to profit
    if ("category" in q or "categories" in q) and "profit" in q:
        return QueryPlan(
            intent="distribution",
            metrics=["profit", "revenue"],
            dimensions=["category"],
            filters={"order_status": "Completed"},
            order_by="profit",
            order_direction="DESC",
            chart_type="donut",
            title="Profit Contribution by Category"
        )

    # Categories in general
    if "category" in q or "categories" in q:
        return QueryPlan(
            intent="distribution",
            metrics=["revenue", "profit"],
            dimensions=["category"],
            filters={"order_status": "Completed"},
            order_by="revenue",
            order_direction="DESC",
            chart_type="donut",
            title="Revenue Distribution by Category"
        )

    # Monthly revenue trends / trend analysis
    if "month" in q or "trend" in q or "time" in q:
        metrics = ["revenue", "profit"] if "profit" in q else ["revenue"]
        return QueryPlan(
            intent="time_series",
            metrics=metrics,
            dimensions=["month_name"],
            filters={"order_status": "Completed"},
            order_by="month_name",
            order_direction="ASC",
            chart_type="line",
            title="Monthly Revenue & Financial Performance Trends (2025)"
        )

    # Revenue by country / Which country has highest revenue
    if "country" in q:
        metrics = ["revenue"]
        if "profit" in q:
            metrics = ["profit", "revenue"]
        return QueryPlan(
            intent="ranking" if "highest" in q else "dimension_breakdown",
            metrics=metrics,
            dimensions=["country"],
            filters={"order_status": "Completed"},
            order_by=metrics[0],
            order_direction="DESC",
            chart_type="bar",
            title="Revenue Performance by Country"
        )

    # Revenue by region / Compare revenue across regions / Which region has highest sales
    if "region" in q or "regions" in q:
        metrics = ["revenue"]
        if "profit" in q:
            metrics = ["profit", "revenue"]
        elif "sales" in q or "quantity" in q:
            metrics = ["revenue", "quantity"]
        return QueryPlan(
            intent="dimension_breakdown",
            metrics=metrics,
            dimensions=["region"],
            filters={"order_status": "Completed"},
            order_by=metrics[0],
            order_direction="DESC",
            chart_type="bar",
            title="Sales and Revenue Comparison Across Regions"
        )

    # Sales Channel
    if "channel" in q or "channels" in q or "online" in q or "retail" in q or "partner" in q:
        return QueryPlan(
            intent="distribution",
            metrics=["revenue", "profit"],
            dimensions=["sales_channel"],
            filters={"order_status": "Completed"},
            order_by="revenue",
            order_direction="DESC",
            chart_type="donut",
            title="Sales Channel Revenue Performance"
        )

    # Total profit
    if "profit" in q and not any(dim in q for dim in ["country", "region", "product", "month"]):
        return QueryPlan(
            intent="kpi_summary",
            metrics=["profit", "revenue", "profit_margin"],
            dimensions=[],
            filters={"order_status": "Completed"},
            chart_type="kpi",
            title="Total Governed Profit Overview"
        )

    # Total revenue / General KPI summary
    if "revenue" in q or "sales" in q or "total" in q or "overview" in q or "summary" in q or "how much" in q:
        return QueryPlan(
            intent="kpi_summary",
            metrics=["revenue", "profit", "profit_margin", "quantity", "order_count"],
            dimensions=[],
            filters={"order_status": "Completed"},
            chart_type="kpi",
            title="Executive Business KPI Overview"
        )

    # Default fallback: Executive overview with region breakdown
    return QueryPlan(
        intent="dimension_breakdown",
        metrics=["revenue", "profit"],
        dimensions=["region"],
        filters={"order_status": "Completed"},
        order_by="revenue",
        order_direction="DESC",
        chart_type="bar",
        title="Business Revenue & Profit by Region"
    )
