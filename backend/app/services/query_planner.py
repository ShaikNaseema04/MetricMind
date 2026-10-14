"""
MetricMind Dynamic Agentic Semantic Query Planner
Analyzes natural language questions, extracts metrics, dimensions, and entity filters,
supports comparisons, rankings, time-series, follow-up conversation context,
and provides honest boundaries for out-of-scope non-analytics queries.
"""
import re
from typing import Dict, Any, List, Optional, Tuple
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

# In-memory conversation state for multi-turn follow-ups
_CONVERSATION_HISTORY: Dict[str, QueryPlan] = {}

# Entity Dictionaries and Synonyms
COUNTRIES_MAP = {
    "USA": ["usa", "united states", "america", "us", "u.s.", "u.s.a."],
    "UK": ["uk", "united kingdom", "britain", "england", "great britain"],
    "Germany": ["germany", "deutschland"],
    "France": ["france"],
    "Canada": ["canada"],
    "Australia": ["australia"],
    "Japan": ["japan"],
    "India": ["india"],
}

REGIONS_MAP = {
    "North America": ["north america", "na"],
    "Europe": ["europe", "eu"],
    "Asia": ["asia", "apac"],
    "Oceania": ["oceania", "anz"],
}

CATEGORIES_MAP = {
    "Electronics": ["electronics", "electronic", "gadgets", "tech"],
    "Accessories": ["accessories", "accessory"],
    "Office": ["office", "furniture", "desks", "chairs", "workspace"],
}

CHANNELS_MAP = {
    "Online": ["online", "web", "website", "ecommerce", "e-commerce"],
    "Retail": ["retail", "store", "physical store", "in-store"],
    "Partner": ["partner", "partners", "reseller", "affiliate"],
}

SEGMENTS_MAP = {
    "Consumer": ["consumer", "consumers", "b2c", "individual"],
    "Small Business": ["small business", "small businesses", "smb", "smbs"],
    "Corporate": ["corporate", "enterprise", "b2b", "corporations"],
}

PRODUCTS_MAP = {
    "Laptop Pro 14": ["laptop pro 14", "laptop pro", "pro 14"],
    "Laptop Air 13": ["laptop air 13", "laptop air", "air 13"],
    "Smartphone X": ["smartphone x", "phone x"],
    "Smartphone Lite": ["smartphone lite", "phone lite"],
    "Tablet Pro": ["tablet pro", "tablet"],
    "Wireless Headphones": ["wireless headphones", "headphones", "headset"],
    "Smart Watch": ["smart watch", "smartwatch", "watch"],
    "Mechanical Keyboard": ["mechanical keyboard", "keyboard"],
    "Office Monitor": ["office monitor", "monitor", "screen"],
    "Ergonomic Chair": ["ergonomic chair", "office chair", "chair"],
    "Desk Lamp": ["desk lamp", "lamp"],
    "USB-C Dock": ["usb-c dock", "usb dock", "docking station", "dock"],
}

MONTHS_MAP = {
    "2025-01": ["january", "jan"],
    "2025-02": ["february", "feb"],
    "2025-03": ["march", "mar"],
    "2025-04": ["april", "apr"],
    "2025-05": ["may"],
    "2025-06": ["june", "jun"],
    "2025-07": ["july", "jul"],
    "2025-08": ["august", "aug"],
    "2025-09": ["september", "sep", "sept"],
    "2025-10": ["october", "oct"],
    "2025-11": ["november", "nov"],
    "2025-12": ["december", "dec"],
}

QUARTERS_MAP = {
    "2025-Q1": ["q1", "first quarter", "quarter 1"],
    "2025-Q2": ["q2", "second quarter", "quarter 2"],
    "2025-Q3": ["q3", "third quarter", "quarter 3"],
    "2025-Q4": ["q4", "fourth quarter", "quarter 4"],
}

