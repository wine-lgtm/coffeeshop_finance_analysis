// Payroll budget client logic (based on overall_budget.js)

function getAllowedMonthRange() {
    const now = new Date();
    const current = new Date(now.getFullYear(), now.getMonth(), 1);
    const max = new Date(now.getFullYear(), now.getMonth() + 3, 1);
    const toMonthStr = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    return { currentMonth: toMonthStr(current), maxMonth: toMonthStr(max) };
}

function applyMonthLimits(input) {
    if (!input) return;
    const { currentMonth, maxMonth } = getAllowedMonthRange();
    input.min = currentMonth; input.max = maxMonth;
}

function isMonthWithinAllowedRange(monthStr) {
    if (!monthStr) return false;
    const { currentMonth, maxMonth } = getAllowedMonthRange();
    return monthStr >= currentMonth && monthStr <= maxMonth;
}

async function loadPayrollBudgets() {
    const month = document.getElementById('payroll_month_filter').value;
    let url = 'http://127.0.0.1:8000/api/payroll_budgets';
    if (month) url += `?month=${month}`;

    try {
        const res = await fetch(url);
        const budgets = await res.json();
        renderPayrollBudgetTable(budgets || []);
        // Also refresh payroll 3-month insights so they reflect the selected month
        if (typeof updatePayrollInsights === 'function') updatePayrollInsights();
    } catch (e) {
        console.error('Error loading payroll budgets:', e);
    }
}

function renderPayrollBudgetTable(budgets) {
    const tbody = document.getElementById('payroll-budget-table-body');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (!budgets || budgets.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">No payroll budgets found for this month</td></tr>';
        return;
    }
    budgets.forEach(b => {
        const tr = document.createElement('tr');
        tr.dataset.id = b.id;
        tr.innerHTML = `
            <td>${b.month}</td>
            <td>$ ${parseFloat(b.amount).toLocaleString()}</td>
            <td>${b.description || ''}</td>
            <td>
                <button onclick="editPayrollBudget(${b.id}, '${b.month}', ${b.amount}, ${b.description ? `'${String(b.description).replace(/'/g, "\\'")}'` : 'null'})" style="background:#f1c40f; border:none; color:white; padding:6px 8px; border-radius:6px; margin-right:6px;"><i class=\"fas fa-edit\"></i></button>
                <button onclick="attemptDeletePayrollBudget(${b.id}, '${b.month}')" style="background:#e74c3c; border:none; color:white; padding:6px 8px; border-radius:6px;"><i class=\"fas fa-trash\"></i></button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function savePayrollBudget() {
    const id = document.getElementById('payroll_budget_id').value;
    const month = document.getElementById('payroll_budget_month').value;
    const amount = document.getElementById('payroll_budget_amount').value;
    const description = document.getElementById('payroll_budget_description').value;
    const filterInput = document.getElementById('payroll_month_filter');

    if (!month || !amount) { alert('Please fill month and amount'); return; }
    if (!isMonthWithinAllowedRange(month)) {
        const { currentMonth, maxMonth } = getAllowedMonthRange();
        alert(`You can only set budgets from ${currentMonth} up to ${maxMonth}.`);
        return;
    }

    const data = { month, amount: parseFloat(amount), description: description || null };
    const url = id ? `http://127.0.0.1:8000/api/payroll_budgets/${id}` : 'http://127.0.0.1:8000/api/payroll_budgets';
    const method = id ? 'PUT' : 'POST';

    try {
        const res = await fetch(url, { method, headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) });
        if (res.ok) {
            alert('Payroll budget saved successfully!');
            clearPayrollForm();
            if (filterInput) filterInput.value = month;
            loadPayrollBudgets();
        } else {
            try {
                const err = await res.json();
                const detail = typeof err.detail === 'string'
                    ? err.detail
                    : (Array.isArray(err.detail)
                        ? err.detail.map(d => (d && d.msg) || (typeof d === 'string' ? d : '')).join(' ')
                        : (err.detail || ''));
                const isOverrun = typeof detail === 'string' &&
                    (detail.includes('exceeds the overall budget') ||
                     detail.includes('Sum of main category budgets including payroll'));
                if (isOverrun && typeof showCategoryOverrunPanel === 'function') {
                    showCategoryOverrunPanel(detail);
                    alert('Payroll budget would push total above the overall limit. Use the Finalize (scale to fit) panel that just appeared to scale main categories and payroll.');
                } else {
                    alert(detail || 'Error saving payroll budget');
                }
            } catch (e) {
                alert('Error saving payroll budget');
            }
        }
    } catch (e) { console.error('Error saving payroll budget:', e); }
}

