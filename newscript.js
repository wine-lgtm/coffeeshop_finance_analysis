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
    document.getElementById('report-link-text').innerText = isSale ? "Submit Report" : "Intelligence Report";
    document.getElementById('dash-title').innerText = isSale ? "Sales Entry Portal" : "Admin Dashboard";
    
    if (document.getElementById('balance-card')) {
        isSale ? document.getElementById('balance-card').classList.add('hidden') : document.getElementById('balance-card').classList.remove('hidden');
    }
    
    const reportArea = document.getElementById('report-content-area');

    if (isSale) {
        reportArea.innerHTML = `
            <div class="intel-report">
                <h2><i class="fas fa-paper-plane"></i> Submit Daily Report</h2>
                <div class="card" style="background:#f8f9fa; margin-bottom:20px;">
                    <h3>Total Records Today</h3>
                    <div class="value" id="sale-count-view">0</div>
                </div>
                <button class="btn-action btn-save" onclick="submitReport()" style="width:100%; padding:20px;">SEND REPORT TO ADMIN</button>
            </div>`;
    } else {
        reportArea.innerHTML = `
        <div class="intel-report">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
                <h2 style="margin:0;">Business Intelligence Report</h2>
                <button onclick="exportToPDF()" style="background: #2c3e50; color: white; border:none; padding: 10px 18px; border-radius: 8px; cursor: pointer;">
                    <i class="fas fa-file-pdf"></i> Export PDF
                </button>
            </div>

            <div class="report-filters" style="display: flex; gap: 15px; align-items: flex-end; margin-bottom: 30px; background: #f8f9fa; padding: 20px; border-radius: 15px; border: 1px solid #eee;">
                <div style="width: 200px;">
                    <label style="font-size: 11px; font-weight: bold; color: #666; display: block; margin-bottom: 5px;">START DATE</label>
                    <input type="date" id="report_start_date" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px;">
                </div>
                <div style="width: 200px;">
                    <label style="font-size: 11px; font-weight: bold; color: #666; display: block; margin-bottom: 5px;">END DATE</label>
                    <input type="date" id="report_end_date" style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px;">
                </div>
                <button onclick="generateFilteredReport()" style="background: #2ea44f; color: white; border: none; padding: 0 25px; border-radius: 8px; font-weight: bold; cursor: pointer; height: 42px;">
                    GENERATE REPORT
                </button>
            </div>

            <div class="kpi-container">
                <div class="card"><h3>Total Revenue</h3><div class="value" id="rev">$0</div></div>
                <div class="card"><h3>Gross Profit</h3><div class="value" id="gross" style="color: #4e73df;">$0</div></div>
                <div class="card"><h3>Net Profit</h3><div class="value" id="profit" style="color: #2ea44f;">$0</div></div>
                <div class="card"><h3>Avg Labor Cost</h3><div class="value" id="report-avg">$0</div></div>
            </div>
            
<div class="detail-table-section" style="margin-top: 30px; background: white; padding: 25px; border-radius: 20px; border: 1px solid #eee;">
    <h3 style="margin-bottom: 20px;">Detailed Transaction History</h3>
    
    <div style="max-height: 400px; overflow-y: auto; border: 1px solid #f1f1f1; border-radius: 10px;">
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
            <thead style="position: sticky; top: 0; background: #f8f9fa; z-index: 1;">
                <tr style="border-bottom: 2px solid #eee;">
                    <th style="padding: 12px; text-align: left;">Date</th>
                    <th style="padding: 12px; text-align: left;">Description</th>
                    <th style="padding: 12px; text-align: left;">Category</th>
                    <th style="padding: 12px; text-align: right;">Amount</th>
                </tr>
            </thead>
            <tbody id="detailed_logs_body">
                </tbody>
        </table>
    </div>
</div>
            <div class="chart-container" style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 30px;">
    <div class="chart-box" style="background:white; padding:15px; border-radius:15px; border: 1px solid #eee; height:320px; position: relative;">
        <h4 style="margin:0 0 10px 0;">Income Trend</h4>
        <div style="height: 250px; width: 100%;">
            <canvas id="incomeTrendChart"></canvas>
        </div>
    </div>
    <div class="chart-box" style="background:white; padding:15px; border-radius:15px; border: 1px solid #eee; height:320px; position: relative;">
        <h4 style="margin:0 0 10px 0;">Expense Mix</h4>
        <div style="height: 250px; width: 100%;">
            <canvas id="expenseChart"></canvas>
        </div>
    </div>
</div>

            <div class="prediction-section" style="background: #ebf5ff; padding: 25px; border-radius: 20px; border: 1px solid #cfe2ff;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3 style="margin:0; color:#01579b;">Financial Forecasting</h3>
                    <span id="ai-confidence" style="font-size:12px; font-weight:bold; color:#007bff;"></span>
                </div>
                
                <div style="display: flex; gap: 15px; align-items: center; margin-bottom: 20px;">
                    <input type="month" id="prediction_month" style="padding: 10px; border: 1px solid #ddd; border-radius: 8px; width: 200px;">
                    <button onclick="runPrediction()" style="background: #007bff; color:white; border:none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor:pointer;">RUN ANALYSIS</button>
                </div>

                <div id="predictionSummary" style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom:20px;">
                    <div class="card"><h3>Expected Revenue</h3><div class="value" id="f_inc" style="font-size: 1.2rem;">$0</div></div>
                    <div class="card"><h3>Expected Expense</h3><div class="value" id="f_exp" style="font-size: 1.2rem; color: #d73a49;">$0</div></div>
                    <div class="card"><h3>Predicted Profit</h3><div class="value" id="f_prof" style="font-size: 1.2rem; color: #2ea44f;">$0</div></div>
                    <div class="card"><h3>Status</h3><div class="value" id="f_status" style="font-size: 1rem;">--</div></div>
                </div>

                <div id="predictionChartsArea" style="display:none; margin-top:20px;">
                    <div class="accuracy-container" style="display: flex; gap: 20px;">
                    <div style="flex:1; background:white; padding:15px; border-radius:12px; border: 1px solid #eee; height: 300px;">
                        <h4 style="margin-top:0;">Income Accuracy</h4>
                        <canvas id="incomeAccuracyChart"></canvas>
                    </div>
                    <div style="flex:1; background:white; padding:15px; border-radius:12px; border: 1px solid #eee; height: 300px;">
                        <h4 style="margin-top:0;">Expense Accuracy</h4>
                        <canvas id="expenseAccuracyChart"></canvas>
                    </div>
                </div>
            </div>
            </div>
        </div>`;
        initReportDates(); 
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
    const monthInput = document.getElementById('prediction_month').value; 
    const reportEndDate = document.getElementById('report_end_date').value;

    if (!monthInput) return alert("Please select a month first!");

    // VALIDATION: Ensure prediction month is strictly AFTER the report end date
    if (reportEndDate) {
        const reportEndMonth = reportEndDate.substring(0, 7); // Extract YYYY-MM
        if (monthInput <= reportEndMonth) {
            alert("Invalid Selection: Prediction month must be later than the current report end date.");
            return;
        }
    }

    try {
        const res = await fetch(`http://127.0.0.1:8000/api/predict-finances?target_date=${monthInput}-01`);
        const data = await res.json();

        if (data.error) return alert(data.error);

        // 1. Update the Summary Cards
        const f = (v) => `$${v.toLocaleString()}`;
        document.getElementById('f_inc').innerText = f(data.forecast.income);
        document.getElementById('f_exp').innerText = f(data.forecast.expense); 
        document.getElementById('f_prof').innerText = f(data.forecast.profit);
        document.getElementById('f_status').innerText = data.forecast.status;
        document.getElementById('ai-confidence').innerText = `Accuracy: ${data.accuracy}`;

        // 2. Render BOTH charts
        const chartsArea = document.getElementById('predictionChartsArea');
        if (data.comparison && data.comparison.length > 0) {
            chartsArea.style.display = 'block';
            renderDualAccuracyCharts(data.comparison);
        } else {
            chartsArea.style.display = 'none';
        }

    } catch (e) {
        console.error("Connection Error:", e);
        alert("Engine is offline.");
    }
}
let incAccChartInstance = null;
let expAccChartInstance = null;