def extract_entities_from_text(q: str) -> Dict[str, List[str]]:
    """Extracts known dataset entities from the user prompt."""
    entities: Dict[str, List[str]] = {
        "country": [],
        "region": [],
        "category": [],
        "sales_channel": [],
        "segment": [],
        "product_name": [],
        "month_name": [],
        "quarter": []
    }

    # Helper function using regex word boundary
    def find_matches(mapping: Dict[str, List[str]], target_list: List[str]):
        for canonical, synonyms in mapping.items():
            for syn in synonyms:
                pattern = r"(?:\b|^)" + re.escape(syn) + r"(?:\b|$)"
                if re.search(pattern, q):
                    if canonical not in target_list:
                        target_list.append(canonical)
                    break

    find_matches(COUNTRIES_MAP, entities["country"])
    find_matches(REGIONS_MAP, entities["region"])
    find_matches(CATEGORIES_MAP, entities["category"])
    find_matches(CHANNELS_MAP, entities["sales_channel"])
    find_matches(SEGMENTS_MAP, entities["segment"])
    find_matches(PRODUCTS_MAP, entities["product_name"])
    find_matches(MONTHS_MAP, entities["month_name"])
    find_matches(QUARTERS_MAP, entities["quarter"])

    return entities

def extract_limit(q: str, default: int = 10) -> int:
    """Extracts top N limit e.g. top 5, top 3, top 10."""
    m = re.search(r"\btop\s+(\d+)\b", q)
    if m:
        try:
            return min(max(int(m.group(1)), 1), 50)
        except ValueError:
            pass
    if "top three" in q or "top 3" in q:
        return 3
    if "top five" in q or "top 5" in q:
        return 5
    if "top ten" in q or "top 10" in q:
        return 10
    if "highest" in q or "best" in q or "leader" in q:
        return 5
    return default

def is_analytics_question(q: str, entities: Dict[str, List[str]]) -> bool:
    """Checks whether the question is within the scope of business analytics."""
    keywords = [
        "revenue", "profit", "margin", "sales", "cost", "quantity", "units",
        "orders", "order", "product", "products", "country", "countries",
        "region", "regions", "trend", "trends", "month", "monthly", "quarter",
        "quarterly", "year", "yearly", "annual", "customer", "customers",
        "segment", "channel", "channels", "compare", "comparison", "highest",
        "lowest", "top", "worst", "best", "breakdown", "distribution",
        "share", "growth", "decrease", "drop", "why", "average", "aov",
        "discount", "discounts", "total", "summary", "overview", "kpi",
        "performance", "metric", "metrics", "data", "how much", "how many"
    ]
    if any(kw in q for kw in keywords):
        return True
    # If any specific business entity was recognized
    if any(len(items) > 0 for items in entities.values()):
        return True
    return False

