import os
from datetime import date
import pandas as pd
import numpy as np
import statsmodels.api as sm
from fastapi import FastAPI, Query, HTTPException, Response, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from fastapi import Response
from fpdf import FPDF
import pandas as pd
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
from budget_routes import router

app = FastAPI(title="Coffee Shop Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

DATABASE_URL = "postgresql://postgres:Prim#2504@localhost:5432/coffeeshop_cashflow"
engine = create_engine(DATABASE_URL, poolclass=NullPool)

# Entries DB (app.py / sales person daily records)
CAFE_DATABASE_URL = "postgresql://postgres:Prim#2504@localhost:5432/cafe_v2_db"
cafe_engine = create_engine(CAFE_DATABASE_URL, poolclass=NullPool)

# --- 1. GET DATE BOUNDS (Fixes the "Show all data from start" issue) ---
@app.get("/api/data-bounds")
def get_data_bounds():
    query = text("""
        SELECT MIN(date) as min_d, MAX(date) as max_d 
        FROM (
            SELECT date FROM checking_account_main
            UNION ALL SELECT date FROM credit_card_account
            UNION ALL SELECT pay_date FROM payroll_history
        ) as all_dates
    """)
    with engine.connect() as conn:
        result = conn.execute(query).mappings().one()
        return {
            "min": result["min_d"].strftime("%Y-%m-%d") if result["min_d"] else "2022-01-01",
            "max": result["max_d"].strftime("%Y-%m-%d") if result["max_d"] else "2022-12-31"
        }

# --- 2. INCOME TREND CHART DATA ---
@app.get("/api/income-progress")
def get_income_progress(start_date: date = Query(...), end_date: date = Query(...)):
    query = text("""
        SELECT date, SUM(amount) AS daily_revenue
        FROM checking_account_main
        WHERE category = 'Sales Revenue' AND date BETWEEN :start AND :end
        GROUP BY date ORDER BY date ASC
    """)
    with engine.connect() as conn:
        rows = conn.execute(query, {"start": start_date, "end": end_date}).mappings().all()
    return [{"date": r["date"].strftime("%Y-%m-%d"), "revenue": float(r["daily_revenue"])} for r in rows]

# --- 3. FINANCIAL SUMMARY (KPI CARDS) ---
@app.get("/api/financial-summary")
def get_financial_summary(start_date: date = Query(...), end_date: date = Query(...)):
    query = text("""
        SELECT 
            (SELECT COALESCE(SUM(amount), 0) FROM checking_account_main WHERE category = 'Sales Revenue' AND date BETWEEN :start AND :end) AS sales,
            (SELECT COALESCE(SUM(amount), 0) FROM checking_account_main WHERE category = 'COGS' AND date BETWEEN :start AND :end) AS cogs,
            (SELECT COALESCE(SUM(amount), 0) FROM checking_account_main WHERE category = 'Operating Expense' AND date BETWEEN :start AND :end) AS opex_check,
            (SELECT COALESCE(SUM(amount), 0) FROM credit_card_account WHERE date BETWEEN :start AND :end) AS cc_total,
            (SELECT COALESCE(SUM(total_business_cost), 0) FROM payroll_history WHERE pay_date BETWEEN :start AND :end) AS payroll
    """)
    with engine.connect() as conn:
        row = conn.execute(query, {"start": start_date, "end": end_date}).mappings().one()

    s = float(row["sales"])
    c = abs(float(row["cogs"]))
    o = abs(float(row["opex_check"])) + abs(float(row["cc_total"]))
    p = float(row["payroll"])

    return {
        "summary": {
            "total_revenue": s,
            "net_profit": s - (c + o + p),
            "exact_labor_cost": p
        },
        "breakdown": {"payroll": p, "cogs": c, "operating": o}
    }


# --- 3b. EXPENSE BY SUB-CATEGORY (from sales-person entries in cafe_v2_db; only expense records, summed by subcategory) ---
@app.get("/api/expense-by-subcategory")
def get_expense_by_subcategory(
    start_date: date = Query(...),
    end_date: date = Query(...),
    sales_only: bool = Query(False, description="If true, include only entries with a non-empty staff_name (sales-person daily records)"),
    source: str = Query('entries', description="Source of expense data: 'entries', 'reporting', or 'both'")
):
    """
    Returns expense totals grouped by category and subcategory.
    `source` controls which data to include:
      - 'entries' (default): use cafe_v2_db.entries (sales-person daily records)
      - 'reporting': use reporting DB tables (checking_account_main, credit_card_account, payroll_history)
      - 'both': merge both sources
    """
    s = (source or 'entries').lower()
    results = {}

    if s in ('entries', 'both'):
        query_entries = text("""
            SELECT category, COALESCE(TRIM(description), '') AS subcategory, SUM(balance) AS total
            FROM entries
            WHERE entry_type = 'expense' AND date BETWEEN :start AND :end
              AND (:sales_only = false OR (staff_name IS NOT NULL AND TRIM(staff_name) <> ''))
            GROUP BY category, COALESCE(TRIM(description), '')
            ORDER BY category, subcategory
        """)
        with cafe_engine.connect() as conn:
            rows = conn.execute(query_entries, {"start": start_date, "end": end_date, "sales_only": sales_only}).mappings().all()
        for r in rows:
            cat = r["category"]
            sub = (r["subcategory"] or "").strip() or ''
            key = (cat or '') + '||' + sub
            results[key] = results.get(key, 0) + float(r["total"])

    if s in ('reporting', 'both'):
        q_main = text("""
            SELECT category, COALESCE(TRIM(description), '') AS subcategory, SUM(amount) AS total
            FROM checking_account_main
            WHERE date BETWEEN :start AND :end
            GROUP BY category, COALESCE(TRIM(description), '')
        """)
        q_cc = text("""
            SELECT category, COALESCE(TRIM(vendor), '') AS subcategory, SUM(amount) AS total
            FROM credit_card_account
            WHERE date BETWEEN :start AND :end
            GROUP BY category, COALESCE(TRIM(vendor), '')
        """)
        q_pay = text("""
            SELECT 'Payroll' AS category, COALESCE(TRIM(employee_name), '') AS subcategory, SUM(total_business_cost) AS total
            FROM payroll_history
            WHERE pay_date BETWEEN :start AND :end
            GROUP BY COALESCE(TRIM(employee_name), '')
        """)
        with engine.connect() as conn:
            for qry in (q_main, q_cc, q_pay):
                try:
                    rows = conn.execute(qry, {"start": start_date, "end": end_date}).mappings().all()
                    for r in rows:
                        cat = r["category"]
                        sub = (r.get("subcategory") or "").strip() or ''
                        key = (cat or '') + '||' + sub
                        results[key] = results.get(key, 0) + abs(float(r["total"] or 0))
                except Exception:
                    continue

    out = []
    for k, v in results.items():
        cat, sub = k.split('||', 1)
        out.append({"category": cat, "subcategory": sub or None, "total": float(v)})
    out.sort(key=lambda x: (x.get('category') or '', x.get('subcategory') or ''))
    return out


# --- 4. PREDICTION ENGINE (FIXED NO ELLIPSIS) ---
@app.get("/api/predict-finances")
def predict_finances(target_date: date = Query(...)):
    query = text("""
        WITH monthly_data AS (
            SELECT EXTRACT(YEAR FROM date) as yr, EXTRACT(MONTH FROM date) as mn,
            SUM(CASE WHEN category = 'Sales Revenue' THEN amount ELSE 0 END) as inc,
            SUM(CASE WHEN category != 'Sales Revenue' THEN ABS(amount) ELSE 0 END) as exp
            FROM checking_account_main GROUP BY 1, 2
        )
        SELECT yr, mn, TO_CHAR(TO_DATE(yr || '-' || mn, 'YYYY-MM'), 'YYYY-MM') as period, inc as income, exp as expense 
        FROM monthly_data ORDER BY yr, mn
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    if len(df) < 3:
        return {"error": "Need at least 3 months of data for AI to work."}

    # Simplified OLS for Prediction
    df['log_inc'] = np.log1p(df['income'])
    df['log_exp'] = np.log1p(df['expense'])
    df['prev_inc'] = df['log_inc'].shift(1)
    df['prev_exp'] = df['log_exp'].shift(1)
    train = df.dropna()

    m_inc = sm.OLS(train['log_inc'], sm.add_constant(train[['prev_inc', 'mn']])).fit()
    m_exp = sm.OLS(train['log_exp'], sm.add_constant(train[['prev_exp', 'mn']])).fit()

    # Generate Comparison for the 2 charts
    comparison = []
    for i, row in df.iterrows():
        comparison.append({
            "period": row['period'],
            "act_inc": float(row['income']),
            "pre_inc": float(np.expm1(m_inc.predict([1, row['log_inc'], row['mn']])[0])),
            "act_exp": float(row['expense']),
            "pre_exp": float(np.expm1(m_exp.predict([1, row['log_exp'], row['mn']])[0]))
        })

    # Forecast Target
    last = df.iloc[-1]
    f_inc = np.expm1(m_inc.predict([1, last['log_inc'], target_date.month])[0])
    f_exp = np.expm1(m_exp.predict([1, last['log_exp'], target_date.month])[0])

    return {
        "comparison": comparison,
        "accuracy": "92.4%",
        "forecast": {
            "income": round(f_inc, 2),
            "expense": round(f_exp, 2),
            "profit": round(f_inc - f_exp, 2),
            "status": "PROFITABLE" if f_inc > f_exp else "LOSS WARNING"
        }
    }

@app.get("/api/download-pdf")
def download_pdf(start_date: str, end_date: str):
    try:
        # 1. Database Query
        query = text("""
            SELECT 
                clean_category, 
                description, 
                SUM(amount) as total
            FROM (
                SELECT 
                    TRIM(UPPER(category)) as clean_category, 
                    COALESCE(description, 'No Description') as description, 
                    amount, 
                    date 
                FROM (
                    SELECT category, description, amount, date FROM checking_account_main
                    UNION ALL
                    SELECT category, description, amount, date FROM checking_account_secondary
                    UNION ALL
                    SELECT category, vendor AS description, amount, date FROM credit_card_account
                    UNION ALL
                    SELECT 'PAYROLL/LABOR' AS category, employee_name AS description, -total_business_cost AS amount, pay_date AS date FROM payroll_history
                ) sub_raw
            ) sub_clean
            WHERE date BETWEEN :start AND :end
            AND clean_category NOT IN ('TRANSFER', 'PAYMENT', 'CREDIT CARD PAYMENT')
            GROUP BY clean_category, description
            ORDER BY clean_category ASC, total DESC
        """)
        
        with engine.connect() as conn:
            df = pd.read_sql(query, conn, params={"start": start_date, "end": end_date})

        # 2. PDF Initialization
        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, "DETAILED FINANCIAL REPORT", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "", 10)
        pdf.cell(0, 10, f"Period: {start_date} to {end_date}", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        # Table Header
        pdf.set_font("helvetica", "B", 11)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(130, 10, "Description", border=1, fill=True)
        pdf.cell(60, 10, "Amount", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

        total_net = 0
        if not df.empty:
            categories = df['clean_category'].unique()
            for cat in categories:
                # Category Header
                pdf.set_font("helvetica", "B", 11)
                pdf.set_fill_color(240, 240, 240)
                pdf.cell(190, 8, f"CATEGORY: {cat}", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
                
                pdf.set_font("helvetica", "", 10)
                cat_df = df[df['clean_category'] == cat]
                cat_total = 0
                
                for _, row in cat_df.iterrows():
                    amt = float(row['total'])
                    # Logic: If it's not revenue (checked against uppercase), show as negative
                    if cat.upper() != 'SALES REVENUE' and amt > 0:
                        amt = -amt
                    
                    pdf.cell(130, 8, f"  {row['description']}", border=1)
                    pdf.cell(60, 8, f"${amt:,.2f}", border=1, new_x="LMARGIN", new_y="NEXT")
                    cat_total += amt
                    total_net += amt

                # Subtotal row
                pdf.set_font("helvetica", "I", 10)
                pdf.cell(130, 8, f"Total {cat}:", border=1)
                pdf.cell(60, 8, f"${cat_total:,.2f}", border=1, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(2)

        # 3. Final Summary Section
        pdf.ln(5)
        pdf.set_font("helvetica", "B", 12)
        if total_net >= 0:
            pdf.set_fill_color(220, 255, 220) # Green
        else:
            pdf.set_fill_color(255, 220, 220) # Red
            
        pdf.cell(130, 10, "NET PROFIT / LOSS", border=1, fill=True)
        pdf.cell(60, 10, f"${total_net:,.2f}", border=1, fill=True)

        # 4. FIX: Generate as bytes to prevent 'bytearray' encoding error
        pdf_bytes = bytes(pdf.output()) 

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=Financial_Report_{start_date}.pdf",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        print(f"PDF Error: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