function renderDualAccuracyCharts(comparisonData) {
    const labels = comparisonData.map(c => c.period);

    // --- CHART 1: INCOME ---
    const ctxInc = document.getElementById('incomeAccuracyChart').getContext('2d');
    if (incAccChartInstance) incAccChartInstance.destroy();
    incAccChartInstance = new Chart(ctxInc, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                { label: 'Actual Inc', data: comparisonData.map(c => c.act_inc), borderColor: '#2ea44f', tension: 0.3 },
                { label: 'Predict', data: comparisonData.map(c => c.pre_inc), borderColor: '#007bff', borderDash: [5, 5], tension: 0.3 }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false ,scales: { y: { beginAtZero: true} }}
    });

    // --- CHART 2: EXPENSE ---
    const ctxExp = document.getElementById('expenseAccuracyChart').getContext('2d');
    if (expAccChartInstance) expAccChartInstance.destroy();
    expAccChartInstance = new Chart(ctxExp, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                { label: 'Actual Exp', data: comparisonData.map(c => c.act_exp), borderColor: '#d73a49', tension: 0.3 },
                { label: 'Predict', data: comparisonData.map(c => c.pre_exp), borderColor: '#f66a0a', borderDash: [5, 5], tension: 0.3 }
            ]
        },
        options: { responsive: true, maintainAspectRatio: false,scales: { y: { beginAtZero: true} } }
    });
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
    // 1. INCOME TREND (Line Chart)
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
        options: { responsive: true, maintainAspectRatio: false}
    });

    // 2. EXPENSE MIX (Pie Chart)
    const ctxPie = document.getElementById('expenseChart').getContext('2d');
    if (expensePieInstance) expensePieInstance.destroy();
    expensePieInstance = new Chart(ctxPie, {
        type: 'doughnut',
        data: {
            labels: ['Payroll', 'COGS', 'Operating'],
            datasets: [{
                data: [breakdown.payroll, breakdown.cogs, breakdown.operating],
                backgroundColor: ['#4e73df', '#1cc88a', '#36b9cc']
            }]
        },
        options: { responsive: true, maintainAspectRatio: false}
    });
}

