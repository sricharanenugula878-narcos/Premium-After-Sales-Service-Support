let allTickets = [];

document.addEventListener('DOMContentLoaded', async () => {
    const user = await Auth.checkSession();
    if (!user) return;
    Auth.requireRole(['admin']);
    Auth.setupLogoutButton();
    Auth.updateUserInfo();

    loadTickets();

    // Filters
    document.getElementById('searchInput').addEventListener('input', applyFilters);
    document.getElementById('statusFilter').addEventListener('change', applyFilters);
});

async function loadTickets() {
    try {
        allTickets = await API.get('/tickets');
        renderTable(allTickets);
    } catch (error) {
        console.error(error);
        alert('Failed to load tickets');
    }
}

function applyFilters() {
    const term = document.getElementById('searchInput').value.toLowerCase();
    const status = document.getElementById('statusFilter').value;

    const filtered = allTickets.filter(t => {
        const matchesTerm = t.ticket_id.toLowerCase().includes(term) ||
                            (t.customer_name && t.customer_name.toLowerCase().includes(term)) ||
                            (t.product_name && t.product_name.toLowerCase().includes(term)) ||
                            t.issue_type.toLowerCase().includes(term);
        const matchesStatus = status === '' || t.status === status;
        
        return matchesTerm && matchesStatus;
    });

    renderTable(filtered);
}

function renderTable(data) {
    const tbody = document.querySelector('#claimsTable tbody');
    tbody.innerHTML = '';
    
    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center">No tickets found</td></tr>';
        return;
    }

    data.forEach(ticket => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${ticket.ticket_id}</strong></td>
            <td>${ticket.customer_name || '-'}</td>
            <td>${ticket.product_name || 'General Complaint'}</td>
            <td>${ticket.issue_type}</td>
            <td><span class="priority-${ticket.priority.toLowerCase()}">${ticket.priority}</span></td>
            <td>${ticket.technician_name || '<span class="text-muted">Unassigned</span>'}</td>
            <td><span class="badge badge-${ticket.status.replace(/\s+/g, '').toLowerCase()}">${ticket.status}</span></td>
            <td>
                <div class="d-flex gap-2">
                    <a href="claim-details.html?id=${ticket.id}" class="btn btn-sm btn-secondary">View</a>
                    <a href="claim-form.html?id=${ticket.id}" class="btn btn-sm btn-primary">Manage</a>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}
