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

    Examples:
      * 'Operating Expense', 'opex' -> 'Operating expense'
      * 'COGS' stays 'COGS'
      * returns the input string trimmed when no rule applies.
    """
    if not cat:
        return ''
    c = str(cat).strip()
    low = c.lower()
    # treat common variations of operating expense
    if low in ('operating expense', 'opex', 'operating'):
        return 'Operating expense'
    if low == 'cogs':
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
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS payroll_budgets (
                id SERIAL PRIMARY KEY,
                month TEXT NOT NULL,
                amount NUMERIC(12,2) NOT NULL,
                description TEXT
            )
        """))
        # Ensure columns exist even if table was created with an older structure
        conn.execute(text("ALTER TABLE overall_budgets ADD COLUMN IF NOT EXISTS month TEXT"))
        conn.execute(text("ALTER TABLE overall_budgets ADD COLUMN IF NOT EXISTS description TEXT"))
        conn.execute(text("ALTER TABLE payroll_budgets ADD COLUMN IF NOT EXISTS month TEXT"))
        conn.execute(text("ALTER TABLE payroll_budgets ADD COLUMN IF NOT EXISTS description TEXT"))
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
    # include payroll_budgets for the same month as part of main/category totals
    payroll_row = conn.execute(text("SELECT COALESCE(SUM(amount),0) AS total FROM payroll_budgets WHERE month = :month"), {"month": month}).fetchone()
    payroll_total = float(payroll_row[0]) if payroll_row else 0.0
    main_sum = float(main_sum_row["total"]) + payroll_total
    return overall_amount, main_sum


def _get_main_category_breakdown(conn, month: str):
    """
    Helper used for validation rules that depend on how many main categories
    are already budgeted. Returns (cat_totals, payroll_total) where:
      - cat_totals: dict like {'COGS': amount, 'Operating expense': amount, ...}
      - payroll_total: sum of payroll_budgets for the month.
    """
    rows = conn.execute(
        text(
            """
            SELECT category, COALESCE(SUM(amount),0) AS total
            FROM budgets
            WHERE month = :month AND subcategory IS NULL
            GROUP BY category
            """
        ),
        {"month": month},
    ).mappings().all()
    cat_totals = {row["category"]: float(row["total"] or 0) for row in rows}
    payroll_row = conn.execute(
        text("SELECT COALESCE(SUM(amount),0) FROM payroll_budgets WHERE month = :month"),
        {"month": month},
    ).fetchone()
    payroll_total = float(payroll_row[0] or 0) if payroll_row else 0.0
    return cat_totals, payroll_total


def _get_payroll_base(conn):
    """
    Return the sum of base salaries used as the minimum payroll budget:
      - Prefer employees.base_salary if the table exists and has data
      - Fallback to employees_static.base_pay (used by the payroll insights API)
    """
    payroll_base = 0.0
    try:
        base_row = None
        # Try employees.base_salary first
        try:
            base_row = conn.execute(text("SELECT COALESCE(SUM(base_salary),0) FROM employees")).fetchone()
        except Exception:
            # SELECT failed (e.g. table doesn't exist) -> rollback this failed statement
            try:
                conn.rollback()
            except Exception:
                pass
            base_row = None
        if base_row and float(base_row[0] or 0) > 0:
            payroll_base = float(base_row[0] or 0)
        else:
            # Fallback to employees_static.base_pay
            try:
                base_row = conn.execute(text("SELECT COALESCE(SUM(base_pay),0) FROM employees_static")).fetchone()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                base_row = None
            if base_row:
                payroll_base = float(base_row[0] or 0)
    except Exception:
        payroll_base = 0.0
    return payroll_base


