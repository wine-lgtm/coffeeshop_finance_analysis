async function loadCompanyBudgets() {
    const month = document.getElementById('company_month_filter').value;
    let url = 'http://127.0.0.1:8000/api/company_budgets';
    if (month) {
        url += `?month=${month}`;
    }

    try {
        const response = await fetch(url);
        const budgets = await response.json();
        renderCompanyBudgetTable(budgets);
        updateCompanyBudgetSummary(budgets);
    } catch (error) {
        console.error('Error loading company budgets:', error);
    }
}

function renderCompanyBudgetTable(budgets) {
    const tbody = document.getElementById('company-budget-table-body');
    if (!tbody) return;
    
    tbody.innerHTML = '';

    if (budgets.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;">No company budgets found for this month</td></tr>';
        return;
    }

    const role = (localStorage.getItem('coffee_user_role') || '').toLowerCase();
    const showActions = role === 'admin';
    budgets.forEach(budget => {
        const tr = document.createElement('tr');
        const actions = showActions ? `
                <button onclick="editCompanyBudget(${budget.id}, '${budget.month}', ${budget.amount})" style="background: #f1c40f; border:none; color:white; padding:5px 10px; border-radius:5px; cursor:pointer; margin-right:5px;"><i class="fas fa-edit"></i></button>
                <button onclick="deleteCompanyBudget(${budget.id})" style="background: #e74c3c; border:none; color:white; padding:5px 10px; border-radius:5px; cursor:pointer;"><i class="fas fa-trash"></i></button>
            ` : '<span style="color:#666;">No actions</span>';

        tr.innerHTML = `
            <td>${budget.month}</td>
            <td>$ ${parseFloat(budget.amount).toLocaleString()}</td>
            <td>${actions}</td>
        `;
        tbody.appendChild(tr);
    });
}

function updateCompanyBudgetSummary(budgets) {
    const total = budgets.reduce((sum, b) => sum + parseFloat(b.amount), 0);
    const totalEl = document.getElementById('company-budget-total');
    if (totalEl) {
        totalEl.innerText = `$ ${total.toLocaleString()}`;
    }
}

async function saveCompanyBudget() {
    const role = (localStorage.getItem('coffee_user_role') || '').toLowerCase();
    if (role !== 'admin') return alert('Only Admin can create or edit company budgets.');

    const id = document.getElementById('company_budget_id').value;
    const month = document.getElementById('company_budget_month').value;
    const amount = document.getElementById('company_budget_amount').value;

    if (!month || !amount) {
        alert('Please fill all fields');
        return;
    }

    const data = { month, amount: parseFloat(amount) };
    const url = id ? `http://127.0.0.1:8000/api/company_budgets/${id}` : 'http://127.0.0.1:8000/api/company_budgets';
    const method = id ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            alert('Company budget saved successfully!');
            clearCompanyForm();
            loadCompanyBudgets();
        } else {
            alert('Error saving company budget');
        }
    } catch (error) {
        console.error('Error saving company budget:', error);
    }
}

async function deleteCompanyBudget(id) {
    const role = (localStorage.getItem('coffee_user_role') || '').toLowerCase();
    if (role !== 'admin') return alert('Only Admin can delete company budgets.');
    if (!confirm('Are you sure you want to delete this company budget?')) return;

    try {
        const response = await fetch(`http://127.0.0.1:8000/api/company_budgets/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            alert('Company budget deleted successfully!');
            loadCompanyBudgets();
        } else {
            alert('Error deleting company budget');
        }
    } catch (error) {
        console.error('Error deleting company budget:', error);
    }
}

function editCompanyBudget(id, month, amount) {
    const role = (localStorage.getItem('coffee_user_role') || '').toLowerCase();
    if (role !== 'admin') return alert('Only Admin can edit company budgets.');

    document.getElementById('company_budget_id').value = id;
    document.getElementById('company_budget_month').value = month;
    document.getElementById('company_budget_amount').value = amount;
    document.getElementById('company-form-title').innerText = 'Edit Company Budget';
    document.getElementById('btn-cancel-edit-company').style.display = 'inline-block';
}

function clearCompanyForm() {
    document.getElementById('company_budget_id').value = '';
    document.getElementById('company_budget_month').value = '';
    document.getElementById('company_budget_amount').value = '';
    document.getElementById('company-form-title').innerText = 'Add Company Budget';
    document.getElementById('btn-cancel-edit-company').style.display = 'none';
}

// Initialize the page
function initCompanyBudgetPage() {
    const today = new Date();
    const monthStr = today.toISOString().slice(0, 7);
    
    const filterInput = document.getElementById('company_month_filter');
    const formMonthInput = document.getElementById('company_budget_month');

    if (filterInput && !filterInput.value) {
        filterInput.value = monthStr;
    }
    if (formMonthInput && !formMonthInput.value) {
        formMonthInput.value = monthStr;
    }

    loadCompanyBudgets();
}

// Call init when page loads (only for overall_budget.html)
if (window.location.pathname.includes('overall_budget.html')) {
    document.addEventListener('DOMContentLoaded', initCompanyBudgetPage);
}