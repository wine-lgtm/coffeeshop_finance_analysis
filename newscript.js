// DATA STORAGE
let incomeHistory = JSON.parse(localStorage.getItem('coffee_income_history')) || [];
let totalIncome = parseFloat(localStorage.getItem('coffee_income_total')) || 0;
let transactionHistory = JSON.parse(localStorage.getItem('coffee_history')) || [];
let currentUserRole = "admin";

let incomeChartInstance = null;
let expensePieInstance = null;

// =======================
// LOGIN & SYSTEM INIT
// =======================
const loginForm = document.getElementById('loginForm');
if (loginForm) {
    loginForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const email = document.getElementById('loginEmail').value;
        const pass = document.getElementById('loginPassword').value;

        if (email === "owner@coffee.com" && pass === "admin123") {
            currentUserRole = "admin";
            localStorage.setItem('coffee_user_role', 'admin');
            initSystem("Administrator");
        } else if (email === "sale@coffee.com" && pass === "sale123") {
            currentUserRole = "sale";
            localStorage.setItem('coffee_user_role', 'sale');
            initSystem("Sale Person");
        } else {
            alert("Invalid credentials!");
        }
    });
}

function initSystem(roleName) {
    // These lines often crash the login if the IDs aren't found
    document.getElementById('login-section')?.classList.add('hidden');
    document.getElementById('dashboard-section')?.classList.remove('hidden');
    document.getElementById('sidebar-nav')?.classList.remove('hidden');

    const userDisplay = document.getElementById('user-display');
    if (userDisplay) userDisplay.innerText = `Logged in as ${roleName}`;

    const roleText = document.getElementById('role-text');
    if (roleText) roleText.innerText = roleName;

    const overlay = document.querySelector('.overlay');
    if (overlay) overlay.style.display = 'none';

    setupPermissions();
    updateUI();
}
// =======================
// PERMISSIONS & UI GEN
// =======================
function setupPermissions() {
    const isSale = currentUserRole === "sale";
    
    // 1. Sidebar Control: Physically hide the Report link from Sales Person
    // This prevents them from ever clicking into the report page.
    const reportLink = document.querySelector('a[onclick*="report-page"]');
    if (reportLink) {
        reportLink.style.display = isSale ? 'none' : 'block';
    }

    // 2. Text updates for shared areas
    const linkText = document.getElementById('report-link-text');
    if (linkText) linkText.innerText = isSale ? "Submit Report" : "Financial Report";
    
    const dashTitle = document.getElementById('dash-title');
    if (dashTitle) dashTitle.innerText = isSale ? "Sales Entry Portal" : "Admin Dashboard";
    
    // 3. Hide specific admin cards on the shared dashboard
    const balanceCard = document.getElementById('balance-card');
    if (balanceCard) {
        isSale ? balanceCard.classList.add('hidden') : balanceCard.classList.remove('hidden');
    }
    
    // 4. Report Area Management
    const reportArea = document.getElementById('report-content-area');
    if (!reportArea) return;

    // --- ADMIN VIEW: FULL RE-INJECTION + BACKEND RE-LINK ---
    // Show the same detailed report UI to Sales users so their dashboard matches Admin
    // We only inject this if it's not already there to prevent breaking active charts
    if (!document.getElementById('incomeTrendChart')) {
        reportArea.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
        <h2 style="margin:0; color: #2b1d1a; font-family: 'Poppins', sans-serif; font-weight: 700;">Financial Report</h2>
        <button onclick="exportToPDF()" class="btn-action" style="background: #2b1d1a; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: bold; display: flex; align-items: center; gap: 8px;">
            <i class="fas fa-file-pdf"></i> EXPORT PDF
        </button>
    </div>

    <div class="report-filters" style="display: flex; gap: 15px; align-items: flex-end; margin-bottom: 30px; background: #f8f9fa; padding: 25px; border-radius: 15px; border: 2px solid #e9ecef;">
        <div style="flex: 1;">
            <label style="font-size: 11px; font-weight: 800; color: #5d4037; display: block; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;">Start Date</label>
            <input type="date" id="report_start_date" style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 10px; font-weight: 600;">
        </div>
        <div style="flex: 1;">
            <label style="font-size: 11px; font-weight: 800; color: #5d4037; display: block; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;">End Date</label>
            <input type="date" id="report_end_date" style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 10px; font-weight: 600;">
        </div>
        <button onclick="generateFilteredReport()" style="background: #5d4037; color: white; border: none; height: 48px; padding: 0 30px; border-radius: 10px; font-weight: bold; cursor: pointer;">
            GENERATE REPORT
        </button>
    </div>

    <div class="kpi-container" style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; margin-bottom: 25px;">
        <div class="card" style="padding: 15px; border-radius: 15px; background: #e3f2fd; border: 1px solid #bbdefb; text-align: center;">
            <h3 style="font-size: 11px; color: #1565c0; margin-bottom: 8px; text-transform: uppercase;">Total Revenue</h3>
            <div class="value" id="rev" style="font-size: 1.4rem; font-weight: 800; color: #0d47a1;">$0</div>
        </div>
        <div class="card" style="padding: 15px; border-radius: 15px; background: #ffebee; border: 1px solid #ffcdd2; text-align: center;">
            <h3 style="font-size: 11px; color: #c62828; margin-bottom: 8px; text-transform: uppercase;">Labor Cost</h3>
            <div class="value" id="report-avg" style="font-size: 1.4rem; font-weight: 800; color: #b71c1c;">$0</div>
        </div>
        <div class="card" style="padding: 15px; border-radius: 15px; background: #fff3e0; border: 1px solid #ffe0b2; text-align: center;">
            <h3 style="font-size: 11px; color: #ef6c00; margin-bottom: 8px; text-transform: uppercase;">Total Expense</h3>
            <div class="value" id="report-total-exp" style="font-size: 1.4rem; font-weight: 800; color: #e65100;">$0</div>
        </div>
        <div class="card" style="padding: 15px; border-radius: 15px; background: #efebe9; border: 1px solid #d7ccc8; text-align: center;">
            <h3 style="font-size: 11px; color: #4e342e; margin-bottom: 8px; text-transform: uppercase;">Gross Profit</h3>
            <div class="value" id="gross" style="font-size: 1.4rem; font-weight: 800; color: #3e2723;">$0</div>
        </div>
        <div class="card" style="padding: 15px; border-radius: 15px; background: #e8f5e9; border: 1px solid #c8e6c9; text-align: center;">
            <h3 style="font-size: 11px; color: #2e7d32; margin-bottom: 8px; text-transform: uppercase;">Net Profit</h3>
            <div class="value" id="profit" style="font-size: 1.4rem; font-weight: 800; color: #1b5e20;">$0</div>
        </div>
    </div>

    <div id="simple-balance-display" style="text-align: center; margin-bottom: 30px; display: none; padding: 20px; background-color: #fff9c4; border-radius: 15px; border: 2px dashed #fbc02d;">
        <p id="balance-result-sentence" style="font-size: 1.1rem; color: #5d4037; font-weight: 700; margin: 0;"></p>
        <p id="budget-sentence-text" style="font-size: 0.95rem; color: #8b572a; font-style: italic; margin-top: 8px;"></p>
    </div>

    <div class="chart-container" style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 30px;">
        <div class="chart-box" style="background:#fff; padding:20px; border-radius:20px; border: 2px solid #f1f1f1; height:350px;">
            <h4 style="margin:0 0 15px 0; color: #5d4037; font-weight: 700;">Income Trend</h4>
            <div style="height: 280px;"><canvas id="incomeTrendChart"></canvas></div>
        </div>
        <div class="chart-box" style="background:#fff; padding:20px; border-radius:20px; border: 2px solid #f1f1f1; height:350px;">
            <h4 style="margin:0 0 15px 0; color: #5d4037; font-weight: 700;">Expense Mix</h4>
            <div style="height: 280px;"><canvas id="expenseChart"></canvas></div>
        </div>
    </div>

    <div class="detail-table-section" style="background: white; padding: 25px; border-radius: 20px; border: 2px solid #f1f1f1; margin-bottom: 30px;">
        <h3 style="margin-bottom: 20px; color: #2b1d1a; font-weight: 700;">Detailed Transaction History</h3>
        <div style="max-height: 400px; overflow-y: auto; border: 1px solid #eee; border-radius: 15px;">
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <thead style="position: sticky; top: 0; background: #5d4037; z-index: 1;">
                    <tr>
                        <th style="padding: 15px; text-align: left; color: white; font-weight: 700;">Date</th>
                        <th style="padding: 15px; text-align: left; color: white; font-weight: 700;">Description</th>
                        <th style="padding: 15px; text-align: left; color: white; font-weight: 700;">Category</th>
                        <th style="padding: 15px; text-align: right; color: white; font-weight: 700;">Amount</th>
                    </tr>
                </thead>
                <tbody id="detailed_logs_body" style="color: #4e342e;"></tbody>
            </table>
        </div>
    </div>

    <div class="prediction-section" style="background: #fdfaf9; padding: 30px; border-radius: 25px; border: 2px solid #efebe9;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
            <h3 style="margin:0; color:#5d4037; font-weight: 700;">3 Months Forecast</h3>
            <span id="ai-confidence" style="font-size:12px; font-weight:900; background:#5d4037; padding:8px 15px; border-radius:30px; color:#fff;">
                ACCURACY: --
            </span>
        </div>

        <div style="display: flex; gap: 15px; align-items: center; margin-bottom: 25px;">
            <select id="scenario-selector" style="padding: 12px; border-radius: 10px; border: 2px solid #ddd; background: white; color: #5d4037; font-weight: bold; cursor: pointer; flex: 1;">
                <option value="Best Case">Best Case (Optimistic)</option>
                <option value="Average Case" selected>Average Case (Likely)</option>
                <option value="Worst Case">Worst Case (Pessimistic)</option>
            </select>
            <button onclick="runPrediction()" style="background: #2e7d32; color: white; border: none; padding: 12px 25px; border-radius: 10px; font-weight: bold; cursor: pointer;">
                GENERATE FORECAST
            </button>
        </div>

        <div id="prediction-table-container" style="display:none; margin-top:20px; border-radius: 15px; overflow: hidden; border: 1px solid #eee;">
            <table style="width: 100%; border-collapse: collapse; background: white;">
                <thead style="background: #5d4037; color: white;">
                    <tr>
                        <th style="padding: 15px; text-align: left; font-weight: 700;">Month</th>
                        <th style="padding: 15px; text-align: right; font-weight: 700;">Projected Revenue</th>
                        <th style="padding: 15px; text-align: right; font-weight: 700;">Projected Expense</th>
                        <th style="padding: 15px; text-align: right; font-weight: 700;">Expected Profit</th>
                    </tr>
                </thead>
                <tbody id="prediction-list-body" style="color: #4e342e;"></tbody>
            </table>
        </div>

        <div class="forecast-insights" style="margin-top: 30px; padding: 25px; background: #efebe9; border-left: 6px solid #5d4037; border-radius: 12px; color: #4e342e;">
            <h4 style="margin: 0 0 12px 0; color: #5d4037;"><i class="fas fa-lightbulb"></i> SYSTEM INSIGHTS</h4>
            <ul style="line-height: 1.6; font-size: 0.95rem; padding-left: 20px; margin: 0;">
                <li><strong>Statistical Reliability:</strong> This forecast utilizes a <strong>MAPE (Mean Absolute Percentage Error)</strong> back-testing to verify prediction confidence.</li>
                <li><strong>Data Sensitivity Warning:</strong> Prediction accuracy is highly dependent on recent record density. If data is sparse, accuracy percentages will drop.</li>
            </ul>
        </div>
    </div>
`;
            
        // Re-initialize backend logic for the injected report UI
        initReportDates(); 
        if (typeof generateFilteredReport === "function") generateFilteredReport();
    }
}
async function initReportDates() {
    try {
        const res = await fetch(`http://127.0.0.1:8000/api/data-bounds`);
        const bounds = await res.json();
        
        const startInput = document.getElementById('report_start_date');
        const endInput = document.getElementById('report_end_date');

        if (startInput && endInput) {
            // 1. Lock the calendars (Limits)
            // This allows the user to scroll back to August (min) but not past Today (max)
            startInput.min = bounds.min;
            startInput.max = bounds.max;
            endInput.min = bounds.min;
            endInput.max = bounds.max;

            // 2. SET CURRENT MONTH AS DEFAULT (Fixes the "August" issue)
            // Use 'default_start' (Feb 1st) instead of 'min' (August)
            startInput.value = bounds.default_start; 
            endInput.value = bounds.default_end;

            console.log("Dashboard defaulting to Current Month:", bounds.default_start, "to", bounds.default_end);
            
            // 3. Load the data immediately for February
            generateFilteredReport();
        }
    } catch (e) {
        console.error("Connection to Database bounds failed. Check main.py");
    }
}
// =======================
// BACKEND CONNECTIONS (No Crash)
async function generateFilteredReport() {
    let startInput = document.getElementById('report_start_date');
    let endInput = document.getElementById('report_end_date');

    if (!startInput || !endInput) return;

    // Handle initial date setting
    if (!startInput.value || !endInput.value) {
        const now = new Date();
        const y = now.getFullYear();
        const m = String(now.getMonth() + 1).padStart(2, '0');
        const d = String(now.getDate()).padStart(2, '0');
        startInput.value = `${y}-${m}-01`; 
        endInput.value = `${y}-${m}-${d}`;   
    }

    const start = startInput.value;
    const end = endInput.value;

    try {
        const [sumRes, trendRes, logRes] = await Promise.all([
            fetch(`http://127.0.0.1:8000/api/financial-summary?start_date=${start}&end_date=${end}`),
            fetch(`http://127.0.0.1:8000/api/income-progress?start_date=${start}&end_date=${end}`),
            fetch(`http://127.0.0.1:8000/api/detailed-cashflow?start_date=${start}&end_date=${end}`)
        ]);

        const data = await sumRes.json();
        const trendData = await trendRes.json();
        const logs = await logRes.json();

        const updateElement = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.innerText = value;
        };

        if (data.summary) {
            // Standard KPIs
            updateElement('rev', `$${(data.summary.total_revenue || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`);
            updateElement('profit', `$${(data.summary.net_profit || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`);
            updateElement('gross', `$${(data.summary.gross_profit || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`);
            updateElement('report-total-exp', `$${(data.summary.total_expense || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`);
            
            // FIXED: Labor Cost Label
            updateElement('report-avg', `$${(data.summary.exact_labor_cost || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`);
            
            // Balance KPIs
            updateElement('start-bal', `$${(data.summary.starting_balance || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`);
            updateElement('end-bal', `$${(data.summary.ending_balance || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`);
            
            const displayDiv = document.getElementById('simple-balance-display');
            if (displayDiv) {
                updateElement('balance-result-sentence', data.summary.status_message || "");
                updateElement('budget-sentence-text', data.summary.budget_message || "");
                displayDiv.style.display = 'block';
            }

            // Also update the top dashboard KPI cards so Sales and Admin match
            const topIncome = document.getElementById('card-income');
            const topTotal = document.getElementById('card-total');
            const topRemaining = document.getElementById('card-remaining');
            if (topIncome) topIncome.innerText = `$${(data.summary.total_revenue || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
            if (topTotal) topTotal.innerText = `$${(data.summary.total_expense || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
            if (topRemaining) {
                const finalBal = data.summary.ending_balance || 0;
                topRemaining.innerText = `$${finalBal.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
                topRemaining.style.color = finalBal < 0 ? '#ff4d4d' : '';
            }
        }

        if (typeof updateChartsWithBackendData === 'function') {
            updateChartsWithBackendData(trendData, data.breakdown || {});
        }

        // Detailed Logs Table logic stays the same...
        const tableBody = document.getElementById('detailed_logs_body'); 
        if (tableBody) {
            tableBody.innerHTML = '';
            logs.forEach(item => {
                const isInflow = ['SALES REVENUE', 'OWNER EQUITY'].includes(item.category?.toUpperCase());
                const isDraw = item.description === 'Owner Draw-out';
                const color = (isInflow && !isDraw) ? '#2ecc71' : '#ff4d4d';

                tableBody.insertAdjacentHTML('beforeend', `
                    <tr>
                        <td>${item.date}</td>
                        <td>${item.description || item.vendor}</td>
                        <td><span class="badge-category">${item.category}</span></td>
                        <td style="color: ${color}; font-weight: bold; text-align: right;">
                            ${isInflow && !isDraw ? '' : '-'}$${Math.abs(item.amount).toLocaleString(undefined, {minimumFractionDigits: 2})}
                        </td>
                    </tr>`);
            });
        }
    } catch (e) {
        console.error("Dashboard Error:", e);
    }
}
async function runPrediction() {
    // 1. Get the baseline date AND the selected scenario from the dropdown
    const reportEndDate = document.getElementById('report_end_date').value; 
    const scenarioChoice = document.getElementById('scenario-selector').value; // Added this
    const confidenceLabel = document.getElementById('ai-confidence');
    const tableContainer = document.getElementById('prediction-table-container');
    const tableBody = document.getElementById('prediction-list-body');

    if (!reportEndDate) return alert("Please generate a report first!");

    try {
        const res = await fetch(`http://127.0.0.1:8000/api/predict-finances?target_date=${reportEndDate}`);
        const data = await res.json();

        if (data.error) return alert("Engine Error: " + data.error);

        // Update Accuracy Score
        confidenceLabel.innerText = `Accuracy: ${data.accuracy}`;

        // Clear and Show the Table
        tableBody.innerHTML = '';
        tableContainer.style.display = 'block';

        // 2. Select the specific scenario data based on the dropdown choice
        // Instead of 'data.breakdown', we use 'data.scenarios[scenarioChoice]'
        const selectedData = data.scenarios[scenarioChoice]; 

        // 3. Loop through the selected scenario's 3 months
        selectedData.forEach(m => {
            const profitColor = m.profit >= 0 ? '#2ea44f' : '#d73a49';

            const row = `
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 15px; font-weight: bold; color: #333;">${m.month}</td>
                    <td style="padding: 15px; text-align: right; color: #2ea44f; font-weight: 600;">
                        $${m.revenue.toLocaleString(undefined, {minimumFractionDigits: 2})}
                    </td>
                    <td style="padding: 15px; text-align: right; color: #d73a49; font-weight: 600;">
                        $${m.expense.toLocaleString(undefined, {minimumFractionDigits: 2})}
                    </td>
                    <td style="padding: 15px; text-align: right; font-weight: bold; color: ${profitColor};">
                        $${m.profit.toLocaleString(undefined, {minimumFractionDigits: 2})}
                    </td>
                </tr>
            `;
            tableBody.insertAdjacentHTML('beforeend', row);
        });

    } catch (e) {
        console.error("Connection Error:", e);
        alert("Prediction Engine is offline.");
    }
}

function exportToPDF() {
    const start = document.getElementById('report_start_date').value;
    const end = document.getElementById('report_end_date').value;

    if (!start || !end) return alert("Please select dates!");

    // This "jumps" to the backend URL, which triggers the download
    window.location.href = `http://127.0.0.1:8000/api/download-pdf?start_date=${start}&end_date=${end}`;
}

// =======================
// CHART & UI LOGIC
// =======================
function updateChartsWithBackendData(trendData, breakdown) {
    // SAFETY CHECK: Prevents login crashes
    if (!breakdown || !trendData) return;

    // 1. INCOME TREND
    const lineEl = document.getElementById('incomeTrendChart');
    if (lineEl) {
        const ctxLine = lineEl.getContext('2d');
        if (typeof incomeChartInstance !== 'undefined' && incomeChartInstance) incomeChartInstance.destroy();
        incomeChartInstance = new Chart(ctxLine, {
            type: 'line',
            data: {
                labels: trendData.map(d => d.date),
                datasets: [{
                    label: 'Daily Revenue',
                    data: trendData.map(d => d.revenue),
                    borderColor: '#4e73df',
                    backgroundColor: 'rgba(78, 115, 223, 0.1)',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
    }

    // 2. EXPENSE MIX (Doughnut) - DYNAMIC DESCRIPTION FIX
  const pieEl = document.getElementById('expenseChart');
    if (pieEl) {
        const ctxPie = pieEl.getContext('2d');
        if (typeof expensePieInstance !== 'undefined' && expensePieInstance) expensePieInstance.destroy();

        // Filter out the "math" keys so they don't show in the legend
const summaryKeys = ['cogs', 'payroll', 'operating'];

const labels = Object.keys(breakdown).filter(key => !summaryKeys.includes(key));
const dataValues = labels.map(key => breakdown[key]);

        expensePieInstance = new Chart(ctxPie, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: dataValues,
                    backgroundColor: ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', '#858796', '#5a5c69', '#f39c12', '#d35400'],
                    borderWidth: 2,
                    hoverOffset: 15 
                }]
            },
             options: { 
                responsive: true, 
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 10 } } },
                    tooltip: {
                        callbacks: {
                            label: (item) => `${item.label}: $${item.raw.toLocaleString()}${item.label}: $${item.raw.toLocaleString()}`
                        }
                    }
                },
                cutout: '70%' 
            }
        });
    }
}
async function updateUI() {
    // 1. DYNAMIC DATE RANGE: default = Start of current month to Today
    // If admin: force the dashboard to show February of the current year only
    const now = new Date();
    const year = now.getFullYear();
    const febStart = `${year}-02-01`;
    const febLastDay = new Date(year, 2, 0).getDate();
    const febEnd = `${year}-02-${String(febLastDay).padStart(2, '0')}`;

    let startDate, today;
    if (currentUserRole === 'admin') {
        startDate = febStart;
        today = febEnd;
    } else {
        startDate = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
        today = now.toISOString().split('T')[0];
    }

    try {
        // 2. Fetch from your financial-summary endpoint
        const res = await fetch(`http://127.0.0.1:8000/api/financial-summary?start_date=${startDate}&end_date=${today}`);
        const data = await res.json();
        
        if (data.summary) {
            // Target the specific IDs in your dashboard
            const incomeCard = document.getElementById('card-income');
            const expenseCard = document.getElementById('card-total');
            const balanceCard = document.getElementById('card-remaining'); // This is your "Current Balance" card

            // 3. APPLY OFFICIAL BACKEND CALCULATIONS
            // total_revenue -> Sales
            if (incomeCard) {
                incomeCard.innerText = `$${data.summary.total_revenue.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
            }
            
            // total_expense -> All categorized expenses + Payroll
            if (expenseCard) {
                expenseCard.innerText = `$${data.summary.total_expense.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
            }

            // ending_balance -> The official starting_balance + net_profit calculated in Python
            if (balanceCard) {
    const finalBal = data.summary.ending_balance;
    balanceCard.innerText = `$${finalBal.toLocaleString(undefined, {minimumFractionDigits: 2})}`;
    
    // Only change color if balance is negative (Red), otherwise let CSS handle it
    balanceCard.style.color = finalBal < 0 ? '#ff4d4d' : ''; 
}
        }

        // 4. Update the Dashboard Table
        const logRes = await fetch(`http://127.0.0.1:8000/api/detailed-cashflow?start_date=${startDate}&end_date=${today}`);
        const logs = await logRes.json();
        
        const dashTableBody = document.getElementById('expense-rows'); 
        if (dashTableBody) {
            dashTableBody.innerHTML = ''; 
            logs.forEach(item => {
                const isExpense = item.amount < 0 || (item.category && item.category.toUpperCase() !== 'SALES REVENUE');
                
                dashTableBody.insertAdjacentHTML('beforeend', `
                    <tr>
                        <td>${item.date}</td>
                        <td>${item.description || item.vendor || 'No Description'}</td>
                        <td><span class="badge-category">${item.category}</span></td>
                        <td style="color: ${isExpense ? '#ff4d4d' : '#2ecc71'}; font-weight: bold;">
                            ${isExpense ? '-' : '+'}$${Math.abs(item.amount).toLocaleString(undefined, {minimumFractionDigits: 2})}
                        </td>
                    </tr>`);
            });
        }

    } catch (e) {
        console.error("Dashboard Sync Error:", e);
    }
}

function showSection(sectionId) {
    if (!sectionId) return;

    // 1. Hide all sections first
    const sections = document.querySelectorAll('.content-section');
    sections.forEach(s => s.classList.add('hidden'));

    // 2. Show the target section
    const target = document.getElementById(sectionId);
    if (target) {
        target.classList.remove('hidden');
    }

    // 3. TRIGGER BUDGET FETCH
    if (sectionId === 'overall-budget-section') { 
        if (typeof initOverallBudgetSection === 'function') {
            initOverallBudgetSection();
        } else if (typeof loadOverallBudgets === 'function') {
            loadOverallBudgets(); // Fallback if init function isn't named exactly
        }
    }
}
// Placeholder helper functions for UI
function addNewRow() { 
    const tbody = document.getElementById('input-rows');
    const tr = document.createElement('tr');
    tr.innerHTML = `<td style="text-align:center"><input type="checkbox" class="row-checkbox"></td><td><input type="text" class="row-desc" required></td><td><select class="row-cat"><option>Supplies</option><option>Wages</option></select></td><td><input type="date" class="row-date" required></td><td><input type="text" class="row-payer"></td><td><input type="number" class="row-amt" step="0.01" required></td>`;
    tbody.appendChild(tr);
}
function deleteHistoryItem(idx) { transactionHistory.splice(idx,1); updateUI(); }
function deleteIncomeItem(idx) { incomeHistory.splice(idx,1); updateUI(); }
function submitReport() { alert("Report Sent!"); }

// =======================
// EXPENSE FUNCTIONS
// =======================
function addNewRow() {
    const tbody = document.getElementById('input-rows');
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td style="text-align:center"><input type="checkbox" class="row-checkbox"></td>
        <td><input type="text" class="row-desc" placeholder="Item Name" required></td>
        <td><select class="row-cat"><option>Supplies</option><option>Wages</option><option>Utilities</option></select></td>
        <td><input type="date" class="row-date" required></td>
        <td><input type="text" class="row-payer" placeholder="Name"></td>
        <td><input type="number" class="row-amt" placeholder="0.00" step="0.01" required></td>
    `;
    tbody.appendChild(tr);
}

function saveFromPage(event) {
    event.preventDefault();
    const rows = document.querySelectorAll('#input-rows tr');
    let count = 0;
    rows.forEach(row => {
        const desc = row.querySelector('.row-desc').value;
        const cat = row.querySelector('.row-cat').value;
        const date = row.querySelector('.row-date').value;
        const payer = row.querySelector('.row-payer').value;
        const amt = parseFloat(row.querySelector('.row-amt').value);
        if (desc && date && amt > 0) {
            transactionHistory.unshift({ desc, cat, date, payer, amt });
            count++;
        }
    });
    if (count > 0) {
        localStorage.setItem('coffee_history', JSON.stringify(transactionHistory));
        updateUI();
        alert("Expense Records Saved!");
        document.getElementById('input-rows').innerHTML = "";
    }
}

function deleteHistoryItem(index) {
    if (currentUserRole !== "admin") return alert("Only Admin can delete!");
    if (confirm("Delete this expense entry?")) {
        transactionHistory.splice(index, 1);
        localStorage.setItem('coffee_history', JSON.stringify(transactionHistory));
        updateUI();
    }
}

function deleteSelectedRows() {
    // 1. Handle Saved History (Database)
    const historyChecked = document.querySelectorAll('#history-rows-manage .row-checkbox:checked');
    if (historyChecked.length > 0 && confirm(`Delete ${historyChecked.length} saved records?`)) {
        const indexes = Array.from(historyChecked).map(cb => parseInt(cb.dataset.index));
        indexes.sort((a,b) => b-a).forEach(idx => transactionHistory.splice(idx, 1));
        localStorage.setItem('coffee_history', JSON.stringify(transactionHistory));
    }

    // 2. Handle New Input Rows (Screen UI)
    const inputChecked = document.querySelectorAll('#input-rows .row-checkbox:checked');
    inputChecked.forEach(cb => cb.closest('tr').remove());

    updateUI(); // Refresh everything
}
function toggleSelectAll(source) {
    document.querySelectorAll('#history-rows-manage .row-checkbox').forEach(cb => cb.checked = source.checked);
}

// =======================
// INCOME FUNCTIONS
// =======================
function addNewIncomeRow() {
    const tbody = document.getElementById('income-input-rows');
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td style="text-align:center"><input type="checkbox" class="income-row-checkbox"></td>
        <td><input type="text" class="income-desc" placeholder="Income Description" required></td>
        <td><select class="income-source"><option>Sales</option><option>Service</option><option>Other</option></select></td>
        <td><input type="date" class="income-date" required></td>
        <td><input type="text" class="income-receiver" placeholder="Received By"></td>
        <td><input type="number" class="income-amt" step="0.01" placeholder="0.00" required></td>
    `;
    tbody.appendChild(tr);
}

function saveIncomeFromPage(event) {
    event.preventDefault();
    const rows = document.querySelectorAll('#income-input-rows tr');
    let count = 0;
    rows.forEach(row => {
        const desc = row.querySelector('.income-desc').value;
        const source = row.querySelector('.income-source').value;
        const date = row.querySelector('.income-date').value;
        const receiver = row.querySelector('.income-receiver').value;
        const amt = parseFloat(row.querySelector('.income-amt').value);

        if (desc && date && amt > 0) {
            incomeHistory.unshift({ desc, source, date, receiver, amt });
            count++;
        }
    });

    if (count > 0) {
        localStorage.setItem('coffee_income_history', JSON.stringify(incomeHistory));
        updateUI();
        alert("Income Records Saved!");
        document.getElementById('income-input-rows').innerHTML = "";
    }
}

function deleteIncomeItem(index) {
    if (currentUserRole !== "admin") return alert("Only Admin can delete!");
    if (confirm("Delete this income entry?")) {
        incomeHistory.splice(index, 1);
        localStorage.setItem('coffee_income_history', JSON.stringify(incomeHistory));
        updateUI();
    }
}

function deleteSelectedIncomeRows() {
    // 1. Handle Saved History (Database)
    const historyChecked = document.querySelectorAll('#income-history-rows .income-row-checkbox:checked');
    if (historyChecked.length > 0 && confirm(`Delete ${historyChecked.length} saved income records?`)) {
        const indexes = Array.from(historyChecked).map(cb => parseInt(cb.dataset.index));
        indexes.sort((a,b) => b-a).forEach(idx => incomeHistory.splice(idx, 1));
        localStorage.setItem('coffee_income_history', JSON.stringify(incomeHistory));
    }

    // 2. Handle New Input Rows (Screen UI)
    const inputChecked = document.querySelectorAll('#income-input-rows .income-row-checkbox:checked');
    inputChecked.forEach(cb => cb.closest('tr').remove());

    updateUI(); // Refresh everything
}
function toggleSelectAllIncome(source) {
    document.querySelectorAll('#income-history-rows .income-row-checkbox').forEach(cb => cb.checked = source.checked);
}

// =======================
// REPORT FUNCTIONS
// =======================
function submitReport() {
    alert("SUCCESS: Today's report has been submitted to Administrator.");
    showSection('dashboard');
}

// =======================
// AUTO-LOGIN CHECK
// =======================
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('action') === 'logout') return;

    const savedRole = localStorage.getItem('coffee_user_role');
    if (savedRole) {
        currentUserRole = savedRole;
        const roleName = savedRole === 'admin' ? 'Administrator' : 'Sale Person';
        initSystem(roleName);
        
        if (window.location.hash) {
            const section = window.location.hash.substring(1);
            showSection(section);
        }
    }
});