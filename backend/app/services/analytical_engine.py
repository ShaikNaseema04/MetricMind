"""
MetricMind Analytical Engine
Translates query plans into parameterized SQL queries against v_orders_enriched,
safely executes them, formats data, computes derived metrics, and generates
clear natural-language business explanations and chart metadata.
"""
import time
from datetime import datetime
from typing import Dict, Any, List, Tuple
from ..database.db import execute_query
from ..semantic.registry import METRIC_DEFINITIONS, DIMENSION_DEFINITIONS, format_metric_value
from ..models.schemas import (
    ChatResponse, ChartMeta, KpiItem, SqlTrace, ApiTrace, SecondaryBreakdown
)
from .query_planner import QueryPlan

def build_sql_from_plan(plan: QueryPlan) -> Tuple[str, Dict[str, Any], List[str]]:
    """
    Constructs a safe, parameterized SQL statement using approved metrics and dimensions.
    """
    select_clauses: List[str] = []
    metric_defs: List[str] = []
    
    # 1. Dimensions
    for dim_name in plan.dimensions:
        dim = DIMENSION_DEFINITIONS.get(dim_name)
        if dim:
            select_clauses.append(f"{dim.source_column} AS {dim_name}")
            
    # 2. Metrics
    for metric_name in plan.metrics:
        if metric_name == "revenue":
            select_clauses.append("ROUND(SUM(revenue), 2) AS revenue")
            metric_defs.append("Revenue = SUM(revenue)")
        elif metric_name == "gross_revenue":
            select_clauses.append("ROUND(SUM(gross_revenue), 2) AS gross_revenue")
            metric_defs.append("Gross Revenue = SUM(gross_revenue)")
        elif metric_name == "profit":
            select_clauses.append("ROUND(SUM(profit), 2) AS profit")
            metric_defs.append("Profit = SUM(profit)")
        elif metric_name == "total_cost":
            select_clauses.append("ROUND(SUM(total_cost), 2) AS total_cost")
            metric_defs.append("Total Cost = SUM(total_cost)")
        elif metric_name == "profit_margin":
            select_clauses.append(
                "ROUND((SUM(profit) / NULLIF(SUM(revenue), 0.0)) * 100.0, 2) AS profit_margin"
            )
            metric_defs.append("Profit Margin (%) = (SUM(profit) / SUM(revenue)) * 100")
        elif metric_name == "quantity":
            select_clauses.append("CAST(SUM(quantity) AS INTEGER) AS quantity")
            metric_defs.append("Quantity = SUM(quantity)")
        elif metric_name == "order_count":
            select_clauses.append("COUNT(order_id) AS order_count")
            metric_defs.append("Order Count = COUNT(order_id)")

    select_str = ", ".join(select_clauses) if select_clauses else "COUNT(*) AS total_records"
    
    # WHERE clauses with parameter binding
    where_clauses: List[str] = []
    params: Dict[str, Any] = {}
    
    if plan.filters:
        for key, val in plan.filters.items():
            param_key = f"param_{key}"
            where_clauses.append(f"{key} = :{param_key}")
            params[param_key] = val
            
    where_str = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    
    # GROUP BY
    group_str = ""
    if plan.dimensions:
        group_clauses = [DIMENSION_DEFINITIONS[d].source_column for d in plan.dimensions if d in DIMENSION_DEFINITIONS]
        if group_clauses:
            group_str = " GROUP BY " + ", ".join(group_clauses)
            
    # ORDER BY
    order_str = ""
    if plan.order_by:
        order_str = f" ORDER BY {plan.order_by} {plan.order_direction}"
        
    # LIMIT
    limit_str = ""
    if plan.limit:
        limit_str = f" LIMIT {int(plan.limit)}"
        
    sql = f"SELECT {select_str}\nFROM v_orders_enriched{where_str}{group_str}{order_str}{limit_str};"
    return sql, params, metric_defs

