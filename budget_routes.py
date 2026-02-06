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

DATABASE_URL = "postgresql://postgres:Prim#2504@localhost:5432/coffeeshop_cashflow"
engine = create_engine(DATABASE_URL, poolclass=NullPool)

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
            # Sub-category: ensure total sub-category amount does not exceed main category (if any)
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

            if main_row is not None:
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
            # Sub-category: ensure total sub-category amount does not exceed main category (if any)
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

            if main_row is not None:
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