def plan_query(question: str, conversation_id: Optional[str] = None) -> QueryPlan:
    """
    Deterministically determines the business intent, metrics, and dimensions
    from the natural language question using semantic registry rules.
    Supports multi-turn context and handles out-of-scope queries cleanly.
    """
    q = question.lower().strip()
    entities = extract_entities_from_text(q)

    # Check for follow-up context if conversation_id is provided
    prev_plan = _CONVERSATION_HISTORY.get(conversation_id) if conversation_id else None

    # Check if question is outside analytics scope
    if not is_analytics_question(q, entities):
        return QueryPlan(
            intent="unsupported",
            metrics=[],
            dimensions=[],
            filters={},
            title="Non-Analytics Question",
            chart_type="kpi"
        )

    # 1. Root cause / Why did revenue decrease in August?
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

    # 2. Comparison between entities (e.g. Compare US and Germany, Compare Online vs Retail)
    is_comparison = ("compare" in q or " vs " in q or " versus " in q or "difference between" in q or "between" in q)
    for dim_key, dim_entities in [
        ("country", entities["country"]),
        ("region", entities["region"]),
        ("category", entities["category"]),
        ("sales_channel", entities["sales_channel"]),
        ("segment", entities["segment"]),
        ("product_name", entities["product_name"]),
    ]:
        if (is_comparison and len(dim_entities) >= 2) or (len(dim_entities) >= 2 and ("and" in q or "," in q)):
            metrics = ["revenue", "profit", "profit_margin"] if "profit" in q or "margin" in q else ["revenue", "profit"]
            return QueryPlan(
                intent="comparison",
                metrics=metrics,
                dimensions=[dim_key],
                filters={dim_key: dim_entities, "order_status": "Completed"},
                order_by="revenue",
                order_direction="DESC",
                chart_type="bar",
                title=f"Performance Comparison: {' vs '.join(dim_entities)}"
            )

    # 3. Time Series Trends: Quarterly, Monthly, Yearly
    is_time_trend = any(w in q for w in ["trend", "trends", "over time", "monthly", "quarterly", "yearly", "annual", "month by month", "by quarter"])
    
    if "quarter" in q or "quarterly" in q:
        metrics = ["revenue", "profit"] if "profit" in q else ["revenue"]
        filters: Dict[str, Any] = {"order_status": "Completed"}
        # Add single entity filters if mentioned (e.g. quarterly revenue for Electronics)
        if entities["category"]:
            filters["category"] = entities["category"][0]
        if entities["country"]:
            filters["country"] = entities["country"][0]
        return QueryPlan(
            intent="time_series",
            metrics=metrics,
            dimensions=["quarter"],
            filters=filters,
            order_by="quarter",
            order_direction="ASC",
            chart_type="line",
            title="Quarterly Financial Trend (2025)"
        )

    if "year" in q or "yearly" in q or "annual" in q:
        metrics = ["revenue", "profit", "profit_margin"]
        return QueryPlan(
            intent="time_series",
            metrics=metrics,
            dimensions=["order_year"],
            filters={"order_status": "Completed"},
            chart_type="bar",
            title="Annual Business Performance"
        )

    if is_time_trend or "month" in q:
        metrics = ["revenue", "profit"] if "profit" in q else ["revenue"]
        filters = {"order_status": "Completed"}
        if entities["country"]:
            filters["country"] = entities["country"][0]
        if entities["category"]:
            filters["category"] = entities["category"][0]
        if entities["region"]:
            filters["region"] = entities["region"][0]
        return QueryPlan(
            intent="time_series",
            metrics=metrics,
            dimensions=["month_name"],
            filters=filters,
            order_by="month_name",
            order_direction="ASC",
            chart_type="line",
            title="Monthly Revenue & Financial Performance Trends (2025)"
        )

    # 4. Rankings / Top N / Highest / Best Selling
    is_ranking = any(w in q for w in ["top", "highest", "best", "leading", "lowest", "worst", "leader"])

    # Top products
    if "product" in q or "products" in q or "selling" in q:
        limit = extract_limit(q, default=10)
        filters = {"order_status": "Completed"}
        if entities["region"]:
            filters["region"] = entities["region"][0]
        if entities["country"]:
            filters["country"] = entities["country"][0]
        if entities["category"]:
            filters["category"] = entities["category"][0]

        if "margin" in q:
            metrics = ["profit_margin", "profit", "revenue"]
            order_by = "profit_margin"
        elif "profit" in q:
            metrics = ["profit", "revenue"]
            order_by = "profit"
        elif "quantity" in q or "units" in q or "volume" in q:
            metrics = ["quantity", "revenue"]
            order_by = "quantity"
        else:
            metrics = ["revenue", "profit"]
            order_by = "revenue"

        title_qualifier = f" in {filters.get('country') or filters.get('region') or filters.get('category')}" if (entities["country"] or entities["region"] or entities["category"]) else ""
        return QueryPlan(
            intent="ranking",
            metrics=metrics,
            dimensions=["product_name"],
            filters=filters,
            order_by=order_by,
            order_direction="DESC",
            limit=limit,
            chart_type="horizontal_bar",
            title=f"Top {limit} Products by {order_by.replace('_', ' ').title()}{title_qualifier}"
        )

    # Top countries
    if ("country" in q or "countries" in q) and is_ranking:
        limit = extract_limit(q, default=5)
        metrics = ["revenue", "profit"] if "profit" in q else ["revenue"]
        return QueryPlan(
            intent="ranking",
            metrics=metrics,
            dimensions=["country"],
            filters={"order_status": "Completed"},
            order_by="revenue",
            order_direction="DESC",
            limit=limit,
            chart_type="bar",
            title=f"Top {limit} Countries by Revenue"
        )

    # Customer Segments
    if "segment" in q or "segments" in q:
        return QueryPlan(
            intent="distribution",
            metrics=["revenue", "profit"],
            dimensions=["segment"],
            filters={"order_status": "Completed"},
            order_by="revenue",
            order_direction="DESC",
            chart_type="donut",
            title="Revenue Contribution by Customer Segment"
        )

    # Sales Channels
    if "channel" in q or "channels" in q:
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

    # Categories
    if "category" in q or "categories" in q:
        metrics = ["revenue", "profit"] if "profit" in q else ["revenue"]
        return QueryPlan(
            intent="distribution",
            metrics=metrics,
            dimensions=["category"],
            filters={"order_status": "Completed"},
            order_by="revenue",
            order_direction="DESC",
            chart_type="donut",
            title="Revenue Distribution by Category"
        )

    # Top customers
    if "customer" in q or "customers" in q:
        limit = extract_limit(q, default=5)
        return QueryPlan(
            intent="ranking",
            metrics=["revenue", "order_count"],
            dimensions=["customer_name"],
            filters={"order_status": "Completed"},
            order_by="revenue",
            order_direction="DESC",
            limit=limit,
            chart_type="horizontal_bar",
            title=f"Top {limit} Customers by Revenue"
        )

    # 6. Dimension Breakdowns (e.g. revenue by country, profit by region)
    if "country" in q or "countries" in q:
        metrics = ["revenue", "profit", "profit_margin"] if "margin" in q or "profit" in q else ["revenue"]
        return QueryPlan(
            intent="dimension_breakdown",
            metrics=metrics,
            dimensions=["country"],
            filters={"order_status": "Completed"},
            order_by=metrics[0],
            order_direction="DESC",
            chart_type="bar",
            title="Revenue Performance by Country"
        )

    if "region" in q or "regions" in q:
        metrics = ["revenue", "profit"] if "profit" in q else ["revenue"]
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

    # 7. Single Entity Filter without group-by (e.g., "What is the revenue in United States?", "Profit of Laptop Pro 14")
    for dim_key, dim_entities, entity_label in [
        ("country", entities["country"], "Country"),
        ("region", entities["region"], "Region"),
        ("category", entities["category"], "Category"),
        ("product_name", entities["product_name"], "Product"),
        ("sales_channel", entities["sales_channel"], "Channel"),
        ("segment", entities["segment"], "Segment"),
    ]:
        if len(dim_entities) == 1:
            val = dim_entities[0]
            metrics = ["revenue", "profit", "profit_margin", "quantity", "order_count"]
            return QueryPlan(
                intent="kpi_summary",
                metrics=metrics,
                dimensions=[],
                filters={dim_key: val, "order_status": "Completed"},
                chart_type="kpi",
                title=f"{val} Performance Overview"
            )

    # 8. Follow-up handling with prior context
    if prev_plan and (entities["country"] or entities["region"] or entities["category"]):
        new_filters = dict(prev_plan.filters)
        if entities["country"]:
            new_filters["country"] = entities["country"][0]
        if entities["region"]:
            new_filters["region"] = entities["region"][0]
        if entities["category"]:
            new_filters["category"] = entities["category"][0]
        return QueryPlan(
            intent=prev_plan.intent,
            metrics=prev_plan.metrics,
            dimensions=prev_plan.dimensions,
            filters=new_filters,
            order_by=prev_plan.order_by,
            order_direction=prev_plan.order_direction,
            limit=prev_plan.limit,
            chart_type=prev_plan.chart_type,
            title=f"Refined Query Context ({list(new_filters.values())[0]})"
        )

    # 9. General Metric Summaries (e.g., "What is the total revenue and profit?", "What is the profit margin?")
    if "margin" in q:
        return QueryPlan(
            intent="kpi_summary",
            metrics=["profit_margin", "profit", "revenue"],
            dimensions=[],
            filters={"order_status": "Completed"},
            chart_type="kpi",
            title="Governed Profit Margin Overview"
        )

    if "profit" in q and "revenue" not in q:
        return QueryPlan(
            intent="kpi_summary",
            metrics=["profit", "revenue", "profit_margin"],
            dimensions=[],
            filters={"order_status": "Completed"},
            chart_type="kpi",
            title="Total Governed Profit Overview"
        )

    # Default total KPI overview
    plan = QueryPlan(
        intent="kpi_summary",
        metrics=["revenue", "profit", "profit_margin", "quantity", "order_count"],
        dimensions=[],
        filters={"order_status": "Completed"},
        chart_type="kpi",
        title="Executive Business KPI Overview"
    )

    if conversation_id:
        _CONVERSATION_HISTORY[conversation_id] = plan

    return plan