function attemptDeletePayrollBudget(id, month) {
    const { currentMonth } = getAllowedMonthRange();
    if (month === currentMonth) {
        alert('Ongoing budget can not be deleted');
        return;
    }
    deletePayrollBudget(id);
}

async function deletePayrollBudget(id) {
    if (!confirm('Are you sure you want to delete this payroll budget?')) return;
    try {
        const res = await fetch(`http://127.0.0.1:8000/api/payroll_budgets/${id}`, { method: 'DELETE' });
        const body = await res.json().catch(() => null);
        if (res.ok) {
            alert((body && body.message) ? body.message : 'Payroll budget deleted');
            // remove row from table immediately
            const row = document.querySelector(`#payroll-budget-table-body tr[data-id="${id}"]`);
            if (row) row.remove();
            // refresh insights and optionally reload list to be safe
            if (typeof updatePayrollInsights === 'function') updatePayrollInsights();
        } else {
            const detail = body && (body.detail || body.message) ? (body.detail || body.message) : 'Error deleting payroll budget';
            alert(detail);
        }
    } catch (e) { console.error('Error deleting payroll budget:', e); alert('Error deleting payroll budget'); }
}

function editPayrollBudget(id, month, amount, description) {
    document.getElementById('payroll_budget_id').value = id;
    const monthInput = document.getElementById('payroll_budget_month');
    monthInput.removeAttribute('min'); monthInput.removeAttribute('max');
    monthInput.value = month;
    document.getElementById('payroll_budget_amount').value = amount;
    const desc = document.getElementById('payroll_budget_description'); if (desc) desc.value = description || '';
    document.getElementById('payroll-form-title').innerText = 'Edit Monthly Payroll Budget';
    document.getElementById('btn-cancel-edit-payroll').style.display = 'inline-block';
}

function clearPayrollForm() {
    document.getElementById('payroll_budget_id').value = '';
    const monthInput = document.getElementById('payroll_budget_month');
    monthInput.value = '';
    applyMonthLimits(monthInput);
    document.getElementById('payroll_budget_amount').value = '';
    const desc = document.getElementById('payroll_budget_description'); if (desc) desc.value = '';
    document.getElementById('payroll-form-title').innerText = 'Add New Monthly Payroll Budget';
    document.getElementById('btn-cancel-edit-payroll').style.display = 'none';
}

document.addEventListener('DOMContentLoaded', function() {
    const { currentMonth } = getAllowedMonthRange();
    const filterInput = document.getElementById('payroll_month_filter');
    const formMonthInput = document.getElementById('payroll_budget_month');

    applyMonthLimits(filterInput); applyMonthLimits(formMonthInput);
    if (filterInput && !filterInput.value) filterInput.value = currentMonth;
    if (formMonthInput && !formMonthInput.value) formMonthInput.value = currentMonth;

    if (formMonthInput) {
        formMonthInput.addEventListener('change', function() {
            if (!isMonthWithinAllowedRange(formMonthInput.value)) {
                const { currentMonth } = getAllowedMonthRange(); formMonthInput.value = currentMonth;
            }
            if (filterInput) { filterInput.value = formMonthInput.value; loadPayrollBudgets(); }
            if (typeof updateKPIsForPayroll === 'function') updateKPIsForPayroll();
        });
    }
    if (filterInput) filterInput.addEventListener('change', loadPayrollBudgets);
    loadPayrollBudgets();
});

