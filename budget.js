const allowedSubcategoriesByCategory = {
    'COGS': [
        'Bakery Payment',
        'Coffee Supplier Payment',
        'Supplies',
        'Ingredients / Groceries',
        'Packaging'
    ],
    'Operating expense': [
        'Utilities',
        'Utility Bill Payment',
        'Marketing',
        'Marketing / promotion',
        'Taxes / licenses / bank fees',
        'Rent Payment',
        'Miscellaneous',
        'Staff meal',
        'Equipment purchase',
        'Local Print Shop',
        'Facebook Ads',
        'Utility Company'
    ]
};

// pendingBudget holds an unsaved main-category entry that triggered an overrun error.
// finalize operation will include its amount when scaling so the new row gets created.
let pendingBudget = null;

// Limit months: current month through next 3 months (no past months)
function getAllowedMonthRange() {
    const now = new Date();
    const current = new Date(now.getFullYear(), now.getMonth(), 1);
    const max = new Date(now.getFullYear(), now.getMonth() + 3, 1);

    const toMonthStr = (d) => {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        return `${y}-${m}`;
    };

    return {
        currentMonth: toMonthStr(current),
        maxMonth: toMonthStr(max)
    };
}

function applyMonthLimits(input) {
    if (!input) return;
    const { currentMonth, maxMonth } = getAllowedMonthRange();
    input.min = currentMonth;
    input.max = maxMonth;
}

function isMonthWithinAllowedRange(monthStr) {
    if (!monthStr) return false;
    const { currentMonth, maxMonth } = getAllowedMonthRange();
    return monthStr >= currentMonth && monthStr <= maxMonth;
}

function updateSubcategoryOptions() {
    const categorySelect = document.getElementById('budget_category');
    const subcategorySelect = document.getElementById('budget_subcategory');
    if (!categorySelect || !subcategorySelect) return;

    const category = categorySelect.value;
    const options = allowedSubcategoriesByCategory[category] || [];

    let html = '<option value="">Select Sub Category</option>';
    html += options.map(opt => `<option value="${opt}">${opt}</option>`).join('');
    subcategorySelect.innerHTML = html;
}

function initBudgetForm() {
    const categorySelect = document.getElementById('budget_category');
    const monthInput = document.getElementById('budget_month');
    const filterInput = document.getElementById('budget_month_filter');

    if (categorySelect) {
        categorySelect.addEventListener('change', updateSubcategoryOptions);
        updateSubcategoryOptions();
    }

    // Apply month limits (current month to next 3 months) to inputs
    applyMonthLimits(monthInput);
    applyMonthLimits(filterInput);

    if (monthInput) {
        monthInput.addEventListener('change', handleBudgetMonthChange);
    }
}

async function handleBudgetMonthChange() {
    const monthInput = document.getElementById('budget_month');
    const filterInput = document.getElementById('budget_month_filter');
    const categorySelect = document.getElementById('budget_category');
    const subcategorySelect = document.getElementById('budget_subcategory');
    if (!monthInput || !categorySelect || !subcategorySelect) return;

    const month = monthInput.value;
    const category = categorySelect.value;
    const subcategory = subcategorySelect.value;

    if (!month) return;

    // Enforce month within allowed range on change
    if (!isMonthWithinAllowedRange(month)) {
        const { currentMonth, maxMonth } = getAllowedMonthRange();
        alert(`You can only set budgets from ${currentMonth} up to ${maxMonth}.`);
        monthInput.value = currentMonth;
        if (filterInput) {
            filterInput.value = currentMonth;
            loadBudgets();
        }
        return;
    }

    // For main category budgets (no subcategory selected), pre-check if a budget already exists
    if (!subcategory && category) {
        try {
            const response = await fetch(`http://127.0.0.1:8000/api/budgets?month=${month}`);
            if (!response.ok) return;
            const budgets = await response.json();
            const existsForCategory = budgets.some(
                (b) => b.category === category && !b.subcategory
            );
            if (existsForCategory) {
                alert('Budget already exists for this category and month');
            }
        } catch (e) {
            console.error('Error checking existing budgets for month:', e);
        }
    }

    // Keep the table in sync with the selected month
    if (filterInput) {
        filterInput.value = month;
        loadBudgets();
    }
}

