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
            <td>$${parseFloat(budget.amount).toLocaleString()}</td>
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
    document.getElementById('overall_budget_month').value = month;
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
    document.getElementById('overall_budget_month').value = '';
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
    const today = new Date();
    const monthStr = today.toISOString().slice(0, 7);
    
    const filterInput = document.getElementById('overall_month_filter');
    const formMonthInput = document.getElementById('overall_budget_month');

    if (filterInput && !filterInput.value) {
        filterInput.value = monthStr;
    }
    if (formMonthInput && !formMonthInput.value) {
        formMonthInput.value = monthStr;
    }

    loadOverallBudgets();
});