def _check_category_sum_within_overall(conn, month: str, main_category_sum: float):
    """Raise if overall budget exists for month and main_category_sum exceeds it."""
    overall_amount, _ = _get_overall_and_category_sum(conn, month)
    if overall_amount is not None and main_category_sum >= overall_amount:
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
    if main_sum > 0 and overall_amount <= main_sum:
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
            detail=f"No overall budget set for {month}. Please add an overall budget first.",
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
    # normalize user input so that database rows are consistent and later
    # comparisons (especially in finalize) are simpler
    budget_month = budget.month
    cat = _normalize_category_server(budget.category)
    sub = budget.subcategory.strip() if budget.subcategory else None

    with engine.connect() as conn:
        # Category budgets require an overall budget for the same month first
        _require_overall_budget_for_month(conn, budget_month)
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
                "month": budget_month,
                "category": cat,
                "subcategory": sub,
            },
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Budget already exists for this category and month",
            )

        # Budget hierarchy rules between main category and sub-categories
        if sub not in (None, ""):
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
                    "month": budget_month,
                    "category": cat,
                },
            ).fetchone()

            if main_row is None:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"No main {cat} budget found for {budget_month}. "
                        f"Please create the main {cat} budget first."
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
                    "month": budget_month,
                    "category": cat,
                },
            ).mappings().one()

            existing_sub_total = float(sub_totals_row["total"])
            new_total = existing_sub_total + float(budget.amount)

            if new_total > main_amount:
                formatted_main = f"{main_amount:,.0f}"
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Sub-category budget exceeds the {budget.category} budget of ${formatted_main}.\n"
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
        overall_amount, current_main_sum = _get_overall_and_category_sum(conn, budget_month)
        new_main_sum = current_main_sum + (float(budget.amount) if sub in (None, "") else 0)

        # first verify we aren't pushing the main categories past the overall budget;
        # this error message triggers the front-end finalize panel.  perform this
        # check before the "90% rule" below so that attempted overrun results in
        # the more actionable overrun message instead of the 90% warning.
        _check_category_sum_within_overall(conn, budget.month, new_main_sum)

        # Extra rule: if after this main-category change only 2 of the 3 main categories
        # (COGS, Operating expense, Payroll) are non-zero, their combined total must not
        # exceed 90% of the overall budget. This leaves at least 10% room for the last category.
        # only enforce the 90% rule when the overall budget has not already been exceeded,
        # since the overrun check above already rejected those cases.
        if overall_amount is not None and sub in (None, ""):
            cat_totals, payroll_total = _get_main_category_breakdown(conn, budget_month)
            cat_name = _normalize_category_server(cat)
            cogs_after = float(cat_totals.get("COGS", 0.0))
            opex_after = float(cat_totals.get("Operating expense", 0.0))
            if cat_name == "COGS":
                cogs_after += float(budget.amount)
            elif cat_name == "Operating expense":
                opex_after += float(budget.amount)
            main_sum_after = cogs_after + opex_after + payroll_total
            active_count = (1 if cogs_after > 0 else 0) + (1 if opex_after > 0 else 0) + (1 if payroll_total > 0 else 0)
            if active_count == 2:
                max_two_cat_sum = overall_amount * 0.9
                if main_sum_after > max_two_cat_sum:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"With only two main categories budgeted, their total (${main_sum_after:,.0f}) "
                            f"must not exceed 90% of the overall budget (${overall_amount:,.0f}) so that the "
                            "remaining category can still be budgeted."
                        ),
                    )

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
                "month": budget_month,
                "category": cat,
                "subcategory": sub,
                "amount": budget.amount,
            },
        )
        conn.commit()
        new_id = result.scalar()
    return {"id": new_id, "message": "Budget created successfully"}

