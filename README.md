# MetricMind — Agentic Semantic BI Engine

> **Enterprise-Grade Natural Language Business Intelligence with Continuous Ambient UI Visualizations and Governed Semantic Transparency**

MetricMind is a full-stack, enterprise-grade Agentic Semantic BI Engine built from the ground up for the Axlero MetricMind project. It connects directly to the real corporate transactions dataset (`MetricMind_Raw_Dataset`), validates analytical requests against a centralized Semantic Registry, generates safe, parameterized SQL, executes queries against an indexed SQLite application data mart, and renders rich, interactive Apache ECharts visualizations and transparent SQL/API audit logs.

---

## Key Highlights

- **Visual Fidelity**: Recreates the deep navy/cyan/violet enterprise reference design with glowing neon effects, dark glassmorphism cards, and responsive sidebars.
- **Continuous Triple Animations**:
  - **7 Cyan/Blue Bars**: Continuously animate up and down with staggered timings inside the Total Revenue card on page load without user interaction.
  - **Neon Wave Line Charts**: Smooth undulating cyan and violet wave curves flowing seamlessly across the canvas.
  - **3-Layered Hill-Shaped Area Waves**: Morphing SVG area paths (Deep Indigo back layer, Violet mid layer, and Electric Blue front layer) creating a flowing mountain wave effect.
- **Real Business Dataset Integration**: Reads from `C:\Users\VENKATA BALAJI\Downloads\MetricMind_Raw_Dataset` (500 customers, 12 products, 10,000 orders, 10,000 costs, 365 date records). Never modifies or overwrites the raw source files.
- **Governed Semantic Metric Registry**:
  - `Total Revenue`: `$740,910,750.00` (Completed orders)
  - `Total Profit`: `$194,796,053.42`
  - `Profit Margin`: `26.29%` (`(Profit / Revenue) * 100`)
  - `Units Sold`: `24,215` units across 5,996 completed transactions
- **Deterministic Natural Language Querying**: Full agent reasoning and multi-step investigation working out of the box without requiring a paid LLM API key.
- **Full Transparency**:
  - **View SQL**: Inspect the exact executed SQL, bound parameters, and metric formulas with one-click copy.
  - **View API Call**: Inspect real HTTP request payloads, response times in milliseconds, and status codes.
- **Complete Suite of Pages**:
  - **Chat Interface**: Natural language business question answering with charts and tables.
  - **Analytics Page**: Executive KPI cards, monthly trends, regional comparisons, product rankings, and interactive filters.
  - **Data Sources Page**: Live directory status, table row counts, column schemas, data quality/missing value summaries, and supplementary CSV upload.
  - **Integrations Page**: Connection and verification status for LLM Provider, Snowflake Data Cloud, Cube.dev, and dbt.
  - **Settings Page**: Controls for continuous animations, reduced motion, accent theme, currency format, and default order filters.

---

## Architecture

```
MetricMind/
  frontend/                     # Next.js 16 (App Router) + TypeScript + Tailwind CSS
    app/                        # App Router pages and proxy routes
    components/                 # AnimatedAnalyticsHero, MetricMindEChart, DataTable, Modals
    mock/                       # API fetch clients and endpoint configuration
    public/                     # Static assets and icons
  backend/                      # Python FastAPI
    app/
      api/                      # REST endpoints (/chat, /dataset, /metrics, /analytics/query, /integrations)
      database/                 # SQLite connection layer and indexed tables
      models/                   # Pydantic schemas for queries, responses, and traces
      semantic/                 # Centralized metric & dimension registry with validation rules
      services/                 # Data loader, deterministic query planner, and analytical engine
    tests/                      # Pytest automated test suite (14 passing tests)
    requirements.txt            # Python dependencies
    .env.example                # Backend environment template
  data/
    processed/                  # Supplementary and processed datasets
    reports/                    # Ingestion and data quality inspection reports
  docs/                         # Architecture specifications
  README.md                     # Documentation and setup instructions
```

---

## Windows Quickstart & Execution

### 1. Prerequisites
- **Python 3.12+**
- **Node.js 20+** and **npm**

### 2. Backend Setup & Run

Open a **PowerShell** terminal in the project root:

```powershell
# Navigate to the workspace root
cd "C:\Users\VENKATA BALAJI\Desktop\MetricMind"

# Install backend dependencies (or create a virtual environment first)
pip install -r backend/requirements.txt

# Start the FastAPI backend server on port 8000
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend starts at `http://127.0.0.1:8000`. You can verify health at `http://127.0.0.1:8000/health` and view OpenAPI docs at `http://127.0.0.1:8000/docs`.

### 3. Frontend Setup & Run

Open a **second PowerShell** terminal in the frontend directory:

```powershell
cd "C:\Users\VENKATA BALAJI\Desktop\MetricMind\frontend"

# Install dependencies (legacy peer deps flag handles React 19 compatibility)
npm install --legacy-peer-deps

# Start the Next.js development server
npm run dev
```

Open your browser to:
👉 **`http://localhost:3000`**

---

## Running Automated Tests

Run the full backend test suite covering dataset ingestion, semantic registry metrics, deterministic query planning, and API endpoints:

```powershell
cd "C:\Users\VENKATA BALAJI\Desktop\MetricMind"
python -m pytest backend/tests
```

Expected result:
```
======================= 14 passed in 2.98s =======================
```

---

## Environment Variables

Configure backend settings via `backend/.env`:

```env
METRICMIND_DATA_DIR=C:\Users\VENKATA BALAJI\Downloads\MetricMind_Raw_Dataset
METRICMIND_DB_PATH=database/metricmind.db
PORT=8000
HOST=127.0.0.1
DEBUG=True

# Optional External AI API Keys (Not needed for built-in deterministic engine)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
```

Frontend configuration in `frontend/.env.local`:
```env
METRICMIND_API_URL=http://127.0.0.1:8000/api/chat
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```