function showSection(id) {
    const section = document.getElementById(id);
    if (!section) return;

    document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active-section'));
    section.classList.add('active-section');
    if (id === 'report-page' && currentUserRole === 'admin') {
        setTimeout(generateFilteredReport, 100);
    }
}

function updateUI() {
    // ====== Expenses Processing ======
    let exTotal = 0;
    let dashExpHTML = "";
    let manageExpHTML = "";
    
    transactionHistory.forEach((item, idx) => {
        exTotal += item.amt;
        dashExpHTML += `<tr><td>${item.desc}</td><td>${item.cat}</td><td>${item.date}</td><td>${item.payer}</td><td style="color:red">-$${item.amt.toLocaleString()}</td></tr>`;
        manageExpHTML += `
            <tr>
                <td style="text-align:center"><input type="checkbox" class="row-checkbox" data-index="${idx}"></td>
                <td>${item.desc}</td><td>${item.cat}</td><td>${item.date}</td><td>${item.payer}</td>
                <td style="color:red">-$${item.amt.toLocaleString()}</td>
                <td>${currentUserRole === 'admin' ? `<button class="delete-icon-btn" onclick="deleteHistoryItem(${idx})"><i class="fas fa-trash"></i></button>` : `<i class="fas fa-lock" style="color:#ccc"></i>`}</td>
            </tr>
        `;
    });

    // ====== Income Processing ======
    let currentIncomeTotal = 0;
    let incomeHTML = "";
    
    incomeHistory.forEach((item, idx) => {
        currentIncomeTotal += item.amt;
        incomeHTML += `
            <tr>
                <td style="text-align:center"><input type="checkbox" class="income-row-checkbox" data-index="${idx}"></td>
                <td>${item.desc}</td><td>${item.source}</td><td>${item.date}</td><td>${item.receiver}</td>
                <td style="color:green">+$${item.amt.toLocaleString()}</td>
                <td>${currentUserRole === 'admin' ? `<button class="delete-icon-btn" onclick="deleteIncomeItem(${idx})"><i class="fas fa-trash"> </i></button>` : `<i class="fas fa-lock" style="color:#ccc"></i>`}</td>
            </tr>
        `;
    });

    // Update global total and storage
    totalIncome = currentIncomeTotal;
    localStorage.setItem('coffee_income_total', totalIncome);

    // ====== Update Cards ======
    document.getElementById('card-income').innerText = `$${totalIncome.toLocaleString()}`;
    document.getElementById('card-total').innerText = `$${exTotal.toLocaleString()}`;
    document.getElementById('card-remaining').innerText = `$${(totalIncome - exTotal).toLocaleString()}`;

    // ====== Update Tables ======
    document.getElementById('expense-rows').innerHTML = dashExpHTML;
    document.getElementById('history-rows-manage').innerHTML = manageExpHTML;
    document.getElementById('income-history-rows').innerHTML = incomeHTML;

    // ====== Update Reports / Stats ======
    if (currentUserRole === 'admin') {
        const reportCount = document.getElementById('report-count');
        const reportAvg = document.getElementById('report-avg');
        if(reportCount) reportCount.innerText = transactionHistory.length + incomeHistory.length;
        if(reportAvg) reportAvg.innerText = `$${(exTotal / (transactionHistory.length || 1)).toFixed(2)}`;
    } else {
        const saleCount = document.getElementById('sale-count-view');
        if(saleCount) saleCount.innerText = transactionHistory.length + incomeHistory.length;
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
