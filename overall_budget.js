// Limit months: current month through next 3 months (same as budget.js — no past months, no beyond 3 months)
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

function updateMonthInputStyle(input) {
    if (!input) return;
    const value = input.value;
    if (!value) {
        input.classList.remove('month-out-of-range');
        return;
    }
    if (isMonthWithinAllowedRange(value)) {
        input.classList.remove('month-out-of-range');
    } else {
        input.classList.add('month-out-of-range');
    }
}

// Enforce allowed range: if value is out of range, clear it so disallowed months cannot be filled
function enforceMonthRange(input, fallbackToCurrent) {
    if (!input) return;
    const value = input.value;
    if (!value) return;
    if (!isMonthWithinAllowedRange(value)) {
        const { currentMonth, maxMonth } = getAllowedMonthRange();
        input.value = fallbackToCurrent ? currentMonth : '';
        updateMonthInputStyle(input);
        input.setCustomValidity('');
        if (fallbackToCurrent) {
            alert(`Only months from ${currentMonth} to ${maxMonth} are allowed. Value was reset.`);
        }
    }
}

async function loadOverallBudgets() {
    const month = document.getElementById('overall_month_filter').value;
    let url = 'http://127.0.0.1:8000/api/overall_budgets';
    if (month) {
        url += `?month=${month}`;
    }

    try {
        const response = await fetch(url);
        const budgets = await response.json();
        renderOverallBudgetTable(budgets);
    } catch (error) {
        console.error('Error loading overall budgets:', error);
    }
}

function renderOverallBudgetTable(budgets) {
    const tbody = document.getElementById('overall-budget-table-body');
    if (!tbody) return;
    
    tbody.innerHTML = '';

    if (budgets.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">No overall budgets found for this month</td></tr>';
        return;
    }

    budgets.forEach(budget => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${budget.month}</td>
            <td>MMK ${parseFloat(budget.amount).toLocaleString()}</td>
            <td>${budget.description || ''}</td>
            <td>
                <button onclick="editOverallBudget(${budget.id}, '${budget.month}', ${budget.amount}, ${budget.description ? `'${String(budget.description).replace(/'/g, "\\'")}'` : 'null'})" style="background: #f1c40f; border:none; color:white; padding:5px 10px; border-radius:5px; cursor:pointer; margin-right:5px;"><i class="fas fa-edit"></i></button>
                <button onclick="deleteOverallBudget(${budget.id})" style="background: #e74c3c; border:none; color:white; padding:5px 10px; border-radius:5px; cursor:pointer;"><i class="fas fa-trash"></i></button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function saveOverallBudget() {
    const id = document.getElementById('overall_budget_id').value;
    const month = document.getElementById('overall_budget_month').value;
    const amount = document.getElementById('overall_budget_amount').value;
    const description = document.getElementById('overall_budget_description').value;
    const filterInput = document.getElementById('overall_month_filter');

    if (!month || !amount) {
        alert('Please fill month and amount');
        return;
    }

    // Block past months and months beyond next 3 (for both new and update)
    if (!isMonthWithinAllowedRange(month)) {
        const { currentMonth, maxMonth } = getAllowedMonthRange();
        alert(`You can only set budgets from ${currentMonth} up to ${maxMonth}. Past and future months are not allowed.`);
        return;
    }

    const data = { month, amount: parseFloat(amount), description: description || null };
    const url = id ? `http://127.0.0.1:8000/api/overall_budgets/${id}` : 'http://127.0.0.1:8000/api/overall_budgets';
    const method = id ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            alert('Overall budget saved successfully!');
            clearOverallForm();
            // Show the month we just saved in the table
            if (filterInput) {
                filterInput.value = month;
            }
            loadOverallBudgets();
        } else {
            const error = await response.json();
            alert(error.detail || 'Error saving overall budget');
        }
    } catch (error) {
        console.error('Error saving overall budget:', error);
    }
}

async function deleteOverallBudget(id) {
    if (!confirm('Are you sure you want to delete this overall budget?')) return;

    try {
        const response = await fetch(`http://127.0.0.1:8000/api/overall_budgets/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            alert('Overall budget deleted successfully!');
            loadOverallBudgets();
        } else {
            alert('Error deleting overall budget');
        }
    } catch (error) {
        console.error('Error deleting overall budget:', error);
    }
}

function editOverallBudget(id, month, amount, description) {
    document.getElementById('overall_budget_id').value = id;
    const monthInput = document.getElementById('overall_budget_month');
    // Allow showing past month when editing (otherwise min/max would hide it)
    monthInput.removeAttribute('min');
    monthInput.removeAttribute('max');
    monthInput.value = month;
    document.getElementById('overall_budget_amount').value = amount;
    const descInput = document.getElementById('overall_budget_description');
    if (descInput) {
        descInput.value = description || '';
    }
    document.getElementById('form-title').innerText = 'Edit Monthly Overall Budget';
    document.getElementById('btn-cancel-edit-overall').style.display = 'inline-block';
}

function clearOverallForm() {
    document.getElementById('overall_budget_id').value = '';
    const monthInput = document.getElementById('overall_budget_month');
    monthInput.value = '';
    applyMonthLimits(monthInput); // restore next-3-months limit for new entry
    document.getElementById('overall_budget_amount').value = '';
    const descInput = document.getElementById('overall_budget_description');
    if (descInput) {
        descInput.value = '';
    }
    document.getElementById('form-title').innerText = 'Add New Monthly Overall Budget';
    document.getElementById('btn-cancel-edit-overall').style.display = 'none';
}

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    const { currentMonth } = getAllowedMonthRange();

    const filterInput = document.getElementById('overall_month_filter');
    const formMonthInput = document.getElementById('overall_budget_month');

    applyMonthLimits(filterInput);
    applyMonthLimits(formMonthInput);

    if (filterInput && !filterInput.value) {
        filterInput.value = currentMonth;
    }
    if (formMonthInput && !formMonthInput.value) {
        formMonthInput.value = currentMonth;
    }

    updateMonthInputStyle(formMonthInput);
    updateMonthInputStyle(filterInput);

    var hintEl = document.getElementById('overall_month_hint');
    if (hintEl) {
        hintEl.textContent = 'Allowed: ' + currentMonth + ' to ' + getAllowedMonthRange().maxMonth + ' (current month through next 3 months)';
    }

    if (formMonthInput) {
        formMonthInput.addEventListener('change', function() {
            // Disallowed months cannot be filled: reset to current month if out of range
            enforceMonthRange(formMonthInput, true);
            updateMonthInputStyle(formMonthInput);
            if (isMonthWithinAllowedRange(formMonthInput.value)) {
                formMonthInput.setCustomValidity('');
                // Sync filter and table to selected month (like budget.js)
                if (filterInput) {
                    filterInput.value = formMonthInput.value;
                    loadOverallBudgets();
                }
            }
        });
        formMonthInput.addEventListener('input', function() {
            updateMonthInputStyle(formMonthInput);
        });
        formMonthInput.addEventListener('blur', function() {
            enforceMonthRange(formMonthInput, true);
            if (isMonthWithinAllowedRange(formMonthInput.value) && filterInput) {
                filterInput.value = formMonthInput.value;
                loadOverallBudgets();
            }
        });
    }
    if (filterInput) {
        filterInput.addEventListener('change', function() {
            enforceMonthRange(filterInput, true);
            updateMonthInputStyle(filterInput);
            loadOverallBudgets();
        });
    }

    loadOverallBudgets();
});