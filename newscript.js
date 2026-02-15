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
    document.getElementById('login-section').classList.add('hidden');
    document.getElementById('dashboard-section').classList.remove('hidden');
    document.getElementById('sidebar-nav').classList.remove('hidden');
    document.getElementById('user-display').innerText = `Logged in as ${roleName}`;
    document.getElementById('role-text').innerText = roleName;
    if(document.querySelector('.overlay')) document.querySelector('.overlay').style.display = 'none';

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
    if (linkText) linkText.innerText = isSale ? "Submit Report" : "Intelligence Report";
    
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

    if (isSale) {
        // Clear the area for sales so they see nothing if they somehow bypass the sidebar
        reportArea.innerHTML = ''; 
    } else {
        // --- ADMIN VIEW: FULL RE-INJECTION + BACKEND RE-LINK ---
        // We only inject this if it's not already there to prevent breaking active charts
        if (!document.getElementById('incomeTrendChart')) {
            reportArea.innerHTML = `
            <div class="intel-report">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
                    <h2 style="margin:0; color: #2b1d1a;">Business Intelligence Report</h2>
                    <button onclick="exportToPDF()" class="btn-action btn-save">
                        <i class="fas fa-file-pdf"></i> Export PDF
                    </button>
                </div>

                <div class="report-filters" style="display: flex; gap: 15px; align-items: flex-end; margin-bottom: 30px; background: #fdfaf9; padding: 20px; border-radius: 15px; border: 1px solid #f1ecea;">
                    <div style="width: 200px;">
                        <label style="font-size: 11px; font-weight: bold; color: #5d4037; display: block; margin-bottom: 5px;">START DATE</label>
                        <input type="date" id="report_start_date" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px;">
                    </div>
                    <div style="width: 200px;">
                        <label style="font-size: 11px; font-weight: bold; color: #5d4037; display: block; margin-bottom: 5px;">END DATE</label>
                        <input type="date" id="report_end_date" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px;">
                    </div>
                    <button onclick="generateFilteredReport()" class="btn-action btn-new" style="height: 42px; padding: 0 25px;">
                        GENERATE REPORT
                    </button>
                </div>

                <div class="kpi-container" style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 25px;">
                    <div class="card" style="padding: 12px; border-radius: 12px;">
                        <h3 style="font-size: 10px; margin-bottom: 5px;">Total Revenue</h3>
                        <div class="value" id="rev" style="font-size: 1.2rem;">$0</div>
                    </div>
                    <div class="card" style="padding: 12px; border-radius: 12px;">
                        <h3 style="font-size: 10px; margin-bottom: 5px;">Labor Cost</h3>
                        <div class="value" id="report-avg" style="color: #d32f2f; font-size: 1.2rem;">$0</div>
                    </div>
                    <div class="card" style="padding: 12px; border-radius: 12px;">
                        <h3 style="font-size: 10px; margin-bottom: 5px;">Total Expense</h3>
                        <div class="value" id="report-total-exp" style="color: #2b1d1a; font-size: 1.2rem;">$0</div>
                    </div>
                    <div class="card" style="padding: 12px; border-radius: 12px;">
                        <h3 style="font-size: 10px; margin-bottom: 5px;">Gross Profit</h3>
                        <div class="value" id="gross" style="color: #6f4e37; font-size: 1.2rem;">$0</div>
                    </div>
                    <div class="card" style="padding: 12px; border-radius: 12px;">
                        <h3 style="font-size: 10px; margin-bottom: 5px;">Net Profit</h3>
                        <div class="value" id="profit" style="color: #28a745; font-size: 1.2rem;">$0</div>
                    </div>
                </div>
                
                <div class="detail-table-section" style="margin-top: 30px; background: white; padding: 25px; border-radius: 20px; border: 1px solid #eee;">
                    <h3 style="margin-bottom: 20px; color: #2b1d1a;">Detailed Transaction History</h3>
                    <div style="max-height: 400px; overflow-y: auto; border: 1px solid #f1f1f1; border-radius: 10px;">
                        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                            <thead style="position: sticky; top: 0; background: #5d4037; color: white; z-index: 1;">
                                <tr style="border-bottom: 2px solid #eee;">
                                    <th style="padding: 12px; text-align: left;">Date</th>
                                    <th style="padding: 12px; text-align: left;">Description</th>
                                    <th style="padding: 12px; text-align: left;">Category</th>
                                    <th style="padding: 12px; text-align: right;">Amount</th>
                                </tr>
                            </thead>
                            <tbody id="detailed_logs_body"></tbody>
                        </table>
                    </div>
                </div>

                <div class="chart-container" style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-top: 30px; margin-bottom: 30px;">
                    <div class="chart-box" style="background:white; padding:15px; border-radius:15px; border: 1px solid #eee; height:320px; position: relative;">
                        <h4 style="margin:0 0 10px 0; color: #5d4037;">Income Trend</h4>
                        <div style="height: 250px; width: 100%;"><canvas id="incomeTrendChart"></canvas></div>
                    </div>
                    <div class="chart-box" style="background:white; padding:15px; border-radius:15px; border: 1px solid #eee; height:320px; position: relative;">
                        <h4 style="margin:0 0 10px 0; color: #5d4037;">Expense Mix</h4>
                        <div style="height: 250px; width: 100%;"><canvas id="expenseChart"></canvas></div>
                    </div>
                </div>

                <div class="prediction-section" style="background: #fdfaf9; padding: 25px; border-radius: 20px; border: 1px solid #f1ecea; margin-top:30px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h3 style="margin:0; color:#5d4037;"> 3-Month Financial Forecast</h3>
                        <span id="ai-confidence" style="font-size:12px; font-weight:bold; background:#fff; padding:5px 12px; border-radius:20px; color:#5d4037; border:1px solid #5d4037;">
                            Accuracy: --
                        </span>
                    </div>
                    <button onclick="runPrediction()" class="btn-action btn-save">GENERATE FORECAST</button>
                    <div id="prediction-table-container" style="display:none; margin-top:20px;">
                        <table style="width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden;">
                            <thead style="background: #5d4037; color: white;">
                                <tr>
                                    <th style="padding: 15px; text-align: left;">Month</th>
                                    <th style="padding: 15px; text-align: right;">Projected Revenue</th>
                                    <th style="padding: 15px; text-align: right;">Projected Expense</th>
                                    <th style="padding: 15px; text-align: right;">Expected Profit</th>
                                </tr>
                            </thead>
                            <tbody id="prediction-list-body"></tbody>
                        </table>
                    </div>
                </div>
            </div>`;
            
            // Re-initialize Admin backend logic
            initReportDates(); 
            if (typeof generateFilteredReport === "function") generateFilteredReport();
        }
    }
}
async function initReportDates() {
    try {
        const res = await fetch(`http://127.0.0.1:8000/api/data-bounds`);
        const bounds = await res.json();
        
        const startInput = document.getElementById('report_start_date');
        const endInput = document.getElementById('report_end_date');

        if (startInput && endInput) {
            // 1. Lock the calendars so user can't pick invalid dates
            startInput.min = bounds.min;
            startInput.max = bounds.max;
            endInput.min = bounds.min;
            endInput.max = bounds.max;

            // 2. FORCE the values to match the database range (Full History)
            startInput.value = bounds.min;
            endInput.value = bounds.max;

            console.log("Dashboard locked to DB range:", bounds.min, "to", bounds.max);
            
            // 3. Load the data immediately
            generateFilteredReport();
        }
    } catch (e) {
        console.error("Connection to Database bounds failed. Check main.py");
    }
}
// =======================
// BACKEND CONNECTIONS (No Crash)
// =======================

