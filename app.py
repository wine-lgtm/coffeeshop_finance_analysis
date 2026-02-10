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
DB_PASSWORD = "Prim#2504"
DB_HOST = "localhost"

def get_db_connection():
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST)

def get_reporting_db_connection():
    return psycopg2.connect(dbname=REPORTING_DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST)

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

def ensure_schema_updates():
    return
def clear_details():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE entries SET details = NULL WHERE details IS NOT NULL")
    conn.commit()
    cur.close()
    conn.close()

def purge_imported_checking_entries():
    import csv, os
    conn = get_db_connection()
    cur = conn.cursor()
    csv_path = os.path.join(os.path.dirname(__file__), "checking_account_main.csv")
    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date_str = row.get("date")
                description = row.get("description")
                category = row.get("category")
                t = (row.get("type") or "").lower()
                entry_type = "income" if t == "credit" else "expense"
                balance = row.get("balance")
                balance_val = float(balance) if balance not in (None, "") else None
                if date_str and description and category and balance_val is not None:
                 #   cur.execute(
                        """
                        DELETE FROM entries
                        WHERE date = %s
                          AND category = %s
                          AND description = %s
                          AND entry_type = %s
                          AND balance = %s
                          AND COALESCE(details,'') = ''
                          AND COALESCE(staff_name,'') = ''
                        """,
                        (date_str, category, description, entry_type, balance_val),
                  #  )
        conn.commit()
    except Exception:
        pass
    finally:
        cur.close()
        conn.close()
