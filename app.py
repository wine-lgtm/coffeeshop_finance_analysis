import os
import sys
import argparse
import psycopg2
import uuid
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import date, datetime, timedelta
import psycopg2.extras

app = Flask(__name__)
app.secret_key = 'supersecretkey'

DB_NAME = "cafe_v2_db"
REPORTING_DB_NAME = "coffeeshop_cashflow"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_HOST = "localhost"
PAYROLL_BONUS_MAX_RATIO = 0.15
EMPLOYEE_FALLBACK = {
    "Arthur Morgan": ("E001", "Manager", 300.0),
    "Elena Fisher": ("E002", "Cashier", 180.0),
    "Victor Sullivan": ("E003", "Barista", 160.0),
    "Chloe Frazer": ("E004", "Barista", 160.0),
    "Leon Kennedy": ("E005", "Waiter", 120.0),
    "Claire Redfield": ("E006", "Waiter", 120.0),
    "Jill Valentine": ("E007", "Waiter", 120.0),
}

def fetch_employees_from_reporting():
    data = {}
    try:
        conn = get_reporting_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS employees_static (
                    employee_id TEXT PRIMARY KEY,
                    employee_name TEXT NOT NULL,
                    role TEXT,
                    base_pay NUMERIC(10,2) NOT NULL
                )
                """
            )
            conn.commit()
        except Exception:
            conn.rollback()
        try:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS employees_inactive (
                    employee_id TEXT,
                    employee_name TEXT NOT NULL
                )
                """
            )
            conn.commit()
        except Exception:
            conn.rollback()
        inactive_ids = set()
        inactive_names = set()
        cur.execute(
            """
            SELECT employee_id, employee_name
            FROM employees_inactive
            """
        )
        inactive_rows = cur.fetchall()
        for emp_id, name in inactive_rows:
            if emp_id:
                inactive_ids.add(emp_id)
            if name:
                inactive_names.add(name)
        cur.execute(
            """
            SELECT employee_id, employee_name, role, base_pay
            FROM employees_static
            ORDER BY employee_id
            """
        )
        rows_static = cur.fetchall()
        for emp_id, name, role, base_pay in rows_static:
            if emp_id in inactive_ids or name in inactive_names:
                continue
            data[name] = {
                "employee_id": emp_id,
                "employee_name": name,
                "role": role,
                "base_pay": float(base_pay or 0),
                "source": "static",
            }
        cur.execute(
            """
            SELECT employee_id, employee_name, role, MAX(net_pay) AS base_pay
            FROM payroll_history
            GROUP BY employee_id, employee_name, role
            ORDER BY employee_id
            """
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        for emp_id, name, role, base_pay in rows:
            if emp_id in inactive_ids or name in inactive_names:
                continue
            if name in data:
                continue
            data[name] = {
                "employee_id": emp_id,
                "employee_name": name,
                "role": role,
                "base_pay": float(base_pay or 0),
                "source": "history",
            }
    except Exception:
        data = {}
    if not data:
        for name, value in EMPLOYEE_FALLBACK.items():
            if name in inactive_names:
                continue
            emp_id, role, base_pay = value
            data[name] = {
                "employee_id": emp_id,
                "employee_name": name,
                "role": role,
                "base_pay": base_pay,
                "source": "fallback",
            }
    return data

def get_db_connection():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST)

def get_reporting_db_connection():
    return psycopg2.connect(dbname=REPORTING_DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST)

# Create the app DB if it doesn't exist
def create_database():
    conn = psycopg2.connect(dbname="postgres", user=DB_USER, password=DB_PASSWORD, host=DB_HOST)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (DB_NAME,))
    exists = cur.fetchone()
    if not exists:
        cur.execute(f"CREATE DATABASE {DB_NAME}")
    cur.close()
    conn.close()