async function generateFilteredReport() {
    const start = document.getElementById('report_start_date').value;
    const end = document.getElementById('report_end_date').value;
    if (!start || !end) return;

    try {
        // 1. Existing KPI Fetch
        const sumRes = await fetch(`http://127.0.0.1:8000/api/financial-summary?start_date=${start}&end_date=${end}`);
        const data = await sumRes.json();

        // 2. Existing Trend Fetch
        const trendRes = await fetch(`http://127.0.0.1:8000/api/income-progress?start_date=${start}&end_date=${end}`);
        const trendData = await trendRes.json();

        // Update UI Text
        document.getElementById('rev').innerText = `$${data.summary.total_revenue.toLocaleString()}`;
        document.getElementById('profit').innerText = `$${data.summary.net_profit.toLocaleString()}`;
        document.getElementById('report-avg').innerText = `$${data.summary.exact_labor_cost.toLocaleString()}`;
        document.getElementById('gross').innerText = `$${(data.summary.total_revenue - data.breakdown.cogs).toLocaleString()}`;
        document.getElementById('report-total-exp').innerText = `$${data.summary.total_expense.toLocaleString()}`;
        // Update Charts
        updateChartsWithBackendData(trendData, data.breakdown);

        // --- THE FULL FIX: Detailed Table ---
        const logRes = await fetch(`http://127.0.0.1:8000/api/detailed-cashflow?start_date=${start}&end_date=${end}`);
        const logs = await logRes.json();
        
        const tableBody = document.getElementById('detailed_logs_body'); 
        if (tableBody) {
            tableBody.innerHTML = ''; // Reset table content

            if (logs.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding: 20px;">No records found for this period.</td></tr>';
            } else {
                logs.forEach(item => {
                    const isExpense = item.amount < 0;
                    const row = `
                        <tr>
                            <td>${item.date}</td>
                            <td>${item.description}</td>
                            <td><span class="badge-category">${item.category}</span></td>
                            <td style="color: ${isExpense ? '#ff4d4d' : '#2ecc71'}; font-weight: bold; text-align: right;">
                                ${isExpense ? '-' : ''}$${Math.abs(item.amount).toLocaleString(undefined, {minimumFractionDigits: 2})}
                            </td>
                        </tr>
                    `;
                    tableBody.insertAdjacentHTML('beforeend', row);
                });
            }
        }

    } catch (e) {
        console.error("Backend error:", e);
    }
}
async function runPrediction() {
    // Uses the end date of your generated report as the baseline
    const reportEndDate = document.getElementById('report_end_date').value; 
    const confidenceLabel = document.getElementById('ai-confidence');
    const tableContainer = document.getElementById('prediction-table-container');
    const tableBody = document.getElementById('prediction-list-body');

    if (!reportEndDate) return alert("Please generate a report first!");

    try {
        const res = await fetch(`http://127.0.0.1:8000/api/predict-finances?target_date=${reportEndDate}`);
        const data = await res.json();

        if (data.error) return alert("Engine Error: " + data.error);

        // 1. Update Accuracy Score
        confidenceLabel.innerText = `Accuracy: ${data.accuracy}`;

        // 2. Clear and Show the Table
        tableBody.innerHTML = '';
        tableContainer.style.display = 'block';

        // 3. Loop through the 3 months
        data.breakdown.forEach(m => {
            const profitColor = m.profit >= 0 ? '#2ea44f' : '#d73a49';

            const row = `
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 15px; font-weight: bold; color: #333;">${m.month}</td>
                    <td style="padding: 15px; text-align: right; color: #2ea44f; font-weight: 600;">
                        $${m.revenue.toLocaleString()}
                    </td>
                    <td style="padding: 15px; text-align: right; color: #d73a49; font-weight: 600;">
                        $${m.expense.toLocaleString()}
                    </td>
                    <td style="padding: 15px; text-align: right; font-weight: bold; color: ${profitColor};">
                        $${m.profit.toLocaleString()}
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
    // 1. INCOME TREND (Line Chart - Keep existing logic)
    const ctxLine = document.getElementById('incomeTrendChart').getContext('2d');
    if (incomeChartInstance) incomeChartInstance.destroy();
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

    // 2. EXPENSE MIX (Doughnut Chart) - THE FULL FIX
    const ctxPie = document.getElementById('expenseChart').getContext('2d');
    if (expensePieInstance) expensePieInstance.destroy();

    // MATCH THESE EXACTLY TO YOUR NEW PYTHON RETURN KEYS
    const expenseData = [
        breakdown.payroll || 0,
        breakdown.cogs || 0,
        breakdown.marketing || 0,
        breakdown.operating || 0, // Changed from breakdown['operating expense']
        breakdown.supplies || 0,
        breakdown.utilities || 0,
        breakdown.other || 0
    ];

    expensePieInstance = new Chart(ctxPie, {
        type: 'doughnut',
        data: {
            labels: ['Payroll', 'COGS', 'Marketing', 'Operating', 'Supplies', 'Utilities', 'Other'],
            datasets: [{
                data: expenseData,
                backgroundColor: [
                    '#4e73df', // Payroll (Blue)
                    '#1cc88a', // COGS (Green)
                    '#36b9cc', // Marketing (Cyan)
                    '#f6c23e', // Operating (Yellow)
                    '#e74a3b', // Supplies (Red)
                    '#858796', // Utilities (Grey)
                    '#5a5c69'  // Other (Dark Grey)
                ],
                borderWidth: 2,
                hoverOffset: 15 // Increased for better look
            }]
        },
        options: { 
            responsive: true, 
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: { boxWidth: 12, padding: 15, font: { size: 10 } }
                },
                tooltip: {
                    callbacks: {
                        label: function(tooltipItem) {
                            return ` $${tooltipItem.raw.toLocaleString()}`;
                        }
                    }
                }
            },
            cutout: '70%' 
        }
    });
}
async function updateUI() {
    // 1. Set the Date Range to match your Database 'Start'
    const today = new Date().toISOString().split('T')[0]; 
    const startDate = "2025-08-01"; // This matches your new SQL data start

    try {
        // 2. Fetch Summary (The Dashboard Cards)
        // Ensure this API endpoint in Python sums ALL tables (Checking + Credit + Payroll)
        const res = await fetch(`http://127.0.0.1:8000/api/financial-summary?start_date=${startDate}&end_date=${today}`);
        const data = await res.json();
        
        if (data.summary) {
            // Updating the Dashboard Cards to match the Report values
            const incomeCard = document.getElementById('card-income');
            const expenseCard = document.getElementById('card-total');
            const profitCard = document.getElementById('card-remaining');

            if (incomeCard) incomeCard.innerText = `$${data.summary.total_revenue.toLocaleString()}`;
            if (expenseCard) expenseCard.innerText = `$${data.summary.total_expense.toLocaleString()}`;
            if (profitCard) profitCard.innerText = `$${data.summary.net_profit.toLocaleString()}`;
        }

        // 3. Update the Transaction Table
        const logRes = await fetch(`http://127.0.0.1:8000/api/detailed-cashflow?start_date=${startDate}&end_date=${today}`);
        const logs = await logRes.json();
        
        const dashTableBody = document.getElementById('expense-rows'); 
        if (dashTableBody) {
            dashTableBody.innerHTML = ''; 
            logs.slice(0, 15).forEach(item => {
                const isExpense = item.amount < 0;
                dashTableBody.insertAdjacentHTML('beforeend', `
                    <tr>
                        <td>${item.date}</td>
                        <td>${item.description || item.vendor || 'No Description'}</td>
                        <td><span class="badge-category">${item.category}</span></td>
                        <td style="color: ${isExpense ? '#ff4d4d' : '#2ecc71'}; font-weight: bold;">
                            ${isExpense ? '-' : '+'}$${Math.abs(item.amount).toLocaleString()}
                        </td>
                    </tr>`);
            });
        }
    } catch (e) {
        console.error("Sync Error:", e);
    }
}
function showSection(id) {
    // 1. Find the target section
    const targetSection = document.getElementById(id);
    if (!targetSection) {
        console.error("Section not found:", id);
        return;
    }

    // 2. Hide ALL sections first
    document.querySelectorAll('.page-section').forEach(section => {
        section.classList.add('hidden');
        section.classList.remove('active-section');
    });

    // 3. Show the requested section
    targetSection.classList.remove('hidden');
    targetSection.classList.add('active-section');

    // 4. If going to dashboard, refresh numbers
    if (id === 'dashboard-section') {
        updateUI();
    }

    // 5. Special logic for Admin Reports
    if (id === 'report-page' && currentUserRole === 'admin') {
        // Wait a tiny bit for the HTML to exist before running chart logic
        setTimeout(() => {
            if (typeof generateFilteredReport === "function") {
                generateFilteredReport();
            }
        }, 100);
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
