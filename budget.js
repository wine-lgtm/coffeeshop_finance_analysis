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
    } catch (error) {
        console.error('Error loading budgets:', error);
    }
}

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
            <td${amountClassAttr}>MMK ${parseFloat(budget.amount).toLocaleString()}</td>
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
                alert(error.detail || 'Error saving budget');
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
            alert('Error deleting budget');
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





