"""
MetricMind Analytical Engine
Translates query plans into parameterized SQL queries against v_orders_enriched,
safely executes them, formats data, computes derived metrics, and generates
clear natural-language business explanations and chart metadata.
"""
import time
from datetime import datetime, timezone
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
    Supports single values, multiple values (IN clause), and complex filters.
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
        elif metric_name == "avg_order_value":
            select_clauses.append("ROUND(SUM(revenue) / NULLIF(COUNT(order_id), 0.0), 2) AS avg_order_value")
            metric_defs.append("Average Order Value = SUM(revenue) / COUNT(order_id)")
        elif metric_name == "discount_pct" or metric_name == "avg_discount":
            select_clauses.append("ROUND(AVG(discount_pct) * 100.0, 2) AS discount_pct")
            metric_defs.append("Average Discount (%) = AVG(discount_pct) * 100")

    select_str = ", ".join(select_clauses) if select_clauses else "COUNT(*) AS total_records"
    
    # WHERE clauses with parameter binding
    where_clauses: List[str] = []
    params: Dict[str, Any] = {}
    
    if plan.filters:
        for key, val in plan.filters.items():
            param_key = f"param_{key}"
            if isinstance(val, (list, tuple, set)):
                in_placeholders = []
                for i, v in enumerate(val):
                    p_name = f"{param_key}_{i}"
                    in_placeholders.append(f":{p_name}")
                    params[p_name] = v
                where_clauses.append(f"{key} IN ({', '.join(in_placeholders)})")
            else:
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

    # Handle out-of-scope non-analytics questions honestly without fake answers
    if plan.intent == "unsupported":
        unsupported_msg = (
            "MetricMind is an enterprise Agentic Semantic BI Engine configured for corporate transactional analytics "
            "(revenue, profit, unit volumes, order status, product catalog, customer segments, and geographical performance across 2025).\n\n"
            "The question you entered appears to be outside this business dataset. Here are some questions you can ask right now:\n\n"
            "• *\"What is the total revenue and profit?\"*\n"
            "• *\"What is the revenue and profit in United States?\"*\n"
            "• *\"Show revenue and profit by country\"*\n"
            "• *\"Quarterly revenue trend for 2025\"*\n"
            "• *\"Compare USA and Germany\"*\n"
            "• *\"Top 5 products by profit margin\"*\n"
            "• *\"Revenue by sales channel\"*\n"
            "• *\"Why did revenue decrease in August?\"*"
        )
        dummy_sql = SqlTrace(
            sql="-- Out of scope: No SQL generated for non-analytics question",
            params={},
            metric_definitions=[],
            execution_engine="N/A",
            rows_returned=0,
            is_preview=False
        )
        dummy_api = ApiTrace(
            endpoint="/api/chat",
            method="POST",
            request_payload={"question": question},
            status_code=200,
            execution_time_ms=0.0
        )
        return ChatResponse(
            question=question,
            explanation=unsupported_msg,
            answer=unsupported_msg,
            response=unsupported_msg,
            message=unsupported_msg,
            data=[],
            results=[],
            sql="-- No SQL generated: question is outside the scope of business analytics",
            generated_sql="-- No SQL generated: question is outside the scope of business analytics",
            chart=None,
            chart_meta=None,
            kpi_items=[],
            sql_trace=dummy_sql,
            api_trace=dummy_api,
            secondary_breakdown=None,
            query_plan=plan.to_dict(),
        )

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
        ORDER BY revenue DESC
        LIMIT 5;
        """
        sec_rows = execute_query(sec_sql)
        secondary = SecondaryBreakdown(
            dimension=sec_dim,
            title=f"Secondary Investigation: {sec_dim.title()} Breakdown",
            explanation=f"Revenue and margin contribution by {sec_dim} during the analyzed timeframe.",
            data=sec_rows
        )

    # Generate insights and KPI items
    explanation, kpis = generate_business_insight(plan, rows, secondary)

    # Format ChartMeta
    chart_meta: ChartMeta | None = None
    if plan.chart_type != "kpi" and plan.dimensions and rows:
        x_key = plan.dimensions[0]
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
        timestamp=datetime.now(timezone.utc).isoformat(),
        sanitized=True
    )

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
    Produces concise, factual natural language narrative and KPI cards based on the actual query results.
    """
    kpis: List[KpiItem] = []
    
    if not rows:
        filter_desc = ", ".join(f"{k}: {v}" for k, v in plan.filters.items()) if plan.filters else "specified filters"
        return f"No matching completed records were found in the dataset for {filter_desc}.", []

    # 1. Comparison Intent (e.g., Comparing USA vs Germany, or Online vs Retail)
    if plan.intent == "comparison" and len(rows) >= 2:
        dim = plan.dimensions[0]
        comp_lines: List[str] = []
        for r in rows:
            name = str(r.get(dim, "Unknown"))
            rev = r.get("revenue", 0)
            prof = r.get("profit", 0)
            margin = r.get("profit_margin", 0)
            fmt_rev = format_metric_value(rev, "currency")
            fmt_prof = format_metric_value(prof, "currency")
            fmt_margin = format_metric_value(margin, "percentage")
            comp_lines.append(f"• **{name}**: Revenue of **{fmt_rev}**, Profit of **{fmt_prof}** (Margin: {fmt_margin})")
            kpis.append(KpiItem(
                label=f"{name} Revenue",
                value=rev,
                formatted_value=fmt_rev,
                formattedValue=fmt_rev,
                description=f"Profit: {fmt_prof} ({fmt_margin} margin)"
            ))
        explanation = f"Comparative performance analysis across **{dim.replace('_', ' ').title()}**:\n\n" + "\n".join(comp_lines)
        return explanation, kpis

    # 2. KPI Summary Mode (1 row, no dimensions) - overall or single filtered entity (e.g. USA or Laptop Pro 14)
    if plan.intent == "kpi_summary" or (not plan.dimensions and len(rows) == 1):
        row = rows[0]
        narratives = []
        
        # Check if single entity was filtered
        entity_name = ""
        for fk, fv in plan.filters.items():
            if fk != "order_status" and isinstance(fv, str):
                entity_name = fv
                break

        prefix = f"In **{entity_name}**, " if entity_name else "Based on authoritative analysis of the 2025 dataset, "

        if "revenue" in row:
            rev_val = row["revenue"]
            fmt_rev = format_metric_value(rev_val, "currency")
            kpis.append(KpiItem(
                label=f"{entity_name} Revenue" if entity_name else "Total Revenue",
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
                label=f"{entity_name} Profit" if entity_name else "Total Profit",
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

        if "order_count" in row:
            ord_val = row["order_count"]
            fmt_ord = format_metric_value(ord_val, "integer")
            kpis.append(KpiItem(
                label="Completed Orders",
                value=ord_val,
                formatted_value=fmt_ord,
                formattedValue=fmt_ord,
                description="Completed transaction volume"
            ))

        explanation = f"{prefix}{', '.join(narratives)} across completed orders."
        return explanation, kpis

    # 3. Root Cause / Trend Analysis
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

    # 4. Time series mode (monthly or quarterly trends)
    if plan.intent == "time_series":
        dim = plan.dimensions[0]
        total_rev = sum(r.get("revenue", 0) for r in rows)
        fmt_total = format_metric_value(total_rev, "currency")
        peak_row = max(rows, key=lambda r: r.get("revenue", 0))
        peak_period = peak_row.get(dim)
        peak_val = format_metric_value(peak_row.get("revenue", 0), "currency")
        
        kpis.append(KpiItem(
            label=f"Peak {dim.replace('_', ' ').title()}",
            value=peak_period,
            formatted_value=str(peak_period),
            formattedValue=str(peak_period),
            description=f"Highest revenue period at {peak_val}"
        ))
        kpis.append(KpiItem(
            label="Total Analyzed Revenue",
            value=total_rev,
            formatted_value=fmt_total,
            formattedValue=fmt_total,
            description="Combined revenue across the selected timeframe"
        ))
        explanation = (
            f"Total revenue across {len(rows)} {dim.replace('_', ' ')} periods reached **{fmt_total}**. "
            f"Peak performance occurred in **{peak_period}** generating **{peak_val}**."
        )
        return explanation, kpis

    # 5. Ranking mode (e.g., top country, top product)
    if plan.intent == "ranking":
        dim = plan.dimensions[0]
        top_row = rows[0]
        top_name = top_row.get(dim, "Unknown")
        top_metric = plan.order_by or plan.metrics[0]
        metric_val = top_row.get(top_metric, 0)
        fmt_val = format_metric_value(metric_val, "percentage" if "margin" in top_metric else ("currency" if "profit" in top_metric or "revenue" in top_metric else "integer"))
        
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
            sec_val = format_metric_value(second_row.get(top_metric, 0), "percentage" if "margin" in top_metric else ("currency" if "profit" in top_metric or "revenue" in top_metric else "integer"))
            explanation += f" It is followed by **{sec_name}** at **{sec_val}**."
        return explanation, kpis

    # 6. Distribution mode (Donut / Pie: channels, categories, segments)
    if plan.intent == "distribution":
        dim = plan.dimensions[0]
        total_val = sum(r.get(plan.metrics[0], 0) for r in rows)
        fmt_total = format_metric_value(total_val, "currency" if "revenue" in plan.metrics[0] or "profit" in plan.metrics[0] else "integer")
        top_row = rows[0]
        top_name = top_row.get(dim, "Unknown")
        top_val = format_metric_value(top_row.get(plan.metrics[0], 0), "currency" if "revenue" in plan.metrics[0] or "profit" in plan.metrics[0] else "integer")
        
        kpis.append(KpiItem(
            label=f"Leading {dim.replace('_', ' ').title()}",
            value=top_name,
            formatted_value=str(top_name),
            formattedValue=str(top_name),
            description=f"{top_val} ({top_row.get(plan.metrics[0], 0) / max(total_val, 1) * 100:.1f}% share)"
        ))
        explanation = (
            f"Distribution across {len(rows)} {dim.replace('_', ' ')} segments represents a combined **{fmt_total}** in {plan.metrics[0].replace('_', ' ')}. "
            f"**{top_name}** accounts for the largest share at **{top_val}**."
        )
        return explanation, kpis

    # 7. Dimension breakdown general
    dim = plan.dimensions[0]
    total_val = sum(r.get(plan.metrics[0], 0) for r in rows)
    fmt_total = format_metric_value(total_val, "currency" if "revenue" in plan.metrics[0] or "profit" in plan.metrics[0] else "integer")
    
    explanation = (
        f"Performance across {len(rows)} {dim.replace('_', ' ')} segments represents a combined "
        f"**{fmt_total}** in {plan.metrics[0].replace('_', ' ')}."
    )
    return explanation, kpis