@router.put("/api/budgets/{budget_id}")
def update_budget(budget_id: int, budget: BudgetModel):
    # normalize inputs
    budget_month = budget.month
    cat = _normalize_category_server(budget.category)
    sub = budget.subcategory.strip() if budget.subcategory else None

    with engine.connect() as conn:
        # Category budgets require an overall budget for the same month first
        _require_overall_budget_for_month(conn, budget_month)
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
                "month": budget_month,
                "category": cat,
                "subcategory": sub,
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
                        f"Sub-category budget exceeds the {budget.category} budget of ${formatted_main}.\n"
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
    from datetime import date
    today = date.today()
    current_month = today.strftime("%Y-%m")
    with engine.connect() as conn:
        # Get the month and subcategory for this budget
        row = conn.execute(text("SELECT month, subcategory FROM budgets WHERE id = :id"), {"id": budget_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Budget not found")
        month, subcategory = row[0], row[1]
        # Prevent deletion of main category budget for current month
        if month == current_month and (subcategory is None or str(subcategory).strip() == ""):
            raise HTTPException(status_code=400, detail="Cannot delete ongoing budget")
        query = text("DELETE FROM budgets WHERE id = :id")
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
    from datetime import date
    today = date.today()
    current_month = today.strftime("%Y-%m")
    with engine.connect() as conn:
        # Get the month for this overall budget
        row = conn.execute(text("SELECT month FROM overall_budgets WHERE id = :id"), {"id": budget_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Overall budget not found")
        month = row[0]
        if month == current_month:
            raise HTTPException(status_code=400, detail="You cannot delete the overall budget for the current month. You may only edit it.")
        query = text("DELETE FROM overall_budgets WHERE id = :id")
        result = conn.execute(query, {"id": budget_id})
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Overall budget not found")
    return {"message": "Overall budget deleted successfully"}


# --- PAYROLL BUDGETS API ---
class PayrollBudgetModel(BaseModel):
    month: str
    amount: float
    description: Optional[str] = None


@router.get("/api/payroll_budgets")
def get_payroll_budgets(month: Optional[str] = None):
    query_str = "SELECT * FROM payroll_budgets"
    params = {}
    if month:
        query_str += " WHERE month = :month"
        params["month"] = month
    query_str += " ORDER BY month DESC"
    with engine.connect() as conn:
        rows = conn.execute(text(query_str), params).mappings().all()
    return [dict(r) for r in rows]


@router.post("/api/payroll_budgets")
def create_payroll_budget(budget: PayrollBudgetModel):
    min_month, max_month = get_overall_budget_month_range()
    if not (min_month <= budget.month <= max_month):
        raise HTTPException(status_code=400, detail=f"You can only set budgets from {min_month} up to {max_month}. Past and future months are not allowed.")
    with engine.connect() as conn:
        # Require an overall budget for this month
        _require_overall_budget_for_month(conn, budget.month)

        # Prevent duplicate for same month
        existing = conn.execute(text("SELECT id FROM payroll_budgets WHERE month = :month"), {"month": budget.month}).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Payroll budget already exists for this month")

        # Ensure sum of main categories + this payroll budget does not exceed overall budget,
        # and if this makes only 2 of the 3 main categories non-zero, reserve at least 10% for the last one.
        # Also ensure payroll budget is never below the sum of base salaries.
        overall_amount, main_sum = _get_overall_and_category_sum(conn, budget.month)
        if overall_amount is not None:
            cat_totals, current_payroll = _get_main_category_breakdown(conn, budget.month)
            payroll_after = current_payroll + float(budget.amount)
            cogs_amount = float(cat_totals.get("COGS", 0.0))
            opex_amount = float(cat_totals.get("Operating expense", 0.0))
            main_sum_after = cogs_amount + opex_amount + payroll_after

            # Standard rule: total must be < overall
            if main_sum_after >= overall_amount:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Sum of main category budgets including payroll ({main_sum_after}) "
                        f"must be less than overall budget ({overall_amount}) for {budget.month}."
                    ),
                )

            # Extra rule: when only two categories are non-zero (e.g. COGS + Operating, or
            # COGS + Payroll, etc.), require that they do not consume more than 90% of overall.
            active_count = (1 if cogs_amount > 0 else 0) + (1 if opex_amount > 0 else 0) + (1 if payroll_after > 0 else 0)
            if active_count == 2:
                max_two_cat_sum = overall_amount * 0.9
                if main_sum_after > max_two_cat_sum:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"With only two main categories budgeted, their total (${main_sum_after:,.0f}) "
                            f"must not exceed 90% of the overall budget (${overall_amount:,.0f}) so that the "
                            "remaining category can still be budgeted."
                        ),
                    )

            # New rule: payroll budget must be at least the sum of base salaries
            payroll_base = _get_payroll_base(conn)
            if payroll_base and payroll_after < payroll_base:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Payroll budget for {budget.month} (${payroll_after:,.0f}) "
                        f"cannot be less than total base salaries (${payroll_base:,.0f}). "
                        "Increase the payroll budget or reduce base salaries."
                    ),
                )

        q = text("""
            INSERT INTO payroll_budgets (month, amount, description)
            VALUES (:month, :amount, :description)
            RETURNING id
        """)
        result = conn.execute(q, {"month": budget.month, "amount": budget.amount, "description": budget.description})
        conn.commit()
        new_id = result.scalar()
    return {"id": new_id, "message": "Payroll budget created successfully"}