def execute_analytical_plan(plan: QueryPlan, question: str) -> ChatResponse:
    """
    Executes the analytical plan against SQLite and formats the complete ChatResponse.
    """
    start_time = time.perf_counter()
    sql, params, metric_defs = build_sql_from_plan(plan)
    
    # Safe execution
    rows = execute_query(sql, params)
    exec_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
    
    # Secondary breakdown if requested
    secondary: SecondaryBreakdown | None = None
    if plan.requires_secondary_breakdown and plan.investigation_dimension:
        sec_dim = plan.investigation_dimension
        sec_sql = f"""
        SELECT 
            {sec_dim},
            ROUND(SUM(revenue), 2) AS revenue,
            ROUND(SUM(profit), 2) AS profit,
            ROUND((SUM(profit) / NULLIF(SUM(revenue), 0.0)) * 100.0, 2) AS profit_margin
        FROM v_orders_enriched
        WHERE order_status = 'Completed'
        GROUP BY {sec_dim}
        ORDER BY revenue DESC;
        """
        sec_rows = execute_query(sec_sql)
        secondary = SecondaryBreakdown(
            dimension=sec_dim,
            title=f"Secondary Breakdown by {sec_dim.replace('_', ' ').title()}",
            data=sec_rows,
            explanation=f"Investigation into distribution across {sec_dim.replace('_', ' ')} based on verified completed orders."
        )

    # Generate natural language explanation and KPI items
    explanation, kpis = generate_business_insight(plan, rows, secondary)
    
    # Build chart metadata
    chart_meta = None
    if plan.chart_type != "kpi" and len(rows) > 0:
        x_key = plan.dimensions[0] if plan.dimensions else None
        y_keys = [m for m in plan.metrics if m != "order_count"] or plan.metrics
        chart_meta = ChartMeta(
            chart_type=plan.chart_type,  # type: ignore
            title=plan.title or "Analytical Result",
            x_key=x_key,
            y_keys=y_keys,
            series_names=[METRIC_DEFINITIONS.get(m, m).display_name if isinstance(METRIC_DEFINITIONS.get(m), object) and hasattr(METRIC_DEFINITIONS.get(m), 'display_name') else m.title() for m in y_keys],
            x_label=x_key.replace("_", " ").title() if x_key else None,
            y_label="Value"
        )
    elif plan.chart_type == "kpi":
        chart_meta = ChartMeta(
            chart_type="kpi",
            title=plan.title,
            x_key=None,
            y_keys=plan.metrics,
            series_names=[m.title() for m in plan.metrics]
        )

    sql_trace = SqlTrace(
        sql=sql,
        params=params,
        metric_definitions=metric_defs,
        execution_engine="SQLite 3.x Analytical Mart (v_orders_enriched)",
        rows_returned=len(rows),
        is_preview=False
    )
    
    api_trace = ApiTrace(
        endpoint="/api/chat",
        method="POST",
        request_payload={"question": question, "plan": plan.to_dict()},
        status_code=200,
        execution_time_ms=exec_time_ms,
        timestamp=datetime.utcnow().isoformat() + "Z",
        sanitized=True
    )

    # Map chart to analyticsUtils.ts ChartMeta format: { type: ..., xKey: ..., yKeys: ..., title: ... }
    chart_alias = None
    if chart_meta:
        chart_alias = {
            "type": "pie" if chart_meta.chart_type == "donut" else chart_meta.chart_type,
            "xKey": chart_meta.x_key,
            "yKeys": chart_meta.y_keys,
            "title": chart_meta.title,
        }

    return ChatResponse(
        question=question,
        explanation=explanation,
        answer=explanation,
        response=explanation,
        message=explanation,
        data=rows,
        results=rows,
        sql=sql,
        generated_sql=sql,
        chart=chart_alias,
        chart_meta=chart_meta,
        kpi_items=kpis,
        sql_trace=sql_trace,
        api_trace=api_trace,
        secondary_breakdown=secondary,
        query_plan=plan.to_dict(),
    )