async function loadBudgets() {
    const month = document.getElementById('budget_month_filter').value;
    let url = 'http://127.0.0.1:8000/api/budgets';
    if (month) {
        url += `?month=${month}`;
    }

    try {
        const response = await fetch(url);
        const budgets = await response.json();
        
        // Filter budgets by category
        const cogsBudgets = budgets.filter(b => b.category === 'COGS');
        const operatingBudgets = budgets.filter(b => b.category === 'Operating expense');
        
        // Render separate tables
        renderBudgetTable(cogsBudgets, 'cogs-budget-table-body');
        renderBudgetTable(operatingBudgets, 'operating-budget-table-body');
        
        // Update summaries
        updateBudgetSummary(cogsBudgets, 'cogs-total');
        updateBudgetSummary(operatingBudgets, 'operating-total');
        // Also refresh the 3-month category insights so they reflect the selected month
        if (typeof updateCategoryThreeMonthInsights === 'function') updateCategoryThreeMonthInsights();
        // Refresh KPIs and overrun panel when on category budget page
        if (typeof updateCategoryKPIs === 'function') updateCategoryKPIs();
    } catch (error) {
        console.error('Error loading budgets:', error);
    }
}

// Compute and render 3-month insights for category budgets (COGS and Operating expense)
async function updateCategoryThreeMonthInsights() {
    // prevent concurrent executions which can cause duplicate rows when called
    // from multiple places (DOMContentLoaded + loadBudgets)
    if (updateCategoryThreeMonthInsights._running) return;
    updateCategoryThreeMonthInsights._running = true;
    const tbody = document.getElementById('category-three-month-table-body');
    const cogsAvgEl = document.getElementById('category-three-month-cogs-avg-value');
    const cogsHighEl = document.getElementById('category-three-month-cogs-highest');
    const operAvgEl = document.getElementById('category-three-month-oper-avg-value');
    const operHighEl = document.getElementById('category-three-month-oper-highest');
    const filterInput = document.getElementById('budget_month_filter');
    if (!tbody || !filterInput) return;

    const base = filterInput.value ? new Date(filterInput.value + '-01') : new Date();
    const months = [];
    // Use the three months immediately BEFORE the selected month (e.g. April -> Jan, Feb, Mar)
    for (let i = 3; i >= 1; i--) {
        const d = new Date(base.getFullYear(), base.getMonth() - i, 1);
        months.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2,'0')}`);
    }

    tbody.innerHTML = '';
    const results = [];

    for (const m of months) {
        let cogsBudget = 0;
        let operBudget = 0;
        try {
            const bRes = await fetch(`http://127.0.0.1:8000/api/budgets?month=${m}`);
            if (bRes.ok) {
                const bs = await bRes.json();
                cogsBudget = (bs || []).filter(b => b.category === 'COGS').reduce((s,x)=>s+Number(x.amount||0),0);
                operBudget = (bs || []).filter(b => b.category === 'Operating expense').reduce((s,x)=>s+Number(x.amount||0),0);
            }
        } catch (e) { console.error('budget fetch failed for', m, e); }

        let cogsExpense = 0;
        let operExpense = 0;
        try {
            const [y, mm] = m.split('-').map(v=>parseInt(v,10));
            const last = new Date(y, mm, 0).getDate();
            const start = `${m}-01`;
            const end = `${m}-${String(last).padStart(2,'0')}`;
            const fRes = await fetch(`http://127.0.0.1:8000/api/financial-summary?start_date=${start}&end_date=${end}`);
            if (fRes.ok) {
                const data = await fRes.json();
                const breakdown = data.breakdown || {};
                cogsExpense = Number(breakdown.cogs || 0);
                operExpense = Number(breakdown.operating || 0);
            }
        } catch (e) { console.error('financial-summary fetch failed for', m, e); }

        results.push({ month: m, cogsBudget: Math.round(cogsBudget*100)/100, cogsExpense: Math.round(cogsExpense*100)/100, operBudget: Math.round(operBudget*100)/100, operExpense: Math.round(operExpense*100)/100 });
    }

    // render rows (only show expenses)
    results.forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td style="padding:10px">${r.month}</td>
            <td class="amount-cell" style="text-align:right">$ ${r.cogsExpense.toLocaleString()}</td>
            <td class="amount-cell" style="text-align:right">$ ${r.operExpense.toLocaleString()}</td>
        `;
        tbody.appendChild(tr);
    });

    // release running flag
    updateCategoryThreeMonthInsights._running = false;

    // averages
    const avgCogsBudget = results.reduce((s,x)=>s+x.cogsBudget,0)/results.length;
    const avgCogsExpense = results.reduce((s,x)=>s+x.cogsExpense,0)/results.length;
    const avgOperBudget = results.reduce((s,x)=>s+x.operBudget,0)/results.length;
    const avgOperExpense = results.reduce((s,x)=>s+x.operExpense,0)/results.length;

    const cogsMost = results.reduce((best, cur) => (cur.cogsExpense > (best.cogsExpense||0) ? cur : best), {});
    const operMost = results.reduce((best, cur) => (cur.operExpense > (best.operExpense||0) ? cur : best), {});

    const elCogsExpenseAvg = document.getElementById('category-three-month-cogs-expense-avg');
    const elOperExpenseAvg = document.getElementById('category-three-month-oper-expense-avg');

    if (elCogsExpenseAvg) elCogsExpenseAvg.innerText = `$ ${Math.round(avgCogsExpense).toLocaleString()}`;
    if (elOperExpenseAvg) elOperExpenseAvg.innerText = `$ ${Math.round(avgOperExpense).toLocaleString()}`;

    if (cogsAvgEl) cogsAvgEl.innerText = `$ ${Number((Math.round(avgCogsExpense*100)/100)).toFixed(2)}`;
    if (operAvgEl) operAvgEl.innerText = `$ ${Number((Math.round(avgOperExpense*100)/100)).toFixed(2)}`;
    if (cogsHighEl) cogsHighEl.innerText = `${cogsMost.month || '-'} ($ ${Number((cogsMost.cogsExpense||0)).toLocaleString()})`;
    if (operHighEl) operHighEl.innerText = `${operMost.month || '-'} ($ ${Number((operMost.operExpense||0)).toLocaleString()})`;

    // wire buttons to populate the amount input based on selected main category
    const useAvgBtn = document.getElementById('use-cat-average-btn');
    const useHighBtn = document.getElementById('use-cat-highest-btn');
    const useAvgBufBtn = document.getElementById('use-cat-avg-buffer-btn');
    const amountInput = document.getElementById('budget_amount');

    const categorySelect = document.getElementById('budget_category');
    function getAvgForSelected() {
        const cat = categorySelect ? categorySelect.value : '';
        if (cat === 'COGS') return avgCogsExpense;
        if (cat === 'Operating expense') return avgOperExpense;
        return null;
    }
    function getHighForSelected() {
        const cat = categorySelect ? categorySelect.value : '';
        if (cat === 'COGS') return cogsMost.cogsExpense || 0;
        if (cat === 'Operating expense') return operMost.operExpense || 0;
        return null;
    }

    if (useAvgBtn) useAvgBtn.onclick = () => {
        if (!amountInput) return;
        const v = getAvgForSelected();
        if (v === null) return alert('Select a main category first');
        amountInput.value = (Math.round(v*100)/100).toFixed(2);
    };
    if (useHighBtn) useHighBtn.onclick = () => {
        if (!amountInput) return;
        const v = getHighForSelected();
        if (v === null) return alert('Select a main category first');
        amountInput.value = (Math.round(v*100)/100).toFixed(2);
    };
    if (useAvgBufBtn) useAvgBufBtn.onclick = () => {
        if (!amountInput) return;
        let cur = parseFloat(amountInput.value);
        if (isNaN(cur)) {
            const v = getAvgForSelected();
            if (v === null) return alert('Select a main category first');
            cur = v;
        }
        const out = Math.round((cur * 1.10) * 100) / 100;
        amountInput.value = out.toFixed(2);
    };
}

// call insights on load and when filter changes
document.addEventListener('DOMContentLoaded', function() {
    const filter = document.getElementById('budget_month_filter');
    updateCategoryThreeMonthInsights();
    if (filter) filter.addEventListener('change', updateCategoryThreeMonthInsights);
});

function renderBudgetTable(budgets, tableBodyId) {
    const tbody = document.getElementById(tableBodyId);
    if (!tbody) return;
    
    tbody.innerHTML = '';

    if (budgets.length === 0) {
        const colspan = '4';
        tbody.innerHTML = `<tr><td colspan="${colspan}" style="text-align:center;">No budgets found for this month</td></tr>`;
        return;
    }

    // Ensure main category row (no subcategory) is always on top
    const sortedBudgets = [...budgets].sort((a, b) => {
        const aIsMain = !a.subcategory;
        const bIsMain = !b.subcategory;
        if (aIsMain && !bIsMain) return -1;
        if (!aIsMain && bIsMain) return 1;
        return 0;
    });

    const role = (localStorage.getItem('coffee_user_role') || '').toLowerCase();
    const showActions = role === 'admin';
    sortedBudgets.forEach(budget => {
        const tr = document.createElement('tr');
        const safeMonth = String(budget.month).replace(/'/g, "\\'");
        const safeCategory = String(budget.category).replace(/'/g, "\\'");
        const safeSubcategory = (budget.subcategory ? String(budget.subcategory) : '').replace(/'/g, "\\'");
        const isMainCategory = !budget.subcategory;
        const amountClassAttr = isMainCategory ? ' class="main-budget-amount"' : '';

        const actionsHtml = showActions ? `
                <button onclick="editBudget(${budget.id}, '${safeMonth}', '${safeCategory}', '${safeSubcategory}', ${budget.amount})" style="background: #f1c40f; border:none; color:white; padding:5px 10px; border-radius:5px; cursor:pointer; margin-right:5px;"><i class="fas fa-edit"></i></button>
                <button onclick="deleteBudget(${budget.id})" style="background: #e74c3c; border:none; color:white; padding:5px 10px; border-radius:5px; cursor:pointer;"><i class="fas fa-trash"></i></button>
            ` : '<span style="color:#666;">No actions</span>';

        tr.innerHTML = `
            <td>${budget.month}</td>
            <td>${budget.subcategory || '-'}</td>
            <td${amountClassAttr}>$ ${parseFloat(budget.amount).toLocaleString()}</td>
            <td>${actionsHtml}</td>
        `;
        tbody.appendChild(tr);
    });
}

function updateBudgetSummary(budgets, totalElementId) {
    // Only sum sub-category budgets (exclude main category rows where subcategory is null/empty)
    const total = budgets
        .filter(b => b.subcategory !== null && b.subcategory !== undefined && String(b.subcategory).trim() !== '')
        .reduce((sum, b) => sum + parseFloat(b.amount), 0);
    const totalEl = document.getElementById(totalElementId);
    if (totalEl) {
        totalEl.innerText = total.toLocaleString();
    }
}

async function saveBudget() {
    const role = (localStorage.getItem('coffee_user_role') || '').toLowerCase();
    if (role !== 'admin') return alert('Only Admin can create or edit budgets.');

    const id = document.getElementById('budget_id').value;
    const month = document.getElementById('budget_month').value;
    const category = document.getElementById('budget_category').value;
    const subcategory = document.getElementById('budget_subcategory').value;
    const amount = document.getElementById('budget_amount').value;

    if (!month || !category || !amount) {
        alert('Please fill all fields');
        return;
    }

    const data = { month, category, subcategory: subcategory || null, amount: parseFloat(amount) };
    const url = id ? `http://127.0.0.1:8000/api/budgets/${id}` : 'http://127.0.0.1:8000/api/budgets';
    const method = id ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            // alert('Budget saved successfully');
            clearBudgetForm();
            loadBudgets();
        } else {
            try {
                const error = await response.json();
                const detail = typeof error.detail === 'string' ? error.detail : (Array.isArray(error.detail) ? (error.detail.map(function(d){ return (d && d.msg) || (typeof d === 'string' ? d : ''); }).join(' ')) : (error.detail || ''));
                // treat either a straight overrun or the "90% rule" message as an overrun
                // case so that the panel appears; the server now prefers the overrun
                // message when both rules would be triggered, but keep the client-side
                // check for completeness.
                const isOverrun =
                    typeof detail === 'string' &&
                    (detail.includes('exceeds the overall budget') || detail.includes('must not exceed 90%'));
                if (isOverrun && typeof showCategoryOverrunPanel === 'function') {
                    // remember the values that triggered the overrun so finalize can include them
                    pendingBudget = { month, category, subcategory: subcategory || null, amount: parseFloat(amount) };
                    showCategoryOverrunPanel(detail);
                    // custom alert depending on which rule fired
                    if (detail.includes('exceeds the overall budget')) {
                        alert('Budget exceeds overall limit. Use the Finalize (scale to fit) panel below to scale all categories to fit.');
                    } else {
                        alert(detail + '\n(you may still use the Finalize panel to scale, but note the 90% limitation)');
                    }
                } else {
                    alert(detail || 'Error saving budget');
                }
            } catch (e) {
                alert('Error saving budget');
            }
        }
    } catch (error) {
        console.error('Error saving budget:', error);
    }
}

