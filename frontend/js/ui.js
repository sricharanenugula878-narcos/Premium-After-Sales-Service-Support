class UI {
    static showToast(message, type = 'success') {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;

        container.appendChild(toast);

        // Animate in
        setTimeout(() => toast.classList.add('show'), 10);

        // Remove after 3 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    static openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('show');
        }
    }

    static closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('show');
        }
    }

    static setupModals() {
        // Setup close buttons
        document.querySelectorAll('[data-close-modal]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modalId = e.target.closest('.modal-backdrop').id;
                this.closeModal(modalId);
            });
        });
    }

    static getStatusBadge(status) {
        const statusMap = {
            'New': 'badge-new',
            'Assigned': 'badge-assigned',
            'In Progress': 'badge-inprogress',
            'Completed': 'badge-completed',
            'Rejected': 'badge-rejected'
        };
        const className = statusMap[status] || '';
        return `<span class="badge ${className}">${status}</span>`;
    }
    
    static formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleDateString();
    }

    static initTheme() {
        const theme = localStorage.getItem('theme') || 'light';
        if (theme === 'dark') {
            document.body.classList.add('dark-theme');
        } else {
            document.body.classList.remove('dark-theme');
        }
        
        const toggleBtn = document.getElementById('themeToggleBtn');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => {
                this.toggleTheme();
            });
        }

        const notifBtn = document.getElementById('notificationBtn');
        if (notifBtn) {
            notifBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleNotifications();
            });
        }

        document.addEventListener('click', (e) => {
            const dropdown = document.getElementById('notificationDropdown');
            if (dropdown && dropdown.classList.contains('show')) {
                if (!e.target.closest('.notification-bell-container')) {
                    dropdown.classList.remove('show');
                }
            }
        });

        this.loadNotifications();
    }

    static toggleTheme() {
        const isDark = document.body.classList.toggle('dark-theme');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
    }

    static toggleNotifications() {
        const dropdown = document.getElementById('notificationDropdown');
        if (dropdown) {
            dropdown.classList.toggle('show');
        }
    }

    static loadNotifications() {
        const body = document.getElementById('notificationDropdownBody');
        if (!body) return;

        const mockNotifications = [
            { id: 1, text: "Technician assigned to Ticket #1004 (Loose fitting cabinet)", time: "10m ago", unread: true },
            { id: 2, text: "Warranty verified for Premium Sofa purchased by Customer #3", time: "1h ago", unread: true },
            { id: 3, text: "New complaint ticket raised by Sri Venkata Furniture client", time: "4h ago", unread: false },
            { id: 4, text: "Monthly resolution analytics report is now ready for view", time: "1d ago", unread: false }
        ];

        body.innerHTML = mockNotifications.map(n => `
            <div class="notification-dropdown-item ${n.unread ? 'unread' : ''}">
                <div>${n.text}</div>
                <span class="notif-time">${n.time}</span>
            </div>
        `).join('');
    }
}

// Automatically check and apply theme on DOM load
document.addEventListener('DOMContentLoaded', () => {
    // Add brief inline check first to avoid screen flash
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
    }
    UI.initTheme();
});

