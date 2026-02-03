from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

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
        conn.commit()
        print("Budget tables created successfully")
except Exception as e:
    print(f"Database connection error: {e}")
    print("Please ensure PostgreSQL is running and the database exists.")

# --- BUDGET MANAGEMENT API ---

class BudgetModel(BaseModel):
    month: str
    category: str
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
    query = text("""
        INSERT INTO budgets (month, category, amount)
        VALUES (:month, :category, :amount)
        RETURNING id
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"month": budget.month, "category": budget.category, "amount": budget.amount})
        conn.commit()
        new_id = result.scalar()
    return {"id": new_id, "message": "Budget created successfully"}

@router.put("/api/budgets/{budget_id}")
def update_budget(budget_id: int, budget: BudgetModel):
    query = text("""
        UPDATE budgets
        SET month = :month, category = :category, amount = :amount
        WHERE id = :id
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"month": budget.month, "category": budget.category, "amount": budget.amount, "id": budget_id})
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