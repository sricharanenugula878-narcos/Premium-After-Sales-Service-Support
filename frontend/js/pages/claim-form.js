document.addEventListener('DOMContentLoaded', async () => {
    const user = await Auth.checkSession();
    if (!user) return;
    Auth.requireRole(['admin']);
    Auth.setupLogoutButton();
    Auth.updateUserInfo();

    await loadDropdowns();

    // Check if editing
    const urlParams = new URLSearchParams(window.location.search);
    const ticketId = urlParams.get('id');

    if (ticketId) {
        document.getElementById('pageTitle').textContent = 'Edit Ticket';
        loadTicketDetails(ticketId);
    }

    document.getElementById('claimForm').addEventListener('submit', handleFormSubmit);
});

async function loadDropdowns() {
    try {
        const [customers, technicians] = await Promise.all([
            API.get('/customers'),
            API.get('/technicians')
        ]);

        const custSelect = document.getElementById('customerId');
        customers.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = `${c.customer_code} - ${c.full_name}`;
            custSelect.appendChild(opt);
        });

        const techSelect = document.getElementById('technicianId');
        technicians.forEach(t => {
            const opt = document.createElement('option');
            opt.value = t.id;
            opt.textContent = `${t.name} (${t.skills || 'General'})`;
            techSelect.appendChild(opt);
        });
    } catch (error) {
        console.error(error);
        alert('Failed to load dropdown listings');
    }
}

async function loadTicketDetails(id) {
    try {
        const ticket = await API.get(`/tickets/${id}`);
        
        document.getElementById('claimId').value = ticket.id;
        document.getElementById('customerId').value = ticket.customer_id;
        document.getElementById('customerId').disabled = true; // Cannot transfer ticket to another customer
        
        document.getElementById('productName').value = ticket.product_name || '';
        document.getElementById('furnitureType').value = ticket.category || '';
        document.getElementById('purchaseDate').value = ticket.purchase_date || '';
        document.getElementById('warrantyExpiry').value = ticket.warranty_end_date || '';
        
        document.getElementById('complaintType').value = ticket.issue_type;
        document.getElementById('priority').value = ticket.priority;
        document.getElementById('description').value = ticket.description;
        
        // Load active technician assignment
        if (ticket.assignments && ticket.assignments.length > 0) {
            const activeAssign = ticket.assignments[0];
            if (activeAssign.status === 'Accepted' || activeAssign.status === 'Pending') {
                document.getElementById('technicianId').value = activeAssign.technician_id;
            }
        }

    } catch (error) {
        console.error(error);
        alert('Failed to load ticket details');
        setTimeout(() => window.location.href = 'claims.html', 2000);
    }
}

async function handleFormSubmit(e) {
    e.preventDefault();
    
    const id = document.getElementById('claimId').value;
    const payload = {
        customer_id: document.getElementById('customerId').value,
        product_name: document.getElementById('productName').value.trim() || null,
        furniture_type: document.getElementById('furnitureType').value.trim() || null,
        purchase_date: document.getElementById('purchaseDate').value || null,
        warranty_expiry_date: document.getElementById('warrantyExpiry').value || null,
        complaint_type: document.getElementById('complaintType').value,
        priority: document.getElementById('priority').value,
        description: document.getElementById('description').value.trim(),
        technician_id: document.getElementById('technicianId').value ? parseInt(document.getElementById('technicianId').value) : null
    };

    try {
        if (id) {
            await API.put(`/tickets/${id}`, payload);
            alert('Ticket updated successfully');
        } else {
            const res = await API.post('/tickets', payload);
            alert(`Ticket ${res.ticket_id} created successfully`);
        }
        
        window.location.href = 'claims.html';
    } catch (error) {
        alert('Failed to submit form: ' + error.message);
    }
}
