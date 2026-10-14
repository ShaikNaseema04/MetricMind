"""
MetricMind Centralized Semantic Layer Registry
Defines approved governed business metrics, dimensions, aggregation rules, and validation constraints.
Ensures identical and consistent calculations across chat, dashboards, API endpoints, and SQL queries.
"""
from typing import Dict, List, Optional
from ..models.schemas import MetricDefinition, DimensionDefinition, SemanticRegistryResponse

METRIC_DEFINITIONS: Dict[str, MetricDefinition] = {
    "revenue": MetricDefinition(
        name="revenue",
        display_name="Total Revenue",
        description="Total monetary revenue generated from completed orders (net of discount).",
        formula="SUM(revenue) WHERE order_status = 'Completed'",
        aggregation="SUM",
        required_columns=["revenue", "order_status"],
        format="currency"
    ),
    "gross_revenue": MetricDefinition(
        name="gross_revenue",
        display_name="Gross Revenue",
        description="Total monetary revenue before applying customer discounts for completed orders.",
        formula="SUM(gross_revenue) WHERE order_status = 'Completed'",
        aggregation="SUM",
        required_columns=["gross_revenue", "order_status"],
        format="currency"
    ),
    "total_cost": MetricDefinition(
        name="total_cost",
        display_name="Total Cost",
        description="Sum of product costs and shipping costs for completed orders.",
        formula="SUM(total_cost) WHERE order_status = 'Completed'",
        aggregation="SUM",
        required_columns=["total_cost", "order_status"],
        format="currency"
    ),
    "profit": MetricDefinition(
        name="profit",
        display_name="Total Profit",
        description="Net monetary profit (Revenue minus Total Cost) for completed orders.",
        formula="SUM(profit) WHERE order_status = 'Completed'",
        aggregation="SUM",
        required_columns=["profit", "order_status"],
        format="currency"
    ),
    "profit_margin": MetricDefinition(
        name="profit_margin",
        display_name="Profit Margin (%)",
        description="Net profit expressed as a percentage of total revenue for completed orders. Calculated as (Profit / Revenue) * 100.",
        formula="(SUM(profit) / NULLIF(SUM(revenue), 0)) * 100 WHERE order_status = 'Completed'",
        aggregation="DERIVED",
        required_columns=["profit", "revenue", "order_status"],
        format="percentage"
    ),
    "quantity": MetricDefinition(
        name="quantity",
        display_name="Total Quantity Sold",
        description="Total volume of units sold across completed transactions.",
        formula="SUM(quantity) WHERE order_status = 'Completed'",
        aggregation="SUM",
        required_columns=["quantity", "order_status"],
        format="integer"
    ),
    "order_count": MetricDefinition(
        name="order_count",
        display_name="Completed Orders",
        description="Total count of completed transactions.",
        formula="COUNT(order_id) WHERE order_status = 'Completed'",
        aggregation="COUNT",
        required_columns=["order_id", "order_status"],
        format="integer"
    ),
    "avg_order_value": MetricDefinition(
        name="avg_order_value",
        display_name="Average Order Value",
        description="Average revenue per completed order.",
        formula="SUM(revenue) / NULLIF(COUNT(order_id), 0) WHERE order_status = 'Completed'",
        aggregation="DERIVED",
        required_columns=["revenue", "order_id", "order_status"],
        format="currency"
    )
}

DIMENSION_DEFINITIONS: Dict[str, DimensionDefinition] = {
    "country": DimensionDefinition(
        name="country",
        display_name="Country",
        source_column="country",
        data_type="string",
        description="Customer destination country (e.g., USA, UK, India, Canada, Germany, France, Japan, Australia)."
    ),
    "region": DimensionDefinition(
        name="region",
        display_name="Region",
        source_column="region",
        data_type="string",
        description="Geographic global territory (Asia, Europe, North America, Oceania)."
    ),
    "product_name": DimensionDefinition(
        name="product_name",
        display_name="Product Name",
        source_column="product_name",
        data_type="string",
        description="Name of the sold product from products catalogue."
    ),
    "category": DimensionDefinition(
        name="category",
        display_name="Category",
        source_column="category",
        data_type="string",
        description="Product categorization (Electronics, Accessories, Furniture)."
    ),
    "month_name": DimensionDefinition(
        name="month_name",
        display_name="Month",
        source_column="strftime('%Y-%m', order_date)",
        data_type="string",
        description="Calendar month for time-series trend analysis (YYYY-MM)."
    ),
    "sales_channel": DimensionDefinition(
        name="sales_channel",
        display_name="Sales Channel",
        source_column="sales_channel",
        data_type="string",
        description="Distribution channel (Online, Partner, Retail)."
    ),
    "order_status": DimensionDefinition(
        name="order_status",
        display_name="Order Status",
        source_column="order_status",
        data_type="string",
        description="Status of order: Completed, Returned, or Cancelled."
    )
}

GOVERNED_RULES: List[str] = [
    "Governed Rule 1: Business metrics (Revenue, Profit, Quantity, Margin) only aggregate 'Completed' transactions unless the user explicitly requests all orders or returns.",
    "Governed Rule 2: Profit Margin is strictly calculated as (SUM(profit) / SUM(revenue)) * 100, preventing invalid average-of-averages.",
    "Governed Rule 3: Single source of truth. Joins between orders, products, and customers use validated foreign keys (product_id, customer_id) with 1-to-1 cardinality to prevent double counting.",
    "Governed Rule 4: Zero fabrication. Missing columns or uncomputable metrics must be clearly communicated as unsupported rather than fabricated.",
    "Governed Rule 5: Architecture ready for dbt and Cube.dev semantic manifests via unified metadata export."
]

def get_semantic_registry() -> SemanticRegistryResponse:
    return SemanticRegistryResponse(
        metrics=list(METRIC_DEFINITIONS.values()),
        dimensions=list(DIMENSION_DEFINITIONS.values()),
        governed_rules=GOVERNED_RULES
    )

def format_metric_value(val: float | int | str | None, metric_format: str) -> str:
    if val is None:
        return "N/A"
    if isinstance(val, str):
        try:
            val = float(val)
        except ValueError:
            return val
    if metric_format == "currency":
        if abs(val) >= 1_000_000:
            return f"${val / 1_000_000:.2f}M"
        elif abs(val) >= 1_000:
            return f"${val / 1_000:.2f}K"
        else:
            return f"${val:,.2f}"
    elif metric_format == "percentage":
        return f"{val:.2f}%"
    elif metric_format == "integer":
        return f"{int(val):,}"
    return f"{val:,.2f}"
