let allCustomers = [];

document.addEventListener('DOMContentLoaded', async () => {
    const user = await Auth.checkSession();
    if (!user) return;

    Auth.setupLogoutButton();
    Auth.updateUserInfo();
    UI.setupModals();

    loadCustomers();

    // Search functionality
    document.getElementById('searchInput').addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        const filtered = allCustomers.filter(c => 
            c.full_name.toLowerCase().includes(term) ||
            c.customer_code.toLowerCase().includes(term) ||
            c.phone.includes(term)
        );
        renderTable(filtered);
    });

    // Form submission
    document.getElementById('customerForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('customerId').value;
        const payload = {
            full_name: document.getElementById('fullName').value,
            phone: document.getElementById('phone').value,
            email: document.getElementById('email').value,
            address: document.getElementById('address').value
        };

        try {
            if (id) {
                await API.put(`/customers/${id}`, payload);
                UI.showToast('Customer updated successfully');
            } else {
                await API.post('/customers', payload);
                UI.showToast('Customer created successfully');
            }
            UI.closeModal('customerModal');
            document.getElementById('customerForm').reset();
            loadCustomers();
        } catch (error) {
            UI.showToast(error.message, 'error');
        }
    });
});

async function loadCustomers() {
    try {
        allCustomers = await API.get('/customers');
        renderTable(allCustomers);
    } catch (error) {
        UI.showToast('Failed to load customers', 'error');
    }
}

function renderTable(data) {
    const tbody = document.querySelector('#customersTable tbody');
    tbody.innerHTML = '';
    
    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No customers found</td></tr>';
        return;
    }

    data.forEach(customer => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${customer.customer_code}</td>
            <td>${customer.full_name}</td>
            <td>${customer.phone}</td>
            <td>${customer.email || '-'}</td>
            <td>${customer.address || '-'}</td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick='editCustomer(${JSON.stringify(customer).replace(/'/g, "&apos;")})'>Edit</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function editCustomer(customer) {
    document.getElementById('modalTitle').textContent = 'Edit Customer';
    document.getElementById('customerId').value = customer.id;
    document.getElementById('fullName').value = customer.full_name;
    document.getElementById('phone').value = customer.phone;
    document.getElementById('email').value = customer.email || '';
    document.getElementById('address').value = customer.address || '';
    UI.openModal('customerModal');
}

// Reset form when modal is closed
document.querySelectorAll('[data-close-modal]').forEach(btn => {
    btn.addEventListener('click', () => {
        setTimeout(() => {
            document.getElementById('customerForm').reset();
            document.getElementById('customerId').value = '';
            document.getElementById('modalTitle').textContent = 'Add Customer';
        }, 300);
    });
});
