# Manual Run Guide for Coffee Shop Finance Analysis

Follow these steps to run the project manually from the terminal.

## Prerequisites
- Python installed
- PostgreSQL installed at `D:\PostgerSQL`
- Terminal (PowerShell recommended)

## Step 0: Install Dependencies
If you haven't already, install the required Python packages:
```powershell
pip install -r requirements.txt
```

## Step 1: Start PostgreSQL Database
You need to start the PostgreSQL server first.
Open a terminal and run:
```powershell
& 'D:\PostgerSQL\bin\pg_ctl.exe' start -D 'D:\PostgerSQL\data' -l pg.log
```
*To stop it later, use `stop` instead of `start`.*

## Step 2: Initialize Database (First Time Only)
If this is your first time running it or you want to reset the data:
```powershell
python init_db.py
```

## Step 3: Start the Servers
You need to run 3 separate terminals for the full stack.

### Terminal 1: Financial API (FastAPI)
This handles the reports and charts.
```powershell
uvicorn main:app --reload --port 8000
```

### Terminal 2: Data Entry App (Flask)
This handles the daily entry forms.
```powershell
python app.py
```
*Note: This runs on port 5003.*

### Terminal 3: Frontend Interface
This serves the HTML files.
```powershell
python -m http.server 3000
```

## Step 4: Access the Application
Open your browser and go to:
**http://localhost:3000**

- **Login Credentials**:
  - User: `admin`
  - Password: `admin` (or Check `index.html` / `newscript.js` if changed)

## Troubleshooting
- **Port Conflicts**: If a port is in use, find the process using `netstat -ano | findstr <port>` and kill it using `taskkill /PID <pid> /F`.
- **Database Password**: The app is configured for password `Prim#2504`. If you change it in Postgres, update `app.py`, `main.py`, and `init_db.py`.