async function deleteBudget(id) {
    const role = (localStorage.getItem('coffee_user_role') || '').toLowerCase();
    if (role !== 'admin') return alert('Only Admin can delete budgets.');
    if (!confirm('Are you sure you want to delete this budget?')) return;

    try {
        const response = await fetch(`http://127.0.0.1:8000/api/budgets/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            loadBudgets();
        } else {
            let msg = 'Error deleting budget';
            try {
                const error = await response.json();
                if (error && error.detail === 'Cannot delete ongoing budget') {
                    msg = 'Cannot delete ongoing budget';
                }
            } catch (e) {}
            alert(msg);
        }
    } catch (error) {
        console.error('Error deleting budget:', error);
    }
}

function editBudget(id, month, category, subcategory, amount) {
    const role = (localStorage.getItem('coffee_user_role') || '').toLowerCase();
    if (role !== 'admin') return alert('Only Admin can edit budgets.');

    document.getElementById('budget_id').value = id;
    document.getElementById('budget_month').value = month;
    const categorySelect = document.getElementById('budget_category');
    const subcategorySelect = document.getElementById('budget_subcategory');

    if (categorySelect) {
        categorySelect.value = category;
        updateSubcategoryOptions();
    }

    if (subcategorySelect && subcategory) {
        // Ensure the existing subcategory is present in options
        let exists = false;
        Array.from(subcategorySelect.options).forEach(opt => {
            if (opt.value === subcategory) {
                exists = true;
            }
        });
        if (!exists) {
            const opt = document.createElement('option');
            opt.value = subcategory;
            opt.textContent = subcategory;
            subcategorySelect.appendChild(opt);
        }
        subcategorySelect.value = subcategory;
    }

    document.getElementById('budget_amount').value = amount;
    document.getElementById('form-title').innerText = 'Edit Budget';
    document.getElementById('btn-cancel-edit').style.display = 'inline-block';
}

function clearBudgetForm() {
    document.getElementById('budget_id').value = '';
    // Don't clear month to keep context
    // document.getElementById('budget_month').value = ''; 
    document.getElementById('budget_category').value = '';
    const subcategorySelect = document.getElementById('budget_subcategory');
    if (subcategorySelect) {
        subcategorySelect.value = '';
    }
    document.getElementById('budget_amount').value = '';
    document.getElementById('form-title').innerText = 'Add New Budget';
    document.getElementById('btn-cancel-edit').style.display = 'none';
}