def reset_entries_from_dataset():
    import csv, os
    conn = get_db_connection()
    cur = conn.cursor()
   # cur.execute("DELETE FROM entries")
    csv_path = os.path.join(os.path.dirname(__file__), "checking_account_main.csv")
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = row["date"]
            description = row["description"]
            category = row["category"]
            t = (row["type"] or "").lower()
            entry_type = "income" if t == "credit" else "expense"
            balance = float(row["balance"] or 0)
            cur.execute(
                """
                INSERT INTO entries (date, entry_type, category, description, balance)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (date_str, entry_type, category, description, balance),
            )
    conn.commit()
    cur.close()
    conn.close()
def seed_entries_from_reporting():
    r_conn = get_reporting_db_connection()
    conn = get_db_connection()
    r_cur = r_conn.cursor()
    cur = conn.cursor()
    r_cur.execute("SELECT date, description, category, type, balance FROM checking_account_main")
    rows = r_cur.fetchall()
    for d, desc, cat, typ, amt in rows:
        t = (typ or "").lower()
        entry_type = "income" if t == "credit" else "expense"
        balance = float(amt or 0)
        cur.execute(
            """
            SELECT 1 FROM entries
            WHERE date = %s AND category = %s AND description = %s AND entry_type = %s AND balance = %s
            """,
            (d, cat, desc, entry_type, balance),
        )
        exists = cur.fetchone()
        if not exists:
            cur.execute(
                """
                INSERT INTO entries (date, entry_type, category, description, balance)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (d, entry_type, cat, desc, balance),
            )
    conn.commit()
    r_cur.close()
    cur.close()
    r_conn.close()
    conn.close()
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
                    r_cur.execute(
                        """
                        INSERT INTO payroll_history (employee_name, pay_date, total_business_cost, role)
                        VALUES (%s, %s, %s, 'Employee')
                        """,
                        (desc, date_val, amount)
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
@app.route('/', methods=('GET', 'POST'))
def add_data():
    role = request.args.get('role', 'sale')
    origin = request.args.get('origin', 'http://127.0.0.1:8080')
    if request.method == 'POST':
        # Preserve role and origin in redirect
        origin = request.form.get('origin', origin)
        
        date_entry = request.form['date']
        entry_type = request.form['entry_type']
        category = request.form['category']
        description = request.form['description']
        details = request.form.get('details') or None
        balance = request.form['balance']
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

        # --- SYNC PAYROLL TO REPORTING DB ---
        if category == 'Payroll':
            try:
                r_conn = get_reporting_db_connection()
                r_cur = r_conn.cursor()
                # Insert into payroll_history. 
                # Mapping: 
                # description -> employee_name
                # date_entry -> pay_date
                # balance -> total_business_cost
                # We also populate gross_pay/net_pay with the same amount or NULL as we don't have breakdown
                # But main.py uses total_business_cost for reports.
                r_cur.execute(
                    """
                    INSERT INTO payroll_history (employee_name, pay_date, total_business_cost, role)
                    VALUES (%s, %s, %s, 'Employee')
                    """,
                    (description, date_entry, balance)
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

        return redirect(url_for('add_data', role=role, origin=origin))
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
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
    sql = "SELECT id, date, entry_type, category, description, details, staff_name, balance, created_at FROM entries"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY date DESC, id DESC"
    cur.execute(sql, params)
    rows = cur.fetchall()

    # Filter out Payroll entries for non-admin users (Sales Person)
    if role != 'admin':
        rows = [r for r in rows if r['category'] != 'Payroll']

    # Build description options per category from checking_account_main.csv dataset
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
    cur.execute("SELECT DISTINCT EXTRACT(YEAR FROM date) AS y FROM entries ORDER BY y DESC")
    years_rows = cur.fetchall()
    cur.close()
    conn.close()
    categories_map = {k: sorted(list(v)) for k, v in cat_map.items()}
    total_income = sum(float(r["balance"]) for r in rows if r["entry_type"] == "income")
    total_expense = sum(float(r["balance"]) for r in rows if r["entry_type"] == "expense")
    available_years = [int(r["y"]) if isinstance(r, dict) else int(r[0]) for r in years_rows]
    selected_month = int(month) if month else None
    selected_year = int(year) if year else None
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
        selected_year=selected_year
    )

@app.route('/delete_entry/<int:id>', methods=['POST'])
def delete_entry(id):
    role = request.args.get('role', 'sale')
    origin = request.args.get('origin', 'http://127.0.0.1:8080')
    conn = get_db_connection()
    cur = conn.cursor()
    
    if role == 'sale':
        cur.execute("SELECT created_at FROM entries WHERE id = %s", (id,))
        result = cur.fetchone()
        if result:
            created_at = result[0]
            if created_at and (datetime.now() - created_at > timedelta(hours=72)):
                conn.close()
                return "Error: Sales users can only delete entries within 72 hours.", 403
    
    # --- SYNC DELETION TO REPORTING DB ---
    try:
        cur.execute("SELECT date, entry_type, category, description, balance FROM entries WHERE id = %s", (id,))
        entry_to_delete = cur.fetchone()
        if entry_to_delete:
            d_date, d_type, d_cat, d_desc, d_bal = entry_to_delete
            
            r_conn = get_reporting_db_connection()
            r_cur = r_conn.cursor()
            
            if d_cat == 'Payroll':
                r_cur.execute(
                    """
                    DELETE FROM payroll_history
                    WHERE pay_date = %s
                      AND employee_name = %s
                      AND total_business_cost = %s
                      AND ctid IN (
                          SELECT ctid FROM payroll_history
                          WHERE pay_date = %s
                            AND employee_name = %s
                            AND total_business_cost = %s
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

    cur.execute("DELETE FROM entries WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('add_data', role=role, origin=origin))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--init-db', action='store_true')
    parser.add_argument('--clear-details', action='store_true')
    parser.add_argument('--reset-from-dataset', action='store_true')
    parser.add_argument('--purge-legacy', action='store_true')
    parser.add_argument('--seed-from-reporting', action='store_true')
    args = parser.parse_args()
    if args.init_db:
        create_database()
        create_entries_table()
        sys.exit(0)
    if args.clear_details:
        clear_details()
        sys.exit(0)
    if args.purge_legacy:
        purge_imported_checking_entries()
        sys.exit(0)
    if args.reset_from_dataset:
        reset_entries_from_dataset()
        sys.exit(0)
    if args.seed_from_reporting:
        seed_entries_from_reporting()
        sys.exit(0)
    ensure_schema_updates()
    app.run(debug=True, port=5003)
