let allTechs = [];

document.addEventListener('DOMContentLoaded', async () => {
    const user = await Auth.checkSession();
    if (!user) return;
    Auth.requireRole(['admin']);
    Auth.setupLogoutButton();
    Auth.updateUserInfo();
    UI.setupModals();

    loadTechs();

    document.getElementById('searchInput').addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        const filtered = allTechs.filter(t => 
            t.name.toLowerCase().includes(term) ||
            t.technician_code.toLowerCase().includes(term) ||
            (t.skills && t.skills.toLowerCase().includes(term))
        );
        renderTable(filtered);
    });

    document.getElementById('techForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('techId').value;
        const payload = {
            name: document.getElementById('techName').value.trim(),
            email: document.getElementById('techEmail').value.trim(),
            phone: document.getElementById('techPhone').value.trim(),
            skills: document.getElementById('techSpec').value.trim(), // Maps spec to skills in database
            availability_status: document.getElementById('techStatus').value
        };

        try {
            if (id) {
                await API.put(`/technicians/${id}`, payload);
                alert('Technician updated successfully');
            } else {
                const res = await API.post('/technicians', payload);
                alert(`Technician created successfully!\n\nUser Profile:\nUsername: ${res.default_credentials.username}\nPassword: ${res.default_credentials.password}`);
            }
            UI.closeModal('techModal');
            document.getElementById('techForm').reset();
            loadTechs();
        } catch (error) {
            alert('Failed to save technician: ' + error.message);
        }
    });
});

async function loadTechs() {
    try {
        allTechs = await API.get('/technicians');
        renderTable(allTechs);
    } catch (error) {
        console.error(error);
        alert('Failed to load technicians');
    }
}

function renderTable(data) {
    const tbody = document.querySelector('#techTable tbody');
    tbody.innerHTML = '';
    
    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No technicians found</td></tr>';
        return;
    }

    data.forEach(tech => {
        const statusClass = tech.availability_status === 'Available' ? 'badge-completed' : 
                            (tech.availability_status === 'On Job' ? 'badge-inprogress' : 'badge-rejected');
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${tech.technician_code}</td>
            <td>${tech.name}</td>
            <td>${tech.phone}</td>
            <td>${tech.skills || '-'}</td>
            <td><span class="badge ${statusClass}">${tech.availability_status}</span></td>
            <td>
                <button class="btn btn-sm btn-secondary" onclick='editTech(${JSON.stringify(tech).replace(/'/g, "&apos;")})'>Edit</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function editTech(tech) {
    document.getElementById('modalTitle').textContent = 'Edit Technician';
    document.getElementById('techId').value = tech.id;
    document.getElementById('techName').value = tech.name;
    document.getElementById('techEmail').value = tech.email || '';
    document.getElementById('techPhone').value = tech.phone;
    document.getElementById('techSpec').value = tech.skills || '';
    document.getElementById('techStatus').value = tech.availability_status;
    UI.openModal('techModal');
}

document.querySelectorAll('[data-close-modal]').forEach(btn => {
    btn.addEventListener('click', () => {
        setTimeout(() => {
            document.getElementById('techForm').reset();
            document.getElementById('techId').value = '';
            document.getElementById('modalTitle').textContent = 'Add Technician';
        }, 300);
    });
});