# Make sure the entries table exists
def create_entries_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS entries (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            entry_type TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            details TEXT,
            staff_name TEXT,
            balance NUMERIC(12,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    cur.close()
    conn.close()

# Hook for future DB tweaks (left empty)
def ensure_schema_updates():
    return

# Clear the details field on all rows
def clear_details():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE entries SET details = NULL WHERE details IS NOT NULL")
    conn.commit()
    cur.close()
    conn.close()


# Website import (CSV/Excel): parse, dedupe, save, then sync to reporting
@app.route('/import_entries', methods=['POST'])
def import_entries():
    role = request.args.get('role', 'sale')
    origin = request.args.get('origin', 'http://127.0.0.1:8080')
    f = request.files.get('import_file')
    if not f or f.filename == '':
        return redirect(url_for('add_data', role=role, origin=origin))
    ext = os.path.splitext(f.filename)[1].lower()
    rows = []
    try:
        if ext == '.csv':
            import csv
            f.stream.seek(0)
            reader = csv.DictReader((line.decode('utf-8-sig') for line in f.stream))
            for row in reader:
                rows.append(row)
        elif ext in ('.xlsx', '.xls'):
            try:
                import pandas as pd
                df = pd.read_excel(f, engine='openpyxl')
            except Exception:
                import pandas as pd
                df = pd.read_excel(f)
            rows = df.to_dict(orient='records')
        else:
            return redirect(url_for('add_data', role=role, origin=origin))
    except Exception as e:
        print(f"Import read error: {e}")
        return redirect(url_for('add_data', role=role, origin=origin))
    conn = get_db_connection()
    cur = conn.cursor()
    r_conn = get_reporting_db_connection()
    r_cur = r_conn.cursor()
    employees_map = fetch_employees_from_reporting()
    inserted = 0
    for raw in rows:
        kv = {str(k).strip().lower(): raw[k] for k in raw.keys()}
        date_val = kv.get('date') or kv.get('pay_date')
        desc = kv.get('description') or kv.get('employee_name') or kv.get('vendor')
        category = kv.get('category')
        amt = kv.get('amount') if kv.get('amount') not in (None, '') else kv.get('balance')
        try:
            amount = float(amt) if amt not in (None, '') else 0
        except Exception:
            try:
                amount = float(str(amt).replace(',', ''))
            except Exception:
                amount = 0
        t = (kv.get('type') or kv.get('entry_type') or '').strip().lower()
        if t in ('credit', 'income'):
            entry_type = 'income'
        elif t in ('debit', 'expense'):
            entry_type = 'expense'
        else:
            entry_type = 'income' if amount >= 0 else 'expense'
        if date_val and category and desc:
            cur.execute(
                """
                SELECT 1 FROM entries
                WHERE date = %s AND category = %s AND description = %s AND entry_type = %s AND balance = %s
                """,
                (date_val, category, desc, entry_type, amount),
            )
            exists = cur.fetchone()
            if exists:
                continue
            cur.execute(
                """
                INSERT INTO entries (date, entry_type, category, description, balance)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (date_val, entry_type, category, desc, amount),
            )
            inserted += 1
            if (category or '').strip().lower() in ('payroll', 'payroll/labor'):
                try:
                    employee_name = desc
                    info = employees_map.get(employee_name.strip()) if employee_name else None
                    if info:
                        employee_id = info["employee_id"]
                        employee_role = info["role"]
                    else:
                        employee_id = "UNKNOWN"
                        employee_role = None
                    net_pay = float(amount)
                    r_cur.execute(
                        """
                        INSERT INTO payroll_history (employee_id, employee_name, role, pay_date, net_pay)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (employee_id, employee_name, employee_role, date_val, net_pay)
                    )
                except Exception as e:
                    print(f"Sync payroll failed: {e}")
            else:
                db_type_val = 'Credit' if entry_type == 'income' else 'Debit'
                tx_id = f"TX-{uuid.uuid4().hex[:8].upper()}"
                try:
                    r_cur.execute(
                        """
                        SELECT 1 FROM checking_account_main
                        WHERE date = %s AND category = %s AND description = %s AND type = %s AND amount = %s
                        """,
                        (date_val, category, desc, db_type_val, amount)
                    )
                    r_exists = r_cur.fetchone()
                    if not r_exists:
                        r_cur.execute(
                            """
                            INSERT INTO checking_account_main (date, transaction_id, description, category, type, amount, balance)
                            VALUES (%s, %s, %s, %s, %s, %s, 0)
                            """,
                            (date_val, tx_id, desc, category, db_type_val, amount)
                        )
                except Exception as e:
                    print(f"Sync checking failed: {e}")
    conn.commit()
    r_conn.commit()
    cur.close()
    r_cur.close()
    conn.close()
    r_conn.close()
    print(f"Imported {inserted} entries from file: {f.filename}")
    return redirect(url_for('add_data', role=role, origin=origin))

@app.route('/add_employee', methods=['POST'])
def add_employee():
    role = request.form.get('role', 'admin')
    origin = request.form.get('origin', 'http://127.0.0.1:8080')
    name = (request.form.get('employee_name') or '').strip()
    employee_role = (request.form.get('employee_role') or '').strip()
    base_raw = request.form.get('base_pay')
    try:
        base_pay = float(base_raw) if base_raw not in (None, '') else 0.0
    except Exception:
        try:
            base_pay = float(str(base_raw).replace(',', ''))
        except Exception:
            base_pay = 0.0
    if not name or not employee_role or base_pay <= 0:
        flash("Enter employee name, role and base pay.")
        return redirect(url_for('add_data', role=role, origin=origin, view='payroll'))
    try:
        conn = get_reporting_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS employees_static (
                employee_id TEXT PRIMARY KEY,
                employee_name TEXT NOT NULL,
                role TEXT,
                base_pay NUMERIC(10,2) NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS employees_inactive (
                employee_id TEXT,
                employee_name TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            DELETE FROM employees_inactive
            WHERE employee_name = %s
            """,
            (name,),
        )
        emp_id = f"E{uuid.uuid4().hex[:5].upper()}"
        cur.execute(
            """
            INSERT INTO employees_static (employee_id, employee_name, role, base_pay)
            VALUES (%s, %s, %s, %s)
            """,
            (emp_id, name, employee_role, base_pay),
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Employee added.")
    except Exception as e:
        print(f"Error adding employee: {e}")
        flash("Could not add employee.")
    return redirect(url_for('add_data', role=role, origin=origin, view='payroll'))

@app.route('/delete_employee', methods=['POST'])
def delete_employee():
    role = request.form.get('role', 'admin')
    origin = request.form.get('origin', 'http://127.0.0.1:8080')
    emp_id = request.form.get('employee_id')
    emp_name = request.form.get('employee_name')
    if not emp_id:
        flash("Missing employee id.")
        return redirect(url_for('add_data', role=role, origin=origin, view='payroll'))
    try:
        conn = get_reporting_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM employees_static
            WHERE employee_id = %s
            """,
            (emp_id,),
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS employees_inactive (
                employee_id TEXT,
                employee_name TEXT NOT NULL
            )
            """
        )
        if emp_name:
            cur.execute(
                """
                SELECT 1 FROM employees_inactive
                WHERE employee_id = %s OR employee_name = %s
                """,
                (emp_id, emp_name),
            )
            exists = cur.fetchone()
            if not exists:
                cur.execute(
                    """
                    INSERT INTO employees_inactive (employee_id, employee_name)
                    VALUES (%s, %s)
                    """,
                    (emp_id, emp_name),
                )
        conn.commit()
        cur.close()
        conn.close()
        flash("Employee removed.")
    except Exception as e:
        print(f"Error deleting employee: {e}")
        flash("Could not remove employee.")
    return redirect(url_for('add_data', role=role, origin=origin, view='payroll'))

# Manage Cash Entry
# POST: add one entry, then sync to reporting
# GET: list with filters and totals
@app.route('/', methods=('GET', 'POST'))
def add_data():
    role = request.args.get('role', 'sale')
    origin = request.args.get('origin', 'http://127.0.0.1:8080')
    view = request.args.get('view', 'daily')
    if request.method == 'POST':
        date_entry = request.form['date']
        view = request.form.get('view', view)
        entry_type = request.form['entry_type']
        category = request.form['category']
        description = request.form.get('description') or ''
        details = request.form.get('details') or None
        employee_id = None
        employee_id = None
        employee_name = None
        employee_role = None
        bonus_amount = 0.0
        raw_balance = request.form.get('balance')
        date_for_check = None
        try:
            date_for_check = datetime.strptime(str(date_entry), "%Y-%m-%d").date()
        except Exception:
            date_for_check = None
        if category == 'Payroll':
            employee_id = request.form.get('employee_id') or None
            employee_name = request.form.get('employee_name') or description
            employee_role = request.form.get('employee_role') or None
            base_raw = request.form.get('base_pay')
            bonus_raw = request.form.get('bonus')
            try:
                base_pay = float(base_raw) if base_raw not in (None, '') else 0.0
            except Exception:
                try:
                    base_pay = float(str(base_raw).replace(',', ''))
                except Exception:
                    base_pay = 0.0
            try:
                bonus_amount = float(bonus_raw) if bonus_raw not in (None, '') else 0.0
            except Exception:
                try:
                    bonus_amount = float(str(bonus_raw).replace(',', ''))
                except Exception:
                    bonus_amount = 0.0
            if bonus_amount < 0:
                bonus_amount = 0.0
            # Backend check: Bonus cannot exceed realistic limit (15% of base pay)
            max_bonus = base_pay * PAYROLL_BONUS_MAX_RATIO
            if bonus_amount > max_bonus:
                bonus_amount = max_bonus
            if base_pay <= 0:
                flash("Select a valid employee with base pay before recording payroll.")
                return redirect(url_for('add_data', role=role, origin=origin, view='payroll'))
            if employee_id and date_for_check:
                try:
                    r_conn = get_reporting_db_connection()
                    r_cur = r_conn.cursor()
                    r_cur.execute(
                        """
                        SELECT 1
                        FROM payroll_history
                        WHERE employee_id = %s
                          AND DATE_TRUNC('month', pay_date) = DATE_TRUNC('month', %s::date)
                        LIMIT 1
                        """,
                        (employee_id, date_for_check),
                    )
                    exists = r_cur.fetchone()
                    r_cur.close()
                    r_conn.close()
                    if exists:
                        flash("Payroll for this employee is already recorded for this month.")
                        return redirect(url_for('add_data', role=role, origin=origin, view='payroll'))
                except Exception as e:
                    print(f"Error checking monthly payroll limit: {e}")
            net_pay = base_pay + bonus_amount
            raw_balance = str(net_pay)
            description = employee_name or description
        try:
            balance = float(raw_balance) if raw_balance not in (None, '') else 0.0
        except Exception:
            try:
                balance = float(str(raw_balance).replace(',', ''))
            except Exception:
                balance = 0.0
        staff_name = request.form['staff_name']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO entries (date, entry_type, category, description, details, staff_name, balance)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (date_entry, entry_type, category, description, details, staff_name, balance),
        )
        conn.commit()
        cur.close()
        conn.close()

        if category == 'Payroll':
            try:
                r_conn = get_reporting_db_connection()
                r_cur = r_conn.cursor()
                employees_map = fetch_employees_from_reporting()
                if not employee_id and description:
                    info = employees_map.get(description.strip())
                    if info:
                        employee_id = info["employee_id"]
                        if not employee_role:
                            employee_role = info["role"]
                if not employee_name:
                    employee_name = description
                if not employee_id:
                    employee_id = "UNKNOWN"
                r_cur.execute(
                    """
                    INSERT INTO payroll_history (employee_id, employee_name, role, pay_date, net_pay)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (employee_id, employee_name, employee_role, date_entry, balance)
                )
                r_conn.commit()
                r_cur.close()
                r_conn.close()
            except Exception as e:
                print(f"Error syncing payroll: {e}")
        else:
            # --- SYNC OTHER ENTRIES TO REPORTING DB (checking_account_main) ---
            try:
                r_conn = get_reporting_db_connection()
                r_cur = r_conn.cursor()
                
                # Map fields
                # entry_type 'income' -> 'Credit', 'expense' -> 'Debit'
                db_type = 'Credit' if entry_type == 'income' else 'Debit'
                
                # Generate a transaction ID
                tx_id = f"TX-{uuid.uuid4().hex[:8].upper()}"
                
                # Insert into checking_account_main
                r_cur.execute(
                    """
                    INSERT INTO checking_account_main (date, transaction_id, description, category, type, amount, balance)
                    VALUES (%s, %s, %s, %s, %s, %s, 0)
                    """,
                    (date_entry, tx_id, description, category, db_type, balance)
                )
                r_conn.commit()
                r_cur.close()
                r_conn.close()
            except Exception as e:
                print(f"Error syncing to checking_account_main: {e}")
        # ------------------------------------

        return redirect(url_for('add_data', role=role, origin=origin, view=view))
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # GET: apply month/year filters and fetch rows
    month = request.args.get('month')
    year = request.args.get('year')
    where = []
    params = []
    if year:
        where.append("EXTRACT(YEAR FROM date) = %s")
        params.append(int(year))
    if month:
        where.append("EXTRACT(MONTH FROM date) = %s")
        params.append(int(month))
    sql = "SELECT id, date, entry_type, category, description, details, staff_name, COALESCE(balance, 0) AS balance, created_at FROM entries"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY date DESC, id DESC"
    cur.execute(sql, params)
    rows = cur.fetchall()

    if role != 'admin':
        rows = [r for r in rows if r['category'] != 'Payroll']

    payroll_rows = []
    if role == 'admin':
        try:
            r_conn = get_reporting_db_connection()
            r_cur = r_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            
            p_where = []
            p_params = []
            if year:
                p_where.append("EXTRACT(YEAR FROM pay_date) = %s")
                p_params.append(int(year))
            if month:
                p_where.append("EXTRACT(MONTH FROM pay_date) = %s")
                p_params.append(int(month))
            p_sql = "SELECT employee_id, employee_name, role, pay_date, net_pay FROM payroll_history"
            if p_where:
                p_sql += " WHERE " + " AND ".join(p_where)
            p_sql += " ORDER BY pay_date DESC, employee_id"
            r_cur.execute(p_sql, p_params)
            payroll_rows = r_cur.fetchall()
            r_cur.close()
            r_conn.close()
        except Exception as e:
            print(f"Error loading payroll history: {e}")
            payroll_rows = []

    import csv, os
    csv_path = os.path.join(os.path.dirname(__file__), "checking_account_main.csv")
    cat_map = {}
    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cat = row.get("category")
                desc = row.get("description")
                if not cat or not desc:
                    continue
                cat_map.setdefault(cat, set()).add(desc)
    except Exception:
        pass
    # Years for filters from existing entries
    cur.execute("SELECT DISTINCT EXTRACT(YEAR FROM date) AS y FROM entries")
    years_entries = {int(r[0]) for r in cur.fetchall()}
    
    # Years from payroll_history (if admin)
    years_payroll = set()
    if role == 'admin':
        try:
            r_conn = get_reporting_db_connection()
            r_cur = r_conn.cursor()
            r_cur.execute("SELECT DISTINCT EXTRACT(YEAR FROM pay_date) FROM payroll_history")
            years_payroll = {int(r[0]) for r in r_cur.fetchall()}
            r_cur.close()
            r_conn.close()
        except Exception:
            pass

    cur.close()
    conn.close()
    
    categories_map = {k: sorted(list(v)) for k, v in sorted(cat_map.items())}
    total_income = sum(float(r["balance"] or 0) for r in rows if r["entry_type"] == "income")
    total_expense = sum(float(r["balance"] or 0) for r in rows if r["entry_type"] == "expense")
    
    available_years = sorted(list(years_entries | years_payroll), reverse=True)
    
    selected_month = int(month) if month else None
    selected_year = int(year) if year else None
    employees = []
    try:
        employees_map = fetch_employees_from_reporting()
        employees = sorted(employees_map.values(), key=lambda e: e["employee_id"])
    except Exception:
        employees = []
    return render_template(
        "add_data.html",
        role=role,
        origin=origin,
        today=date.today(),
        now=datetime.now(),
        transactions=rows,
        total_income=total_income,
        total_expense=total_expense,
        categories_map=categories_map,
        available_years=available_years,
        selected_month=selected_month,
        selected_year=selected_year,
        employees=employees,
        payroll_rows=payroll_rows,
        view=view
    )

# Delete an entry (sales can delete within 72h)
# First delete in reporting DB, then in entries
@app.route('/delete_entry/<string:id>', methods=['POST'])
def delete_entry(id):
    role = request.args.get('role', 'sale')
    origin = request.args.get('origin', 'http://127.0.0.1:8080')
    view = request.form.get('view', 'daily')
    
    # Handle Payroll History Deletion (id is employee_id string)
    if request.form.get('is_payroll') == 'true':
        if role != 'admin':
            return "Error: Only admin can delete payroll entries.", 403
            
        try:
            pay_date = request.form.get('date')
            employee_name = request.form.get('employee_name')
            net_pay = float(request.form.get('net_pay'))
            
            r_conn = get_reporting_db_connection()
            r_cur = r_conn.cursor()
            
            # Delete from payroll_history
            r_cur.execute(
                """
                DELETE FROM payroll_history
                WHERE pay_date = %s
                  AND employee_name = %s
                  AND net_pay = %s
                  AND ctid IN (
                      SELECT ctid FROM payroll_history
                      WHERE pay_date = %s
                        AND employee_name = %s
                        AND net_pay = %s
                      LIMIT 1
                  )
                """,
                (pay_date, employee_name, net_pay, pay_date, employee_name, net_pay)
            )
            
            # Also try to delete corresponding entry in 'entries' table if it exists
            # This keeps both DBs in sync
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """
                DELETE FROM entries
                WHERE category = 'Payroll'
                  AND date = %s
                  AND description = %s
                  AND balance = %s
                  AND ctid IN (
                      SELECT ctid FROM entries
                      WHERE category = 'Payroll'
                        AND date = %s
                        AND description = %s
                        AND balance = %s
                      LIMIT 1
                  )
                """,
                (pay_date, employee_name, net_pay, pay_date, employee_name, net_pay)
            )
            conn.commit()
            cur.close()
            conn.close()
            
            r_conn.commit()
            r_cur.close()
            r_conn.close()
            
            return redirect(url_for('add_data', role=role, origin=origin, view='payroll'))
            
        except Exception as e:
            print(f"Error deleting payroll entry: {e}")
            return f"Error deleting payroll entry: {e}", 500

    # Handle Normal Entry Deletion (id is integer)
    try:
        entry_id = int(id)
    except ValueError:
        return "Invalid entry ID", 400

    conn = get_db_connection()
    cur = conn.cursor()
    
    if role == 'sale':
        cur.execute("SELECT created_at FROM entries WHERE id = %s", (entry_id,))
        result = cur.fetchone()
        if result:
            created_at = result[0]
            if created_at and (datetime.now() - created_at > timedelta(hours=72)):
                conn.close()
                return "Error: Sales users can only delete entries within 72 hours.", 403
    
    # --- SYNC DELETION TO REPORTING DB ---
    try:
        cur.execute("SELECT date, entry_type, category, description, balance FROM entries WHERE id = %s", (entry_id,))
        entry_to_delete = cur.fetchone()
        if entry_to_delete:
            d_date, d_type, d_cat, d_desc, d_bal = entry_to_delete
            
            r_conn = get_reporting_db_connection()
            r_cur = r_conn.cursor()
            
            if d_cat == 'Payroll':
                # Existing logic for deleting payroll from entries table
                r_cur.execute(
                    """
                    DELETE FROM payroll_history
                    WHERE pay_date = %s
                      AND employee_name = %s
                      AND net_pay = %s
                      AND ctid IN (
                          SELECT ctid FROM payroll_history
                          WHERE pay_date = %s
                            AND employee_name = %s
                            AND net_pay = %s
                          LIMIT 1
                      )
                    """,
                    (d_date, d_desc, d_bal, d_date, d_desc, d_bal)
                )
            else:
                db_type_val = 'Credit' if d_type == 'income' else 'Debit'
                r_cur.execute(
                    """
                    DELETE FROM checking_account_main
                    WHERE date = %s
                      AND category = %s
                      AND description = %s
                      AND type = %s
                      AND amount = %s
                      AND ctid IN (
                          SELECT ctid FROM checking_account_main
                          WHERE date = %s
                            AND category = %s
                            AND description = %s
                            AND type = %s
                            AND amount = %s
                          LIMIT 1
                      )
                    """,
                    (d_date, d_cat, d_desc, db_type_val, d_bal, d_date, d_cat, d_desc, db_type_val, d_bal)
                )
            r_conn.commit()
            r_cur.close()
            r_conn.close()
    except Exception as e:
        print(f"Error syncing deletion: {e}")
    # -------------------------------------

    cur.execute("DELETE FROM entries WHERE id = %s", (entry_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('add_data', role=role, origin=origin))

if __name__ == '__main__':
    # Command-line helpers; without flags we start the dev server
    parser = argparse.ArgumentParser()
    parser.add_argument('--init-db', action='store_true')
    parser.add_argument('--clear-details', action='store_true')

    args = parser.parse_args()
    if args.init_db:
        create_database()
        create_entries_table()
        sys.exit(0)
    if args.clear_details:
        clear_details()
        sys.exit(0)
   
    ensure_schema_updates()
    app.run(debug=True, port=5003)
