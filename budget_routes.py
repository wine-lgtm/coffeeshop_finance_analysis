from datetime import date
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


def get_overall_budget_month_range():
    """Allowed months: current month through next 3 months (no past, no beyond)."""
    today = date.today()
    current_first = date(today.year, today.month, 1)
    # max month: +3 months from current
    y, m = today.year, today.month
    m += 3
    if m > 12:
        m -= 12
        y += 1
    max_first = date(y, m, 1)
    min_str = current_first.strftime("%Y-%m")
    max_str = max_first.strftime("%Y-%m")
    return min_str, max_str

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/coffeeshop_cashflow"
engine = create_engine(DATABASE_URL, poolclass=NullPool)
# cafe entries DB (sales-person daily records) used optionally by key-insights
CAFE_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/cafe_v2_db"
cafe_engine = create_engine(CAFE_DATABASE_URL, poolclass=NullPool)


def _normalize_category_server(cat: str):
    """Normalize category names on the server to match frontend keys.
    Examples: 'Operating Expense' -> 'Operating expense', 'COGS' stays 'COGS'.
    """
    if not cat:
        return ''
    c = str(cat).strip()
    if c.lower() == 'operating expense':
        return 'Operating expense'
    if c.lower() == 'cogs':
        return 'COGS'
    return c

