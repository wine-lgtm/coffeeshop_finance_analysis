
async function loadBudgets() {
    const month = document.getElementById('budget_month_filter').value;
    let url = 'http://127.0.0.1:8000/api/budgets';
    if (month) {
        url += `?month=${month}`;
    }

    try {
        const response = await fetch(url);
        const budgets = await response.json();
        renderBudgetTable(budgets);
        updateBudgetSummary(budgets);
    } catch (error) {
        console.error('Error loading budgets:', error);
    }
}

function renderBudgetTable(budgets) {
    const tbody = document.getElementById('budget-table-body');
    if (!tbody) return;
    
    tbody.innerHTML = '';

    if (budgets.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">No budgets found for this month</td></tr>';
        return;
    }

    budgets.forEach(budget => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${budget.month}</td>
            <td>${budget.category}</td>
            <td>$${parseFloat(budget.amount).toLocaleString()}</td>
            <td>
                <button onclick="editBudget(${budget.id}, '${budget.month}', '${budget.category}', ${budget.amount})" style="background: #f1c40f; border:none; color:white; padding:5px 10px; border-radius:5px; cursor:pointer; margin-right:5px;"><i class="fas fa-edit"></i></button>
                <button onclick="deleteBudget(${budget.id})" style="background: #e74c3c; border:none; color:white; padding:5px 10px; border-radius:5px; cursor:pointer;"><i class="fas fa-trash"></i></button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function updateBudgetSummary(budgets) {
    const total = budgets.reduce((sum, b) => sum + parseFloat(b.amount), 0);
    const totalEl = document.getElementById('total-budget-amount');
    if (totalEl) {
        totalEl.innerText = `$${total.toLocaleString()}`;
    }
}

async function saveBudget() {
    const id = document.getElementById('budget_id').value;
    const month = document.getElementById('budget_month').value;
    const category = document.getElementById('budget_category').value;
    const amount = document.getElementById('budget_amount').value;

    if (!month || !category || !amount) {
        alert('Please fill all fields');
        return;
    }

    const data = { month, category, amount: parseFloat(amount) };
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
            alert('Error saving budget');
        }
    } catch (error) {
        console.error('Error saving budget:', error);
    }
}

async function deleteBudget(id) {
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

function editBudget(id, month, category, amount) {
    document.getElementById('budget_id').value = id;
    document.getElementById('budget_month').value = month;
    document.getElementById('budget_category').value = category;
    document.getElementById('budget_amount').value = amount;
    document.getElementById('form-title').innerText = 'Edit Budget';
    document.getElementById('btn-cancel-edit').style.display = 'inline-block';
}

function clearBudgetForm() {
    document.getElementById('budget_id').value = '';
    // Don't clear month to keep context
    // document.getElementById('budget_month').value = ''; 
    document.getElementById('budget_category').value = '';
    document.getElementById('budget_amount').value = '';
    document.getElementById('form-title').innerText = 'Add New Budget';
    document.getElementById('btn-cancel-edit').style.display = 'none';
}

// Attach event listener when section is shown
function initBudgetPage() {
    const today = new Date();
    const monthStr = today.toISOString().slice(0, 7);
    
    const filterInput = document.getElementById('budget_month_filter');
    const formMonthInput = document.getElementById('budget_month');

    if (filterInput && !filterInput.value) {
        filterInput.value = monthStr;
    }
    if (formMonthInput && !formMonthInput.value) {
        formMonthInput.value = monthStr;
    }

    loadBudgets();
    loadCompanyBudgets();
}

function showCompanyBudget() {
    document.getElementById('company-budget-section').style.display = 'block';
    document.getElementById('category-budget-section').style.display = 'none';
}

function showCategoryBudget() {
    document.getElementById('company-budget-section').style.display = 'none';
    document.getElementById('category-budget-section').style.display = 'block';
}