// --- Payroll insights: workers list + 3-month netpay ---
async function updatePayrollInsights() {
    const filterInput = document.getElementById('payroll_month_filter');
    if (!filterInput) return;
    const base = filterInput.value ? new Date(filterInput.value + '-01') : new Date();

    // build months: selected and previous two months
    const months = [];
     for (let i = 3; i >= 1; i--) {
        const d = new Date(base.getFullYear(), base.getMonth() - i, 1);
        months.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2,'0')}`);
    }


    // Fetch per-month payroll totals using financial-summary
    const results = [];
    for (const m of months) {
        let payrollTotal = 0;
        try {
            const [y, mm] = m.split('-').map(v=>parseInt(v,10));
            const last = new Date(y, mm, 0).getDate();
            const start = `${m}-01`;
            const end = `${m}-${String(last).padStart(2,'0')}`;
            const res = await fetch(`http://127.0.0.1:8000/api/financial-summary?start_date=${start}&end_date=${end}`);
            if (res.ok) {
                const data = await res.json();
                payrollTotal = Number((data.summary && (data.summary.exact_labor_cost || data.summary.exact_labor_cost === 0) ? data.summary.exact_labor_cost : (data.breakdown ? data.breakdown.payroll : 0)) || 0);
            }
        } catch (e) { console.error('financial-summary fetch failed for', m, e); }
        results.push({ month: m, payroll: Math.round(payrollTotal*100)/100 });
    }

    // render table
    const tbody = document.getElementById('payroll-three-month-table-body');
    if (tbody) {
        tbody.innerHTML = '';
        results.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td style="padding:8px">${r.month}</td><td style="text-align:right; padding:8px">$ ${Number(r.payroll).toLocaleString()}</td>`;
            tbody.appendChild(tr);
        });
    }

    const avg = results.reduce((s,x)=>s+x.payroll,0)/results.length;
    const highest = results.reduce((best, cur) => (cur.payroll > (best.payroll||0) ? cur : best), {});
    const avgEl = document.getElementById('payroll-three-month-avg');
    const highEl = document.getElementById('payroll-three-month-highest');
    const bufEl = document.getElementById('payroll-three-month-buffer');
    if (avgEl) avgEl.innerText = `$ ${Number((Math.round(avg*100)/100)).toFixed(2)}`;
    if (highEl) highEl.innerText = `${highest.month || '-'} ($ ${Number((highest.payroll||0)).toLocaleString()})`;
    if (bufEl) bufEl.innerText = `$ ${Number((Math.round(avg * 1.10 * 100)/100)).toFixed(2)}`;

    // Wire action buttons to populate amount input
    const useAvgBtn = document.getElementById('use-payroll-average-btn');
    const useHighBtn = document.getElementById('use-payroll-highest-btn');
    const useAvgBufBtn = document.getElementById('use-payroll-avg-buffer-btn');
    const amountInput = document.getElementById('payroll_budget_amount');
    if (useAvgBtn) useAvgBtn.onclick = () => { if (!amountInput) return; amountInput.value = (Math.round(avg*100)/100).toFixed(2); };
    if (useHighBtn) useHighBtn.onclick = () => { if (!amountInput) return; amountInput.value = (Math.round((highest.payroll||0)*100)/100).toFixed(2); };
    if (useAvgBufBtn) useAvgBufBtn.onclick = () => { if (!amountInput) return; let cur = parseFloat(amountInput.value); if (isNaN(cur)) cur = avg; const out = Math.round((cur * 1.10) * 100) / 100; amountInput.value = out.toFixed(2); };

    // Worker list: fetch active employees from employees_static and render count + base-pay sum
    try {
        const empRes = await fetch('http://127.0.0.1:8000/api/employees');
        if (empRes.ok) {
            const employees = await empRes.json();
            const listEl = document.getElementById('payroll-worker-list');
            const countEl = document.getElementById('payroll-worker-count');
            const sumEl = document.getElementById('payroll-worker-base-sum');
            if (listEl) {
                listEl.innerHTML = '';
                employees.forEach(e => {
                    const name = e.employee_name || '(Unknown)';
                    const role = e.role || '';
                    const base = Number(e.base_pay || 0);
                    const div = document.createElement('div');
                    div.style.padding = '6px 0';
                    div.innerHTML = `<div style="display:flex; justify-content:space-between;"><div>${role ? role + ' — ' : ''}${name}</div><div>$ ${base.toLocaleString()}</div></div>`;
                    listEl.appendChild(div);
                });
            }
            if (countEl) countEl.innerText = employees.length;
            if (sumEl) {
                const totalBase = employees.reduce((s, x) => s + (Number(x.base_pay) || 0), 0);
                sumEl.innerText = `$ ${Number((Math.round(totalBase * 100) / 100)).toLocaleString()}`;
            }
        }
    } catch (e) { console.error('employees fetch failed', e); }

    // toggle worker list
    const toggleBtn = document.getElementById('toggle-worker-list');
    if (toggleBtn) {
        toggleBtn.onclick = () => {
            const list = document.getElementById('worker-summary');
            if (!list) return;
            if (list.style.display === 'none') { list.style.display = ''; toggleBtn.innerText = 'Hide'; }
            else { list.style.display = 'none'; toggleBtn.innerText = 'Show'; }
        };
    }
}

// call on load and when filter changes
document.addEventListener('DOMContentLoaded', function() {
    const filter = document.getElementById('payroll_month_filter');
    updatePayrollInsights();
    if (filter) filter.addEventListener('change', updatePayrollInsights);
});