# Create tables if not exist
try:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS budgets (
                id SERIAL PRIMARY KEY,
                month TEXT NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT,
                amount NUMERIC(12,2) NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS company_budgets (
                id SERIAL PRIMARY KEY,
                month TEXT NOT NULL,
                amount NUMERIC(12,2) NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS overall_budgets (
                id SERIAL PRIMARY KEY,
                month TEXT,
                amount NUMERIC(12,2),
                description TEXT
            )
        """))
        # Ensure columns exist even if table was created with an older structure
        conn.execute(text("ALTER TABLE overall_budgets ADD COLUMN IF NOT EXISTS month TEXT"))
        conn.execute(text("ALTER TABLE overall_budgets ADD COLUMN IF NOT EXISTS description TEXT"))
        conn.commit()
        print("Budget tables created successfully")
except Exception as e:
    print(f"Database connection error: {e}")
    print("Please ensure PostgreSQL is running and the database exists.")

# --- BUDGET MANAGEMENT API ---


def _get_overall_and_category_sum(conn, month: str):
    """Returns (overall_amount or None, sum of main category budgets for that month)."""
    overall = conn.execute(
        text("SELECT amount FROM overall_budgets WHERE month = :month"),
        {"month": month},
    ).fetchone()
    main_sum_row = conn.execute(
        text(
            """
        SELECT COALESCE(SUM(amount), 0) AS total
        FROM budgets
        WHERE month = :month AND subcategory IS NULL
        """
        ),
        {"month": month},
    ).mappings().one()
    overall_amount = float(overall[0]) if overall else None
    main_sum = float(main_sum_row["total"])
    return overall_amount, main_sum


def _check_category_sum_within_overall(conn, month: str, main_category_sum: float):
    """Raise if overall budget exists for month and main_category_sum exceeds it."""
    overall_amount, _ = _get_overall_and_category_sum(conn, month)
    if overall_amount is not None and main_category_sum > overall_amount:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Category budgets total ${main_category_sum:,.0f} exceeds the overall budget for this month (${overall_amount:,.0f}). "
                "Please increase the overall budget or reduce category budgets."
            ),
        )


def _check_overall_not_below_category_sum(conn, month: str, overall_amount: float):
    """Raise if sum of main category budgets for month exceeds overall_amount."""
    _, main_sum = _get_overall_and_category_sum(conn, month)
    if main_sum > 0 and overall_amount < main_sum:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Category budgets for this month total ${main_sum:,.0f}. "
                f"Overall budget (${overall_amount:,.0f}) cannot be less. Please increase the overall budget or reduce category budgets."
            ),
        )


def _require_overall_budget_for_month(conn, month: str):
    """Raise if no overall budget exists for this month. Category budgets require an overall budget first."""
    overall_amount, _ = _get_overall_and_category_sum(conn, month)
    if overall_amount is None:
        raise HTTPException(
            status_code=400,
            detail=f"No overall budget set for {month}. Please add an overall budget for this month before adding category budgets.",
        )


class BudgetModel(BaseModel):
    month: str
    category: str
    subcategory: Optional[str] = None
    amount: float

@router.get("/api/budgets")
def get_budgets(month: Optional[str] = None):
    query_str = "SELECT * FROM budgets"
    params = {}
    if month:
        query_str += " WHERE month = :month"
        params["month"] = month
    query_str += " ORDER BY month DESC, category ASC"
    
    with engine.connect() as conn:
        rows = conn.execute(text(query_str), params).mappings().all()
    return [dict(r) for r in rows]

@router.post("/api/budgets")
def create_budget(budget: BudgetModel):
    with engine.connect() as conn:
        # Category budgets require an overall budget for the same month first
        _require_overall_budget_for_month(conn, budget.month)
        # Prevent duplicate budget for same month + category + subcategory
        existing = conn.execute(
            text(
                """
                SELECT id FROM budgets
                WHERE month = :month
                  AND category = :category
                  AND (
                        (subcategory IS NULL AND :subcategory IS NULL)
                        OR subcategory = :subcategory
                  )
                """
            ),
            {
                "month": budget.month,
                "category": budget.category,
                "subcategory": budget.subcategory,
            },
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Budget already exists for this category and month",
            )

        # Budget hierarchy rules between main category and sub-categories
        if budget.subcategory not in (None, ""):
            # Sub-category: main category budget must exist first, and total sub-categories must not exceed it
            main_row = conn.execute(
                text(
                    """
                    SELECT amount FROM budgets
                    WHERE month = :month
                      AND category = :category
                      AND subcategory IS NULL
                    """
                ),
                {
                    "month": budget.month,
                    "category": budget.category,
                },
            ).fetchone()

            if main_row is None:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"No main {budget.category} budget found for {budget.month}. "
                        f"Please create the main {budget.category} budget first, then add sub-category budgets."
                    ),
                )

            main_amount = float(main_row[0])
            sub_totals_row = conn.execute(
                text(
                    """
                    SELECT COALESCE(SUM(amount), 0) AS total
                    FROM budgets
                    WHERE month = :month
                      AND category = :category
                      AND subcategory IS NOT NULL
                    """
                ),
                {
                    "month": budget.month,
                    "category": budget.category,
                },
            ).mappings().one()

            existing_sub_total = float(sub_totals_row["total"])
            new_total = existing_sub_total + float(budget.amount)

            if new_total > main_amount:
                formatted_main = f"{main_amount:,.0f}"
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"This sub-category budget exceeds the {budget.category} budget of ${formatted_main}.\n"
                        f"Please increase the {budget.category} budget or reduce the sub-category amount."
                    ),
                )
        else:
            # Main category: if sub-categories already exist, main must be >= sum of sub-categories
            sub_totals_row = conn.execute(
                text(
                    """
                    SELECT COALESCE(SUM(amount), 0) AS total
                    FROM budgets
                    WHERE month = :month
                      AND category = :category
                      AND subcategory IS NOT NULL
                    """
                ),
                {
                    "month": budget.month,
                    "category": budget.category,
                },
            ).mappings().one()

            existing_sub_total = float(sub_totals_row["total"])
            if existing_sub_total > 0 and budget.amount < existing_sub_total:
                formatted_sub = f"{existing_sub_total:,.0f}"
                formatted_main = f"{budget.amount:,.0f}"
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Your sub-category budgets total ${formatted_sub}, which is higher than the {budget.category} budget of ${formatted_main}.\n"
                        f"Please increase the {budget.category} budget or adjust the sub-category amounts."
                    ),
                )

        # Category budgets must belong to an overall budget (same month): sum of main category budgets <= overall budget
        _, current_main_sum = _get_overall_and_category_sum(conn, budget.month)
        new_main_sum = current_main_sum + (float(budget.amount) if budget.subcategory in (None, "") else 0)
        _check_category_sum_within_overall(conn, budget.month, new_main_sum)

        query = text(
            """
            INSERT INTO budgets (month, category, subcategory, amount)
            VALUES (:month, :category, :subcategory, :amount)
            RETURNING id
        """
        )
        result = conn.execute(
            query,
            {
                "month": budget.month,
                "category": budget.category,
                "subcategory": budget.subcategory,
                "amount": budget.amount,
            },
        )
        conn.commit()
        new_id = result.scalar()
    return {"id": new_id, "message": "Budget created successfully"}

@router.put("/api/budgets/{budget_id}")
def update_budget(budget_id: int, budget: BudgetModel):
    with engine.connect() as conn:
        # Category budgets require an overall budget for the same month first
        _require_overall_budget_for_month(conn, budget.month)
        # Prevent changing into a duplicate month + category + subcategory of another row
        existing = conn.execute(
            text(
                """
                SELECT id FROM budgets
                WHERE month = :month
                  AND category = :category
                  AND (
                        (subcategory IS NULL AND :subcategory IS NULL)
                        OR subcategory = :subcategory
                  )
                  AND id <> :id
                """
            ),
            {
                "month": budget.month,
                "category": budget.category,
                "subcategory": budget.subcategory,
                "id": budget_id,
            },
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Budget already exists for this category and month",
            )

        # Budget hierarchy rules between main category and sub-categories
        if budget.subcategory not in (None, ""):
            # Sub-category: main category budget must exist first, and total sub-categories must not exceed it
            main_row = conn.execute(
                text(
                    """
                    SELECT amount FROM budgets
                    WHERE month = :month
                      AND category = :category
                      AND subcategory IS NULL
                    """
                ),
                {
                    "month": budget.month,
                    "category": budget.category,
                },
            ).fetchone()

            if main_row is None:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"No main {budget.category} budget found for {budget.month}. "
                        f"Please create the main {budget.category} budget first, then add sub-category budgets."
                    ),
                )

            main_amount = float(main_row[0])
            sub_totals_row = conn.execute(
                text(
                    """
                    SELECT COALESCE(SUM(amount), 0) AS total
                    FROM budgets
                    WHERE month = :month
                      AND category = :category
                      AND subcategory IS NOT NULL
                      AND id <> :id
                    """
                ),
                {
                    "month": budget.month,
                    "category": budget.category,
                    "id": budget_id,
                },
            ).mappings().one()

            existing_sub_total = float(sub_totals_row["total"])
            new_total = existing_sub_total + float(budget.amount)

            if new_total > main_amount:
                formatted_main = f"{main_amount:,.0f}"
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"This sub-category budget exceeds the {budget.category} budget of ${formatted_main}.\n"
                        f"Please increase the {budget.category} budget or reduce the sub-category amount."
                    ),
                )
        else:
            # Main category: if sub-categories already exist, main must be >= sum of sub-categories
            sub_totals_row = conn.execute(
                text(
                    """
                    SELECT COALESCE(SUM(amount), 0) AS total
                    FROM budgets
                    WHERE month = :month
                      AND category = :category
                      AND subcategory IS NOT NULL
                    """
                ),
                {
                    "month": budget.month,
                    "category": budget.category,
                },
            ).mappings().one()

            existing_sub_total = float(sub_totals_row["total"])
            if existing_sub_total > 0 and budget.amount < existing_sub_total:
                formatted_sub = f"{existing_sub_total:,.0f}"
                formatted_main = f"{budget.amount:,.0f}"
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Your sub-category budgets total ${formatted_sub}, which is higher than the {budget.category} budget of ${formatted_main}.\n"
                        f"Please increase the {budget.category} budget or adjust the sub-category amounts."
                    ),
                )

        # Category budgets must belong to an overall budget (same month): sum of main category budgets <= overall budget
        row = conn.execute(text("SELECT subcategory, amount FROM budgets WHERE id = :id"), {"id": budget_id}).fetchone()
        _, current_main_sum = _get_overall_and_category_sum(conn, budget.month)
        # Subtract old amount if this row was a main category, add new amount if updated row is main category
        old_contrib = float(row[1]) if row and row[0] in (None, "") else 0
        new_contrib = float(budget.amount) if budget.subcategory in (None, "") else 0
        new_main_sum = current_main_sum - old_contrib + new_contrib
        _check_category_sum_within_overall(conn, budget.month, new_main_sum)

        query = text(
            """
            UPDATE budgets
            SET month = :month, category = :category, subcategory = :subcategory, amount = :amount
            WHERE id = :id
        """
        )
        result = conn.execute(
            query,
            {
                "month": budget.month,
                "category": budget.category,
                "subcategory": budget.subcategory,
                "amount": budget.amount,
                "id": budget_id,
            },
        )
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Budget not found")
    return {"message": "Budget updated successfully"}

@router.delete("/api/budgets/{budget_id}")
def delete_budget(budget_id: int):
    query = text("DELETE FROM budgets WHERE id = :id")
    with engine.connect() as conn:
        result = conn.execute(query, {"id": budget_id})
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Budget not found")
    return {"message": "Budget deleted successfully"}

# --- COMPANY BUDGET MANAGEMENT API ---

class CompanyBudgetModel(BaseModel):
    month: str
    amount: float

@router.get("/api/company_budgets")
def get_company_budgets(month: Optional[str] = None):
    query_str = "SELECT * FROM company_budgets"
    params = {}
    if month:
        query_str += " WHERE month = :month"
        params["month"] = month
    query_str += " ORDER BY month DESC"
    
    with engine.connect() as conn:
        rows = conn.execute(text(query_str), params).mappings().all()
    return [dict(r) for r in rows]

@router.post("/api/company_budgets")
def create_company_budget(budget: CompanyBudgetModel):
    query = text("""
        INSERT INTO company_budgets (month, amount)
        VALUES (:month, :amount)
        RETURNING id
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"month": budget.month, "amount": budget.amount})
        conn.commit()
        new_id = result.scalar()
    return {"id": new_id, "message": "Company budget created successfully"}

