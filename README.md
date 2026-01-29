# Coffee Shop Finance Analysis - Run Guide

This guide explains how to run the project on a new PC using **VS Code**. It covers both **Windows** and **Mac**.

## 🛠️ Prerequisites

Before you start, ensure you have the following installed:
1.  **VS Code**: [Download here](https://code.visualstudio.com/).
2.  **Python 3.x**: [Download here](https://www.python.org/downloads/).
3.  **PostgreSQL**: [Download here](https://www.postgresql.org/download/).
    *   **Important**: The project expects the PostgreSQL username to be `postgres` and the password to be `postgres`.
    *   If your password is different, you will need to update `app.py` (line 17) and `main.py` (line 24) after downloading.

---

## 🚀 Part 1: Initial Setup

### 1. Open the Project
1.  Open **VS Code**.
2.  Go to **File > Open Folder...** and select the `coffeeshop_finance_analysis` folder.

### 2. Open the Terminal
1.  In VS Code, go to **Terminal > New Terminal** (or press `` Ctrl+` `` / `` Cmd+` ``).

### 3. Install Dependencies
Run the command for your OS:

**Windows:**
```bash
python -m pip install -r requirements.txt
```

**Mac:**
```bash
python3 -m pip install -r requirements.txt
```

### 4. Setup Database
This script creates the database and imports data automatically.

**Windows:**
```bash
python init_db.py
```

**Mac:**
```bash
python3 init_db.py
```

---

## 🎓 Part 2: Teacher Demo Mode (How to Run)

You need to run **3 separate servers**. To keep your screen clean for the teacher, we will **hide** the backend server.

### Step 1: Start the "Invisible" Engine (Backend API)
This server powers the charts but **does not need to be shown**.

> **⚠️ IMPORTANT:** You **MUST** use port `8000` for this step. The code is hardcoded to look for this specific port.

1.  In the **first terminal**, run:
    *   **Windows:** `python -m uvicorn main:app --reload --port 8000`
    *   **Mac:** `python3 -m uvicorn main:app --reload --port 8000`
2.  **Hide this terminal**:
    *   Once it says "Application startup complete", you can ignore this terminal.
    *   In VS Code, you can click the `+` button to create a new terminal, leaving this one running in the background.

### Step 2: Start the "Visible" App (Data Entry)
This is the Flask app you might want to show.

1.  Open a **New Terminal** (click `+`).
2.  Run:
    *   **Windows:** `python app.py`
    *   **Mac:** `python3 app.py`

### Step 3: Start the Frontend (Website)
1.  Open another **New Terminal** (click `+`).
2.  Run:
    *   **Windows:** `python -m http.server 3000`
    *   **Mac:** `python3 -m http.server 3000`

> **Note:** We use port `3000` here, but if that port is busy on the other PC, you can change it to any number (e.g., `8080` or `5000`). The project will automatically adapt to whatever port you choose for this step.

---

## 🌐 Part 3: Show the Project
Open your web browser and go to:
👉 **http://localhost:3000/index.html**

*(If you changed the port in Step 3, use that number instead of 3000)*

You can now demonstrate:
1.  **Login** (admin/admin123).
2.  **Dashboard** (Charts will load because Step 1 is running in the background).
3.  **Data Entry** (Powered by Step 2).

---

### ❓ Troubleshooting
*   **"Command not found"?**
    *   On Windows, ensure you selected "Add Python to PATH" during installation.
    *   On Mac, always use `python3` and `pip3`.
*   **Database Error?**
    *   Make sure PostgreSQL is running.
    *   Check `app.py` line 17 to match your PC's password.