def generate_business_insight(
    plan: QueryPlan,
    rows: List[Dict[str, Any]],
    secondary: SecondaryBreakdown | None = None
) -> Tuple[str, List[KpiItem]]:
    """
    Produces concise, factual natural language narrative and KPI cards.
    """
    kpis: List[KpiItem] = []
    
    if not rows:
        return "No matching completed records were found in the dataset for this query.", []

    # KPI summary mode (1 row, no dimensions)
    if plan.intent == "kpi_summary" or (not plan.dimensions and len(rows) == 1):
        row = rows[0]
        narratives = []
        
        if "revenue" in row:
            rev_val = row["revenue"]
            fmt_rev = format_metric_value(rev_val, "currency")
            kpis.append(KpiItem(
                label="Total Revenue",
                value=rev_val,
                formatted_value=fmt_rev,
                formattedValue=fmt_rev,
                description="Governed net revenue from completed transactions"
            ))
            narratives.append(f"Total Revenue reached **{fmt_rev}**")
            
        if "profit" in row:
            profit_val = row["profit"]
            fmt_profit = format_metric_value(profit_val, "currency")
            kpis.append(KpiItem(
                label="Total Profit",
                value=profit_val,
                formatted_value=fmt_profit,
                formattedValue=fmt_profit,
                description="Net profit after deducting product and shipping costs"
            ))
            narratives.append(f"Total Profit is **{fmt_profit}**")

        if "profit_margin" in row:
            margin_val = row["profit_margin"]
            fmt_margin = format_metric_value(margin_val, "percentage")
            kpis.append(KpiItem(
                label="Profit Margin",
                value=margin_val,
                formatted_value=fmt_margin,
                formattedValue=fmt_margin,
                description="Overall profit margin percentage (Profit / Revenue)"
            ))
            narratives.append(f"Profit Margin is **{fmt_margin}**")
            
        if "quantity" in row:
            qty_val = row["quantity"]
            fmt_qty = format_metric_value(qty_val, "integer")
            kpis.append(KpiItem(
                label="Units Sold",
                value=qty_val,
                formatted_value=fmt_qty,
                formattedValue=fmt_qty,
                description="Total volume of units sold"
            ))
            narratives.append(f"totaling **{fmt_qty} units** sold")

        explanation = f"Based on authoritative analysis of the 2025 dataset, {', '.join(narratives)} across completed orders."
        return explanation, kpis

    # Root Cause / Trend Analysis
    if plan.intent == "root_cause_investigation":
        first_month = rows[0]
        last_month = rows[-1]
        rev_start = first_month.get("revenue", 0)
        rev_end = last_month.get("revenue", 0)
        
        explanation = (
            f"Monthly revenue analysis indicates seasonality across 2025. "
            f"Revenue started at **{format_metric_value(rev_start, 'currency')}** in {first_month.get('month_name')} "
            f"and closed at **{format_metric_value(rev_end, 'currency')}** in {last_month.get('month_name')}. "
        )
        if secondary and secondary.data:
            top_cat = secondary.data[0]
            cat_name = top_cat.get("category", "Products")
            cat_rev = format_metric_value(top_cat.get("revenue", 0), "currency")
            explanation += (
                f"Secondary breakdown shows **{cat_name}** is the primary financial driver with **{cat_rev}** in revenue. "
                f"*Note: While seasonal and volume shifts are visible, the dataset does not contain external macroeconomic, advertising, or churn signals to definitively establish non-operational causes.*"
            )
        return explanation, kpis

    # Time series mode (monthly trends)
    if plan.intent == "time_series":
        total_rev = sum(r.get("revenue", 0) for r in rows)
        fmt_total = format_metric_value(total_rev, "currency")
        peak_month = max(rows, key=lambda r: r.get("revenue", 0))
        peak_val = format_metric_value(peak_month.get("revenue", 0), "currency")
        
        kpis.append(KpiItem(
            label="Peak Month",
            value=peak_month.get("month_name"),
            formatted_value=str(peak_month.get("month_name")),
            formattedValue=str(peak_month.get("month_name")),
            description=f"Highest revenue month at {peak_val}"
        ))
        kpis.append(KpiItem(
            label="2025 Annual Revenue",
            value=total_rev,
            formatted_value=fmt_total,
            formattedValue=fmt_total,
            description="Sum of all completed monthly revenue in 2025"
        ))
        explanation = (
            f"Monthly revenue across 2025 totaled **{fmt_total}**. "
            f"Peak performance occurred in **{peak_month.get('month_name')}** generating **{peak_val}**."
        )
        return explanation, kpis

    # Ranking mode (e.g., top country, top product)
    if plan.intent == "ranking":
        dim = plan.dimensions[0]
        top_row = rows[0]
        top_name = top_row.get(dim, "Unknown")
        top_metric = plan.order_by or plan.metrics[0]
        metric_val = top_row.get(top_metric, 0)
        fmt_val = format_metric_value(metric_val, "currency" if "profit" in top_metric or "revenue" in top_metric else "integer")
        
        # Build Top 1 KPI
        kpis.append(KpiItem(
            label=f"Top {dim.replace('_', ' ').title()}",
            value=top_name,
            formatted_value=str(top_name),
            formattedValue=str(top_name),
            description=f"Leader with {fmt_val} in {top_metric.replace('_', ' ')}"
        ))
        
        explanation = f"**{top_name}** leads the dataset with **{fmt_val}** in {top_metric.replace('_', ' ')}."
        if len(rows) > 1:
            second_row = rows[1]
            sec_name = second_row.get(dim, "Unknown")
            sec_val = format_metric_value(second_row.get(top_metric, 0), "currency" if "profit" in top_metric or "revenue" in top_metric else "integer")
            explanation += f" It is followed by **{sec_name}** at **{sec_val}**."
        return explanation, kpis
        return explanation, kpis

    # Time series or Dimension breakdown general
    dim = plan.dimensions[0]
    total_val = sum(r.get(plan.metrics[0], 0) for r in rows)
    fmt_total = format_metric_value(total_val, "currency" if "revenue" in plan.metrics[0] or "profit" in plan.metrics[0] else "integer")
    
    explanation = (
        f"Performance across {len(rows)} {dim.replace('_', ' ')} segments represents a combined "
        f"**{fmt_total}** in {plan.metrics[0].replace('_', ' ')}."
    )
    return explanation, kpis