@router.put("/api/company_budgets/{budget_id}")
def update_company_budget(budget_id: int, budget: CompanyBudgetModel):
    query = text("""
        UPDATE company_budgets
        SET month = :month, amount = :amount
        WHERE id = :id
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"month": budget.month, "amount": budget.amount, "id": budget_id})
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Company budget not found")
    return {"message": "Company budget updated successfully"}

@router.delete("/api/company_budgets/{budget_id}")
def delete_company_budget(budget_id: int):
    query = text("DELETE FROM company_budgets WHERE id = :id")
    with engine.connect() as conn:
        result = conn.execute(query, {"id": budget_id})
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Company budget not found")
    return {"message": "Company budget deleted successfully"}

# --- OVERALL BUDGET MANAGEMENT API ---

class OverallBudgetModel(BaseModel):
    month: str
    amount: float
    description: Optional[str] = None

@router.get("/api/overall_budgets")
def get_overall_budgets(month: Optional[str] = None):
    query_str = "SELECT * FROM overall_budgets"
    params = {}
    if month:
        query_str += " WHERE month = :month"
        params["month"] = month
    query_str += " ORDER BY month DESC"
    
    with engine.connect() as conn:
        rows = conn.execute(text(query_str), params).mappings().all()
    return [dict(r) for r in rows]

@router.post("/api/overall_budgets")
def create_overall_budget(budget: OverallBudgetModel):
    min_month, max_month = get_overall_budget_month_range()
    if not (min_month <= budget.month <= max_month):
        raise HTTPException(
            status_code=400,
            detail=f"You can only set budgets from {min_month} up to {max_month}. Past and future months are not allowed.",
        )
    with engine.connect() as conn:
        # Check if budget already exists for this month
        existing = conn.execute(text("SELECT id FROM overall_budgets WHERE month = :month"), {"month": budget.month}).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Budget already exists for this month")
        # Sum of main category budgets must not exceed overall budget
        _check_overall_not_below_category_sum(conn, budget.month, float(budget.amount))
        # Insert new budget
        query = text("""
            INSERT INTO overall_budgets (month, amount, description)
            VALUES (:month, :amount, :description)
            RETURNING id
        """)
        result = conn.execute(
            query,
            {"month": budget.month, "amount": budget.amount, "description": budget.description},
        )
        conn.commit()
        new_id = result.scalar()
    return {"id": new_id, "message": "Overall budget created successfully"}

@router.put("/api/overall_budgets/{budget_id}")
def update_overall_budget(budget_id: int, budget: OverallBudgetModel):
    min_month, max_month = get_overall_budget_month_range()
    if not (min_month <= budget.month <= max_month):
        raise HTTPException(
            status_code=400,
            detail=f"You can only set budgets from {min_month} up to {max_month}. Past and future months are not allowed.",
        )
    query = text(
        """
        UPDATE overall_budgets
        SET month = :month, amount = :amount, description = :description
        WHERE id = :id
    """
    )
    with engine.connect() as conn:
        # Sum of main category budgets must not exceed overall budget
        _check_overall_not_below_category_sum(conn, budget.month, float(budget.amount))
        result = conn.execute(
            query,
            {
                "month": budget.month,
                "amount": budget.amount,
                "description": budget.description,
                "id": budget_id,
            },
        )
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Overall budget not found")
    return {"message": "Overall budget updated successfully"}

@router.delete("/api/overall_budgets/{budget_id}")
def delete_overall_budget(budget_id: int):
    query = text("DELETE FROM overall_budgets WHERE id = :id")
    with engine.connect() as conn:
        result = conn.execute(query, {"id": budget_id})
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Overall budget not found")
    return {"message": "Overall budget deleted successfully"}


# --- KEY INSIGHTS (aggregates budgets + expenses for a month) ---
@router.get("/api/key-insights")
def get_key_insights(
    start_date: date = Query(...),
    end_date: date = Query(...),
    month: Optional[str] = None,
    sales_only: bool = Query(False),
    source: str = Query('both')
):
    s = (source or 'both').lower()

    # 1) load budgets for month
    budgets = []
    if month:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT category, COALESCE(subcategory, '') AS subcategory, amount FROM budgets WHERE month = :month"), {"month": month}).mappings().all()
        budgets = [dict(r) for r in rows]

    # map budgets by (category, subcategory) - normalize category to match frontend
    budget_map = {}
    for b in budgets:
        key = (_normalize_category_server(b.get('category') or ''), (b.get('subcategory') or '').strip())
        budget_map[key] = float(b.get('amount') or 0)

    # 2) gather expense totals from reporting DB and optional entries DB
    results = {}

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
                        cat = _normalize_category_server((r.get('category') or '').strip())
                        sub = (r.get('subcategory') or '').strip()
                        key = (cat, sub)
                        results[key] = results.get(key, 0) + abs(float(r.get('total') or 0))
                except Exception:
                    continue

    if s in ('entries', 'both'):
        q_entries = text("""
            SELECT category, COALESCE(TRIM(description), '') AS subcategory, SUM(balance) AS total, staff_name
            FROM entries
            WHERE entry_type = 'expense' AND date BETWEEN :start AND :end
              AND (:sales_only = false OR (staff_name IS NOT NULL AND TRIM(staff_name) <> ''))
            GROUP BY category, COALESCE(TRIM(description), ''), staff_name
        """)
        try:
            with cafe_engine.connect() as conn:
                rows = conn.execute(q_entries, {"start": start_date, "end": end_date, "sales_only": sales_only}).mappings().all()
                for r in rows:
                    cat = _normalize_category_server((r.get('category') or '').strip())
                    sub = (r.get('subcategory') or '').strip()
                    key = (cat, sub)
                    results[key] = results.get(key, 0) + abs(float(r.get('total') or 0))
        except Exception:
            # if cafe DB not available, ignore entries-source
            pass

    # 3) build entries list combining budgets and actuals
    entries = []
    seen_keys = set()

    # include keys from budgets and results
    for (cat, sub) in list(set(list(budget_map.keys()) + list(results.keys()))):
        key = (cat or '', sub or '')
        if key in seen_keys:
            continue
        seen_keys.add(key)
        budgeted = float(budget_map.get(key) or 0)
        actual = float(results.get(key) or 0)

        # status: exclude main-level rows (blank subcategory) from counts; still include in entries with subcategory '' marked as main
        variance = budgeted - actual
        percent = (abs(variance) / budgeted * 100) if budgeted else 0
        if not sub or sub.strip() == '':
            status = 'Main'
        else:
            if not budgeted or budgeted == 0:
                status = 'No Budget Creation'
            else:
                if percent <= 5:
                    status = 'Near Budget'
                else:
                    status = 'Under Budget' if variance >= 0 else 'Over Budget'

        entries.append({
            'category': cat,
            'subcategory': sub or None,
            'budgeted': round(budgeted, 2),
            'actual': round(actual, 2),
            'variance': round(variance, 2),
            'status': status
        })

    # 4) top expensive subcategories (exclude blank subcategory)
    tops = sorted(
        [{'category': k[0], 'subcategory': k[1], 'actual': v} for k, v in results.items() if k[1] and k[1].strip() != ''],
        key=lambda x: x['actual'], reverse=True
    )

    # 5) summary counts (exclude main-level / blank subcategories from counts)
    summary_counts = {'Under Budget': {'count': 0, 'total': 0}, 'Over Budget': {'count': 0, 'total': 0}, 'Near Budget': {'count': 0, 'total': 0}, 'No Budget Creation': {'count': 0, 'total': 0}}
    alerts = 0
    for e in entries:
        if not e.get('subcategory'):
            continue
        st = e.get('status')
        if st == 'Under Budget':
            summary_counts['Under Budget']['count'] += 1
            summary_counts['Under Budget']['total'] += max(0, e.get('variance') or 0)
        elif st == 'Over Budget':
            summary_counts['Over Budget']['count'] += 1
            summary_counts['Over Budget']['total'] += max(0, -(e.get('variance') or 0))
            alerts += 1
        elif st == 'Near Budget':
            summary_counts['Near Budget']['count'] += 1
            summary_counts['Near Budget']['total'] += abs(e.get('variance') or 0)
        elif st == 'No Budget Creation':
            summary_counts['No Budget Creation']['count'] += 1
            summary_counts['No Budget Creation']['total'] += e.get('actual') or 0

    recommendations = []
    # simple recommendation: focus on top over-budget items
    biggest_over = next((x for x in entries if x.get('status') == 'Over Budget' and x.get('subcategory')), None)
    if biggest_over:
        recommendations.append(f"Review purchases for {biggest_over.get('category')} / {biggest_over.get('subcategory')} .")

    return {
        'top_expensive': tops[:5],
        'entries': entries,
        'alerts': alerts,
        'recommendations': recommendations,
        'summary': summary_counts
    }


@router.get("/api/expense-by-subcategory")
def expense_by_subcategory(
    start_date: date = Query(...),
    end_date: date = Query(...),
    sales_only: bool = Query(False),
    source: str = Query('both')
):
    """Return aggregated expense totals by (category, subcategory).
    `source` can be 'reporting', 'entries', or 'both'.
    """
    s = (source or 'both').lower()
    results = {}

    if s in ('reporting', 'both'):
        q = text("""
            SELECT category, COALESCE(TRIM(description), '') AS subcategory, SUM(amount) AS total
            FROM (
                SELECT category, description, amount, date FROM checking_account_main
                UNION ALL
                SELECT category, description, amount, date FROM checking_account_secondary
                UNION ALL
                SELECT category, vendor AS description, amount, date FROM credit_card_account
            ) AS combined
            WHERE date BETWEEN :start AND :end
            GROUP BY category, COALESCE(TRIM(description), '')
        """)
        try:
            with engine.connect() as conn:
                rows = conn.execute(q, {"start": start_date, "end": end_date}).mappings().all()
                for r in rows:
                    cat = (r.get('category') or '').strip()
                    sub = (r.get('subcategory') or '').strip()
                    key = (cat, sub)
                    results[key] = results.get(key, 0) + abs(float(r.get('total') or 0))
        except Exception:
            pass

    if s in ('entries', 'both'):
        q_entries = text("""
            SELECT category, COALESCE(TRIM(description), '') AS subcategory, SUM(balance) AS total
            FROM entries
            WHERE entry_type = 'expense' AND date BETWEEN :start AND :end
            GROUP BY category, COALESCE(TRIM(description), '')
        """)
        try:
            with cafe_engine.connect() as conn:
                rows = conn.execute(q_entries, {"start": start_date, "end": end_date}).mappings().all()
                for r in rows:
                    cat = (r.get('category') or '').strip()
                    sub = (r.get('subcategory') or '').strip()
                    key = (cat, sub)
                    results[key] = results.get(key, 0) + abs(float(r.get('total') or 0))
        except Exception:
            pass

    out = []
    for (cat, sub), total in results.items():
        out.append({"category": cat, "subcategory": sub, "total": round(total, 2)})
    return out