@router.put("/api/payroll_budgets/{budget_id}")
def update_payroll_budget(budget_id: int, budget: PayrollBudgetModel):
    min_month, max_month = get_overall_budget_month_range()
    if not (min_month <= budget.month <= max_month):
        raise HTTPException(status_code=400, detail=f"You can only set budgets from {min_month} up to {max_month}. Past and future months are not allowed.")
    q = text("""
        UPDATE payroll_budgets
        SET month = :month, amount = :amount, description = :description
        WHERE id = :id
    """)
    with engine.connect() as conn:
        # fetch existing row to compute adjusted sums if updating same month
        old = conn.execute(text("SELECT month, amount FROM payroll_budgets WHERE id = :id"), {"id": budget_id}).fetchone()
        if not old:
            raise HTTPException(status_code=404, detail="Payroll budget not found")

        # Require overall budget for target month
        _require_overall_budget_for_month(conn, budget.month)

        # Compute new main sum for the target month (subtract old amount if same month)
        overall_amount, main_sum = _get_overall_and_category_sum(conn, budget.month)
        adjusted_main_sum = main_sum
        try:
            old_month = old[0]
            old_amount = float(old[1] or 0)
        except Exception:
            old_month = None
            old_amount = 0.0

        if old_month == budget.month:
            adjusted_main_sum = main_sum - old_amount + float(budget.amount)
        else:
            adjusted_main_sum = main_sum + float(budget.amount)

        if overall_amount is not None:
            # Standard rule: total must be < overall
            if adjusted_main_sum >= overall_amount:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Sum of main category budgets including payroll ({adjusted_main_sum}) "
                        f"must be less than overall budget ({overall_amount}) for {budget.month}."
                    ),
                )

            # Extra rule: when only two categories are non-zero after this change,
            # require that they do not consume more than 90% of overall.
            cat_totals, current_payroll = _get_main_category_breakdown(conn, budget.month)
            # remove old payroll from breakdown if it belonged to this month, then add new
            if old_month == budget.month:
                payroll_after = current_payroll - old_amount + float(budget.amount)
            else:
                payroll_after = current_payroll + float(budget.amount)

            cogs_amount = float(cat_totals.get("COGS", 0.0))
            opex_amount = float(cat_totals.get("Operating expense", 0.0))
            main_sum_after = cogs_amount + opex_amount + payroll_after

            # 90% rule when only two categories are non-zero
            active_count = (1 if cogs_amount > 0 else 0) + (1 if opex_amount > 0 else 0) + (1 if payroll_after > 0 else 0)
            if active_count == 2:
                max_two_cat_sum = overall_amount * 0.9
                if main_sum_after > max_two_cat_sum:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"With only two main categories budgeted, their total (${main_sum_after:,.0f}) "
                            f"must not exceed 90% of the overall budget (${overall_amount:,.0f}) so that the "
                            "remaining category can still be budgeted."
                        ),
                    )

            # New rule: payroll budget must be at least the sum of base salaries
            payroll_base = _get_payroll_base(conn)
            if payroll_base and payroll_after < payroll_base:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Payroll budget for {budget.month} (${payroll_after:,.0f}) "
                        f"cannot be less than total base salaries (${payroll_base:,.0f}). "
                        "Increase the payroll budget or reduce base salaries."
                    ),
                )
        result = conn.execute(q, {"month": budget.month, "amount": budget.amount, "description": budget.description, "id": budget_id})
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Payroll budget not found")
    return {"message": "Payroll budget updated successfully"}


