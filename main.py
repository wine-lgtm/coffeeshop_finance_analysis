import os
from datetime import date
import pandas as pd
import numpy as np
import statsmodels.api as sm
from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from fastapi import Response
from fpdf import FPDF
import pandas as pd
from sqlalchemy import text
from dateutil.relativedelta import relativedelta
from budget_routes import router as budget_router

app = FastAPI(title="Coffee Shop Backend")

app.include_router(budget_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Change this:
DATABASE_URL = "postgresql://postgres:Prim#2504@127.0.0.1:5432/coffeeshop_cashflow"
engine = create_engine(DATABASE_URL, poolclass=NullPool)

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

@app.get("/api/detailed-cashflow")
def get_detailed_cashflow(start_date: date = Query(...), end_date: date = Query(...)):
    query = text("""
        SELECT 
            TO_CHAR(date, 'YYYY-MM-DD') as date, 
            description, 
            category, 
            amount
        FROM (
            SELECT date, description, category, amount FROM checking_account_main
            UNION ALL
            SELECT date, description, category, amount FROM checking_account_secondary
            UNION ALL
            SELECT date, vendor AS description, category, amount FROM credit_card_account
            UNION ALL
            SELECT pay_date AS date, employee_name AS description, 'PAYROLL/LABOR' AS category, -total_business_cost AS amount FROM payroll_history
        ) sub_raw
        WHERE CAST(date AS DATE) BETWEEN :start AND :end
        AND TRIM(UPPER(category)) NOT IN ('TRANSFER', 'PAYMENT', 'CREDIT CARD PAYMENT')
        ORDER BY date DESC
    """)
    try:
        with engine.connect() as conn:
            # We pass the date objects directly; SQLAlchemy handles the rest
            result = conn.execute(query, {"start": start_date, "end": end_date})
            data = [dict(row._mapping) for row in result]
            print(f"DEBUG: Found {len(data)} rows for range {start_date} to {end_date}")
            return data
    except Exception as e:
        print(f"Detail Table Error: {e}")
        return []
        

import pandas as pd
import numpy as np
import statsmodels.api as sm
from datetime import date
from dateutil.relativedelta import relativedelta
from sqlalchemy import text
from fastapi import APIRouter, Query

@app.get("/api/predict-finances")
def predict_finances(target_date: date = Query(...)):
    # 1. SQL QUERY (Unchanged - your data aggregation)
    query = text("""
        WITH combined_data AS (
            SELECT category, amount, date FROM checking_account_main
            UNION ALL
            SELECT category, amount, date FROM checking_account_secondary
            UNION ALL
            SELECT category, amount, date FROM credit_card_account
            UNION ALL
            SELECT 'PAYROLL/LABOR' AS category, -total_business_cost AS amount, pay_date AS date FROM payroll_history
        ),
        monthly_data AS (
            SELECT 
                EXTRACT(YEAR FROM date) as yr, 
                EXTRACT(MONTH FROM date) as mn,
                SUM(CASE WHEN TRIM(UPPER(category)) = 'SALES REVENUE' THEN amount ELSE 0 END) as inc,
                SUM(CASE WHEN TRIM(UPPER(category)) != 'SALES REVENUE' THEN ABS(amount) ELSE 0 END) as exp
            FROM combined_data 
            WHERE TRIM(UPPER(category)) NOT IN ('TRANSFER', 'PAYMENT', 'CREDIT CARD PAYMENT')
            GROUP BY 1, 2
        )
        SELECT yr, mn, 
               TO_CHAR(TO_DATE(yr || '-' || mn, 'YYYY-MM'), 'YYYY-MM') as period, 
               inc as income, exp as expense 
        FROM monthly_data 
        ORDER BY yr, mn
    """)
    
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    if len(df) < 3:
        return {"error": "Need at least 3 months of data."}

    # 2. FEATURE ENGINEERING (Stable Learning)
    # We identify peak months from YOUR history (March, April, June)
    df['is_peak'] = df['mn'].isin([3, 4, 6]).astype(int)
    df['log_inc'] = np.log1p(df['income'].clip(lower=0))
    df['log_exp'] = np.log1p(df['expense'].clip(lower=0))
    df['prev_log_inc'] = df['log_inc'].shift(1)
    df['prev_log_exp'] = df['log_exp'].shift(1)
    
    train_df = df.dropna().copy()
    
    # Train models with a constant (intercept) to stabilize predictions
    model_inc = sm.OLS(train_df['log_inc'], sm.add_constant(train_df[['prev_log_inc', 'is_peak', 'mn']])).fit()
    model_exp = sm.OLS(train_df['log_exp'], sm.add_constant(train_df[['prev_log_exp', 'is_peak', 'mn']])).fit()

    # 3. ACCURACY CALCULATION (Back-testing)
    errors = []
    for i in range(1, len(df)):
        p_log = model_inc.predict([1, df.iloc[i-1]['log_inc'], df.iloc[i]['is_peak'], int(df.iloc[i]['mn'])])[0]
        act = float(df.iloc[i]['income'])
        if act > 0:
            # Accuracy = 1 - (|Actual - Predicted| / Actual)
            pred_val = np.expm1(p_log)
            errors.append(abs(act - pred_val) / act)
    
    # If errors are wild, we cap accuracy at 99.9% but force it to reflect the pattern
    accuracy_val = round(max(0, min(99.9, (1 - np.mean(errors)) * 100)), 1) if errors else 0.0

    # 4. RECURSIVE BRIDGE (Fixes the October 0 and the December Crash)
    comparison = []
    last_db = df.iloc[-1]
    
    # Starting "Memory"
    curr_i_log = last_db['log_inc']
    curr_e_log = last_db['log_exp']
    
    # Dates
    walker_date = date(int(last_db['yr']), int(last_db['mn']), 1)
    target_start = date(target_date.year, target_date.month, 1)
    target_end = target_start + relativedelta(months=2)

    for _ in range(24): # Max 2 years
        walker_date += relativedelta(months=1)
        if walker_date > target_end:
            break
            
        m_idx = walker_date.month
        is_p = 1 if m_idx in [3, 4, 6] else 0
        
        # PREDICT + CLIP: This prevents the 'inf' (Infinity) error
        # 18.5 is roughly $100 Million. This stops the explosion.
        curr_i_log = np.clip(model_inc.predict([1, curr_i_log, is_p, m_idx])[0], 0, 18.5)
        curr_e_log = np.clip(model_exp.predict([1, curr_e_log, is_p, m_idx])[0], 0, 18.5)
        
        if walker_date >= target_start:
            p_str = walker_date.strftime("%Y-%m")
            
            # Map predicted values back from Log to Real Numbers
            p_inc = round(float(np.expm1(curr_i_log)), 2)
            p_exp = round(float(np.expm1(curr_e_log)), 2)
            
            comparison.append({
                "period": p_str,
                "act_inc": 0.0,
                "pre_inc": p_inc,
                "act_exp": 0.0,
                "pre_exp": p_exp
            })

    # 5. RESPONSE
    forecast_main = comparison[0] if comparison else {"pre_inc": 0, "pre_exp": 0}

    return {
        "comparison": comparison,
        "accuracy": f"{accuracy_val}%",
        "forecast": {
            "target": target_date.strftime("%B %Y"),
            "income": forecast_main["pre_inc"],
            "expense": forecast_main["pre_exp"],
            "profit": round(forecast_main["pre_inc"] - forecast_main["pre_exp"], 2),
            "status": "PROFITABLE" if (forecast_main["pre_inc"] > forecast_main["pre_exp"]) else "LOSS EXPECTED"
        }
    }
@app.get("/api/download-pdf")
def download_pdf(start_date: date, end_date: date):
    try:
        # 1. KPI Query (Main Cards)
        query_kpi = text("""
            SELECT 
                (SELECT COALESCE(SUM(amount), 0) FROM checking_account_main WHERE category = 'Sales Revenue' AND date BETWEEN :start AND :end) AS sales,
                (SELECT COALESCE(SUM(amount), 0) FROM checking_account_main WHERE category = 'COGS' AND date BETWEEN :start AND :end) AS cogs,
                (SELECT COALESCE(SUM(amount), 0) FROM checking_account_main WHERE category = 'Operating Expense' AND date BETWEEN :start AND :end) AS opex_check,
                (SELECT COALESCE(SUM(amount), 0) FROM credit_card_account WHERE date BETWEEN :start AND :end) AS cc_total,
                (SELECT COALESCE(SUM(total_business_cost), 0) FROM payroll_history WHERE pay_date BETWEEN :start AND :end) AS payroll
        """)
        
        # 2. Detail Query (Ordered ASCENDING by date)
        detail_query = text("""
            SELECT TO_CHAR(date, 'YYYY-MM-DD') as formatted_date, clean_category, description, total FROM (
                SELECT date, TRIM(UPPER(category)) as clean_category, description, amount as total
                FROM (
                    SELECT date, category, description, amount FROM checking_account_main
                    UNION ALL SELECT date, category, description, amount FROM checking_account_secondary
                    UNION ALL SELECT date, category, vendor AS description, amount FROM credit_card_account
                    UNION ALL SELECT pay_date AS date, 'PAYROLL/LABOR' AS category, employee_name AS description, -total_business_cost AS amount FROM payroll_history
                ) sub_raw
                WHERE date BETWEEN :start AND :end
            ) sub_clean
            WHERE clean_category NOT IN ('TRANSFER', 'PAYMENT', 'CREDIT CARD PAYMENT')
            ORDER BY date ASC, clean_category ASC
        """)

        with engine.connect() as conn:
            row_kpi = conn.execute(query_kpi, {"start": start_date, "end": end_date}).mappings().one()
            df_details = pd.read_sql(detail_query, conn, params={"start": start_date, "end": end_date})

        # --- Dashboard Math ---
        s = float(row_kpi["sales"])
        c = abs(float(row_kpi["cogs"]))
        o = abs(float(row_kpi["opex_check"])) + abs(float(row_kpi["cc_total"]))
        p = float(row_kpi["payroll"])
        
        actual_gross_profit = s - c
        actual_net_profit = s - (c + o + p)

        # 3. Category Summary Calculation
        # We group the dataframe to get totals per category
        df_details['clean_total'] = df_details.apply(
            lambda x: float(x['total']) if pd.notnull(x['total']) else 0.0, axis=1
        )
        # Flip signs for display (Sales positive, others negative)
        df_details['display_total'] = df_details.apply(
            lambda x: x['clean_total'] if x['clean_category'] == 'SALES REVENUE' else -abs(x['clean_total']), axis=1
        )
        cat_summary = df_details.groupby('clean_category')['display_total'].sum().reset_index()

        # 4. PDF Generation
        pdf = FPDF()
        pdf.add_page()
        
        # Header
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, "FINANCIAL PERFORMANCE REPORT", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "", 10)
        pdf.cell(0, 8, f"Period: {start_date} to {end_date}", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        # Summary KPIs
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(45, 10, " TOTAL REVENUE:", border=1, fill=True)
        pdf.cell(50, 10, f"${s:,.2f}", border=1)
        pdf.cell(45, 10, " GROSS PROFIT:", border=1, fill=True)
        pdf.cell(50, 10, f"${actual_gross_profit:,.2f}", border=1, new_x="LMARGIN", new_y="NEXT")
        
        pdf.cell(45, 10, " LABOR COST:", border=1, fill=True)
        pdf.cell(50, 10, f"${p:,.2f}", border=1)
        pdf.cell(45, 10, " NET PROFIT:", border=1, fill=True)
        pdf.set_text_color(200, 0, 0) if actual_net_profit < 0 else pdf.set_text_color(0, 128, 0)
        pdf.cell(50, 10, f"${actual_net_profit:,.2f}", border=1, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(10)

        # --- NEW: CATEGORY TOTALS TABLE ---
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 10, "Category Summary", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "B", 10)
        pdf.set_fill_color(220, 220, 220)
        pdf.cell(110, 10, " Category Name", border=1, fill=True)
        pdf.cell(80, 10, " Total Amount", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font("helvetica", "", 10)
        for _, row in cat_summary.iterrows():
            pdf.cell(110, 8, f" {row['clean_category']}", border=1)
            pdf.cell(80, 8, f"${row['display_total']:,.2f}", border=1, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(10)

        # --- TRANSACTION DETAILS TABLE (ASCENDING) ---
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 10, "Detailed Transactions", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "B", 9)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(25, 10, " Date", border=1, fill=True)
        pdf.cell(125, 10, " Description", border=1, fill=True)
        pdf.cell(40, 10, " Amount", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("helvetica", "", 8)
        for _, row_data in df_details.iterrows():
            pdf.cell(25, 8, f" {row_data['formatted_date']}", border=1)
            pdf.cell(125, 8, f" [{row_data['clean_category']}] {str(row_data['description'])[:55]}", border=1)
            pdf.cell(40, 8, f"${row_data['display_total']:,.2f}", border=1, new_x="LMARGIN", new_y="NEXT")

        return Response(
            content=bytes(pdf.output()),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=Report.pdf"}
        )
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

