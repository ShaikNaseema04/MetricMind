# MetricMind — Agentic Semantic BI Engine Architecture

## 1. System Overview

MetricMind is an enterprise-grade Semantic BI platform providing natural-language business question answering with deterministic mathematical accuracy, continuous ambient UI animations, SQL transparency, and governed metrics.

```
                           +----------------------------------------+
                           |     MetricMind Next.js Frontend        |
                           |  (App Router, TypeScript, ECharts)     |
                           +-------------------+--------------------+
                                               |
                                     JSON API Requests
                                               |
                                               v
                           +----------------------------------------+
                           |       FastAPI Backend Application      |
                           +-------------------+--------------------+
                                               |
                     +-------------------------+-------------------------+
                     |                                                   |
                     v                                                   v
        +----------------------------+                     +---------------------------+
        |   Semantic Metric Registry |                     | Agentic Query Planner     |
        |  - Approved Metrics        |                     | - Intent Recognition      |
        |  - Governed Formulas       |                     | - Dimension Extraction    |
        |  - 1-to-1 Join Rules       |                     | - Deterministic Fallback  |
        +--------------+-------------+                     +-------------+-------------+
                       |                                                 |
                       +-----------------------+-------------------------+
                                               |
                                     Validated Query Plan
                                               |
                                               v
                           +----------------------------------------+
                           |       Analytical Execution Engine      |
                           |  - Parameterized Safe SQL Generation   |
                           |  - Secondary Trend Breakdowns          |
                           |  - SQL & API Execution Tracing         |
                           +-------------------+--------------------+
                                               |
                                         Executes Query
                                               |
                                               v
                           +----------------------------------------+
                           |      SQLite Analytical Mart (v3.x)     |
                           |    v_orders_enriched (10,000 orders)   |
                           |  Costs, Products, Customers, Dates     |
                           +----------------------------------------+
```

## 2. Governed Business Metrics

All analytics derive strictly from `MetricMind_Raw_Dataset` (`C:\Users\VENKATA BALAJI\Downloads\MetricMind_Raw_Dataset`):

| Metric | Business Definition | Formula | Governed Rule |
| :--- | :--- | :--- | :--- |
| **Total Revenue** | Net recognized sales from completed transactions | `SUM(revenue) WHERE order_status = 'Completed'` | Excludes returns and cancellations |
| **Total Profit** | Net profit after deducting product & shipping costs | `SUM(profit) WHERE order_status = 'Completed'` | Authoritative profit field in dataset |
| **Profit Margin** | Ratio of net profit to total revenue | `(SUM(profit) / SUM(revenue)) * 100` | Prevents arithmetic average-of-averages |
| **Units Sold** | Total quantity of physical items sold | `SUM(quantity) WHERE order_status = 'Completed'` | Integer unit aggregation |
| **Completed Orders** | Total volume of fulfilled customer orders | `COUNT(order_id) WHERE order_status = 'Completed'` | Deduplicated transaction count |

## 3. Transparency & Auditability

1. **View SQL**: Shows the exact, parameterized SQL generated against the enriched view `v_orders_enriched`, including bound parameters and execution duration in milliseconds.
2. **View API Call**: Shows the exact HTTP endpoint, method, sanitized request payload, HTTP status code, and JSON response.