@router.delete("/api/payroll_budgets/{budget_id}")
def delete_payroll_budget(budget_id: int):
    # Prevent deletion of ongoing (current-month) payroll budgets
    q_sel = text("SELECT month FROM payroll_budgets WHERE id = :id")
    with engine.connect() as conn:
        row = conn.execute(q_sel, {"id": budget_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Payroll budget not found")
        # `fetchone()` returns a Row; use index access (first column is month)
        try:
            budget_month = row[0]
        except Exception:
            # Fallback to mapping access if available
            try:
                budget_month = row['month']
            except Exception:
                budget_month = None
        current_month = date.today().strftime("%Y-%m")
        if budget_month == current_month:
            raise HTTPException(status_code=400, detail="Cannot delete ongoing payroll budget for the current month")

        q = text("DELETE FROM payroll_budgets WHERE id = :id")
        result = conn.execute(q, {"id": budget_id})
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Payroll budget not found")
    return {"message": "Payroll budget deleted successfully"}


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

@router.get("/api/latest-labor-cost")
def get_latest_labor_cost():
    """Fetch the most recent Payroll entry from entries table."""
    with cafe_engine.connect() as conn:
        row = conn.execute(text("""
            SELECT balance, date, staff_name, description
            FROM entries
            WHERE category = 'Payroll'
              AND entry_type = 'expense'
            ORDER BY date DESC, id DESC
            LIMIT 1
        """), {}).fetchone()
    if row:
        return {
            "labor_cost": float(row[0]),
            "date": str(row[1]),
            "staff_name": row[2],
            "description": row[3]
        }
    return {"labor_cost": None}

@router.get("/api/sum-labor-cost")
def get_sum_labor_cost(month: str = None):
    """Fetch the sum of Payroll entries from entries table for admin for a specific month."""
    query = "SELECT COALESCE(SUM(balance), 0) AS total FROM entries WHERE category = 'Payroll' AND entry_type = 'expense' AND staff_name = 'Admin'"
    params = {}
    if month:
        query += " AND TO_CHAR(date, 'YYYY-MM') = :month"
        params["month"] = month
    with cafe_engine.connect() as conn:
        row = conn.execute(text(query), params).fetchone()
    return {"labor_cost_sum": float(row[0])}


# --- KPI endpoints and finalize logic ---
@router.get('/api/budget-summary')
def get_budget_summary(month: str = Query(..., description="Month YYYY-MM")):
    """Return overall and main_sum (COGS + Operating + Payroll) for overrun detection. Uses same logic as validation."""
    with engine.connect() as conn:
        overall_amount, main_sum = _get_overall_and_category_sum(conn, month)
    return {
        "month": month,
        "overall": overall_amount,
        "main_sum": round(main_sum, 2),
        "overrun": overall_amount is not None and main_sum > overall_amount,
    }


@router.get('/api/kpis')
def get_kpis(month: Optional[str] = None):
    """Return four small KPIs for the requested month: overall, COGS, Operating expense, Payroll.
    Each KPI includes: budgeted, payroll/base (for payroll KPI), and percent_of_overall.
    """
    if not month:
        raise HTTPException(status_code=400, detail="month is required in YYYY-MM format")
    with engine.connect() as conn:
        # overall budget for month
        overall_row = conn.execute(text("SELECT amount FROM overall_budgets WHERE month = :month"), {"month": month}).fetchone()
        overall = float(overall_row[0]) if overall_row else None

        # main category budgets (subcategory IS NULL)
        rows = conn.execute(text(
            "SELECT category, COALESCE(SUM(amount),0) AS total FROM budgets WHERE month = :month AND subcategory IS NULL GROUP BY category"
        ), {"month": month}).mappings().all()
        cat_map = {r['category']: float(r['total']) for r in rows}

        # payroll budget
        payroll_row = conn.execute(text("SELECT COALESCE(SUM(amount),0) FROM payroll_budgets WHERE month = :month"), {"month": month}).fetchone()
        payroll_budget = float(payroll_row[0]) if payroll_row else 0.0

        # attempt to fetch base payroll (sum of base salaries) if employees table exists
        payroll_base = 0.0
        try:
            base_row = conn.execute(text("SELECT COALESCE(SUM(base_salary),0) FROM employees")).fetchone()
            if base_row:
                payroll_base = float(base_row[0])
        except Exception:
            payroll_base = 0.0

        cogs = cat_map.get('COGS', 0.0)
        opex = cat_map.get('Operating expense', 0.0)

        def pct(x):
            try:
                return round((x / overall) * 100, 1) if overall and overall > 0 else None
            except Exception:
                return None

        return {
            'month': month,
            'overall': {'budgeted': overall},
            'cogs': {'budgeted': cogs, 'percent_of_overall': pct(cogs)},
            'operating': {'budgeted': opex, 'percent_of_overall': pct(opex)},
            'payroll': {'budgeted': payroll_budget, 'base': payroll_base, 'percent_of_overall': pct(payroll_budget)}
        }


@router.post('/api/finalize-budgets')

def finalize_budgets(month: str = Query(..., description="Month in YYYY-MM format"),
                     pending_category: Optional[str] = Query(None, description="Category of an unsaved budget to include"),
                     pending_amount: Optional[float] = Query(None, description="Amount of an unsaved budget to include")):
    """Finalize budgets for a month by computing a scaling factor and applying it to main category budgets.
    Ensures payroll is not scaled below base payroll (from `employees.base_salary` if available).
    If `pending_category`/`pending_amount` are provided they are treated as an additional
    budget entry (used when the user attempted to save a category and hit overrun).
    Returns the applied factor and updated amounts.
    """
    with engine.connect() as conn:
        try:
            # fetch overall
            try:
                overall_row = conn.execute(text("SELECT amount FROM overall_budgets WHERE month = :month"), {"month": month}).fetchone()
            except Exception as e:
                print(f"[finalize_budgets] error fetching overall for {month}: {e}")
                raise
            if not overall_row:
                raise HTTPException(status_code=400, detail=f"No overall budget set for {month}")
            overall = float(overall_row[0])

            # fetch main categories totals (COGS and Operating expense) - we'll keep track of ids
            try:
                rows = conn.execute(text(
                    "SELECT id, category, COALESCE(amount,0) AS amount FROM budgets WHERE month = :month AND subcategory IS NULL"
                ), {"month": month}).mappings().all()
            except Exception as e:
                print(f"[finalize_budgets] error fetching budget rows for {month}: {e}")
                raise
            cat_rows = list(rows)
            # map by normalized category name for easier access
            cat_map = {r['category']: float(r['amount']) for r in cat_rows}
            cogs_amt = float(cat_map.get('COGS', 0.0))
            opex_amt = float(cat_map.get('Operating expense', 0.0))

            # include payroll_budgets in original main sum for factor reporting
            try:
                p_row = conn.execute(text("SELECT id, COALESCE(amount,0) FROM payroll_budgets WHERE month = :month"), {"month": month}).fetchone()
            except Exception as e:
                print(f"[finalize_budgets] error fetching payroll row for {month}: {e}")
                raise
            payroll_amount = float(p_row[1]) if p_row else 0.0
            payroll_id = int(p_row[0]) if p_row and p_row[0] is not None else None

            # if there's a pending (unsaved) budget, include it now for calculations
            if pending_category and pending_amount is not None:
                cat = str(pending_category).strip()
                if cat.lower() == 'cogs':
                    cogs_amt += float(pending_amount)
                elif cat.lower() == 'operating expense':
                    opex_amt += float(pending_amount)
                elif cat.lower() == 'payroll':
                    payroll_amount += float(pending_amount)
                # note: we do not immediately insert a row here; the later upsert logic
                # will take care of creating the missing main category entry if needed.

            main_sum = cogs_amt + opex_amt + payroll_amount
            if main_sum == 0:
                raise HTTPException(status_code=400, detail="No main category budgets to scale")

            # get payroll base using shared helper
            payroll_base = _get_payroll_base(conn)

            # payroll should not be scaled down below either its current amount or its base
            payroll_target = payroll_amount
            if payroll_base and payroll_target < payroll_base:
                payroll_target = payroll_base
            # compute how much of the overall remains for COGS + OPEX
            remaining = overall - payroll_target
            warning_msg = None
            if remaining < 0:
                # We used to abort here because the payroll base alone exceeded
                # the overall budget.  That prevented any COGS/OPEX rows from
                # being created and left the caller confused ("OPEX never got
                # a budget").  Instead of blowing up we'll proceed but reserve
                # *all* of the budget for payroll and shrink the other two
                # categories to a very small non‑zero amount.  The frontend can
                # still inspect the returned factor/updates and display an error
                # if desired.
                warning_msg = (
                    f"Overall budget ({overall}) is smaller than payroll base "
                    f"({payroll_base}); COGS/OPEX were scaled to minimal values."
                )
                print(f"[finalize_budgets] {warning_msg}")
                remaining = 0

            # determine new amounts for COGS and OPEX based on their current (and pending) values
            if cogs_amt > 0 and opex_amt > 0:
                sub_factor = remaining / (cogs_amt + opex_amt)
                new_cogs = round(cogs_amt * sub_factor, 2)
                new_opex = round(opex_amt * sub_factor, 2)
            else:
                # if one or both categories had no budget, split remaining evenly so each gets some
                new_cogs = round(remaining / 2, 2)
                new_opex = round(remaining / 2, 2)

            # enforce minimum nonzero
            if new_cogs <= 0:
                new_cogs = 0.01
            if new_opex <= 0:
                new_opex = 0.01

            # payroll amount is fixed at payroll_target (no scaling down)
            new_payroll_amount = round(payroll_target, 2)

            # compute a factor representing how cogs+opex changed relative to prior sum
            prior_cats = cogs_amt + opex_amt
            if prior_cats > 0:
                factor = remaining / prior_cats
            else:
                # nothing to scale (both cats zero) so factor 1 keeps subcategories unchanged
                factor = 1

            # apply updated values back to the DB
            updates = []
            # helper to upsert a main category row
            def _upsert_main(cat_name, amount):
                nonlocal updates
                # look for an existing row using normalized names so that
                # variants like "OPEX" vs "Operating expense" don't cause a
                # duplicate to be inserted.
                def _norm(s):
                    return _normalize_category_server(s or '').lower()
                row = next((r for r in cat_rows if _norm(r['category']) == _norm(cat_name)), None)
                if row:
                    cid = int(row['id'])
                    old = float(row['amount'])
                    try:
                        conn.execute(text("UPDATE budgets SET amount = :amount WHERE id = :id"), {"amount": amount, "id": cid})
                        updates.append({'id': cid, 'category': cat_name, 'old': old, 'new': amount})
                    except Exception as e:
                        print(f"[finalize_budgets] failed updating budget id={cid}: {e}")
                        conn.rollback()
                        raise HTTPException(status_code=500, detail=f"Failed updating budget id={cid}: {str(e)}")
                else:
                    # insert row when category was missing
                    try:
                        res = conn.execute(text("INSERT INTO budgets (month, category, subcategory, amount) VALUES (:month, :cat, NULL, :amt) RETURNING id"), {"month": month, "cat": cat_name, "amt": amount})
                        new_id = None
                        try:
                            new_id = int(res.fetchone()[0])
                        except Exception:
                            try:
                                new_id = int(res.scalar())
                            except Exception:
                                new_id = None
                        updates.append({'id': new_id, 'category': cat_name, 'old': 0, 'new': amount})
                    except Exception as e:
                        print(f"[finalize_budgets] failed inserting {cat_name} row: {e}")
                        conn.rollback()
                        raise HTTPException(status_code=500, detail=f"Failed inserting budget for {cat_name}: {str(e)}")

            # update/insert categories
            _upsert_main('COGS', new_cogs)
            _upsert_main('Operating expense', new_opex)

            # scale subcategory budget rows by the same factor so subcategory totals match main category
            try:
                sub_rows = conn.execute(text(
                    "SELECT id, COALESCE(amount,0) AS amount FROM budgets WHERE month = :month AND subcategory IS NOT NULL"
                ), {"month": month}).mappings().all()
                for r in sub_rows:
                    sid = int(r['id'])
                    old = float(r['amount'])
                    new_amt = round(old * factor, 2)
                    # never drive a previously-budgeted subcategory all the way to 0
                    if old > 0 and new_amt <= 0:
                        new_amt = 0.01
                    conn.execute(text("UPDATE budgets SET amount = :amount WHERE id = :id"), {"amount": new_amt, "id": sid})
                    updates.append({'id': sid, 'category': None, 'old': old, 'new': new_amt})
            except Exception as e:
                print(f"[finalize_budgets] error scaling subcategory rows: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass
                raise HTTPException(status_code=500, detail=f"Failed scaling subcategory budgets: {str(e)}")

            # update payroll_budgets row if exists
            if payroll_id is not None:
                try:
                    conn.execute(text("UPDATE payroll_budgets SET amount = :amount WHERE id = :id"), {"amount": new_payroll_amount, "id": payroll_id})
                except Exception as e:
                    print(f"[finalize_budgets] failed updating payroll id={payroll_id}: {e}")
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    raise HTTPException(status_code=500, detail=f"Failed updating payroll id={payroll_id}: {str(e)}")
            else:
                # create payroll row if it did not exist and new_payroll_amount > 0
                if new_payroll_amount > 0:
                    try:
                        res = conn.execute(text("INSERT INTO payroll_budgets (month, amount, description) VALUES (:month, :amount, :desc) RETURNING id"), {"month": month, "amount": new_payroll_amount, "desc": 'Scaled payroll on finalize'})
                        try:
                            payroll_id = int(res.fetchone()[0])
                        except Exception:
                            # some DB drivers return scalar differently
                            try:
                                payroll_id = int(res.scalar())
                            except Exception:
                                payroll_id = None
                    except Exception as e:
                        print(f"[finalize_budgets] failed inserting payroll row: {e}")
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        raise HTTPException(status_code=500, detail=f"Failed inserting payroll row: {str(e)}")

            conn.commit()

            result = {
                'month': month,
                'factor': round(factor, 6),
                'updates': updates,
                'payroll': {'id': payroll_id, 'old': payroll_amount, 'new': new_payroll_amount}
            }
            if warning_msg:
                result['warning'] = warning_msg
            return result
        except Exception as e:
            # print for server logs and return a clear HTTP error with diagnostic info
            print(f"[finalize_budgets] error while finalizing {month}: {e}")
            try:
                conn.rollback()
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=f"Finalize error: {str(e)}")


@router.get("/api/employees")
def get_employees():
    """Return active employees from employees_static (exclude employees_inactive)."""
    out = []
    try:
        with engine.connect() as conn:
            # load inactive ids/names if table exists
            inactive_ids = set()
            inactive_names = set()
            try:
                rows_inactive = conn.execute(text("SELECT employee_id, employee_name FROM employees_inactive")).mappings().all()
                for r in rows_inactive:
                    if r.get('employee_id'):
                        inactive_ids.add(r.get('employee_id'))
                    if r.get('employee_name'):
                        inactive_names.add(r.get('employee_name'))
            except Exception:
                # table may not exist; ignore
                pass

            try:
                rows = conn.execute(text("SELECT employee_id, employee_name, role, base_pay FROM employees_static ORDER BY employee_id")).mappings().all()
                for r in rows:
                    emp_id = r.get('employee_id')
                    name = r.get('employee_name')
                    if (emp_id and emp_id in inactive_ids) or (name and name in inactive_names):
                        continue
                    out.append({
                        'employee_id': emp_id,
                        'employee_name': name,
                        'role': r.get('role'),
                        'base_pay': float(r.get('base_pay') or 0)
                    })
            except Exception:
                pass
    except Exception:
        pass
    return out
