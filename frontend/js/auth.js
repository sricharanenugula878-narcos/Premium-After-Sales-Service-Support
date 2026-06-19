class Auth {
    static async checkSession() {
        const token = localStorage.getItem('token');
        const isLoginPage = window.location.pathname.endsWith('index.html') || 
                            window.location.pathname === '/' || 
                            window.location.pathname === '' || 
                            window.location.pathname.endsWith('register.html');

        if (!token) {
            if (!isLoginPage) {
                window.location.href = '/index.html';
            }
            return null;
        }

        try {
            const user = await API.get('/me');
            if (user) {
                localStorage.setItem('user', JSON.stringify(user));
                return user;
            }
        } catch (error) {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            if (!isLoginPage) {
                window.location.href = '/index.html';
            }
        }
        return null;
    }

    static async login(username, password) {
        try {
            const data = await API.post('/login', { username, password });
            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify(data.user));
            return data;
        } catch (error) {
            throw error;
        }
    }

    static async logout() {
        try {
            await API.post('/logout');
        } catch (e) {
            console.error(e);
        } finally {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = '/index.html';
        }
    }

    static getCurrentUser() {
        const userStr = localStorage.getItem('user');
        if (userStr) {
            try {
                return JSON.parse(userStr);
            } catch (e) {
                return null;
            }
        }
        return null;
    }

    static requireAdmin() {
        const user = this.getCurrentUser();
        if (!user || user.role !== 'admin') {
            this.redirectToRoleDashboard(user);
        }
    }

    static requireRole(allowedRoles) {
        const user = this.getCurrentUser();
        if (!user || !allowedRoles.includes(user.role)) {
            this.redirectToRoleDashboard(user);
        }
    }

    static redirectToRoleDashboard(user) {
        if (!user) {
            window.location.href = '/index.html';
            return;
        }
        if (user.role === 'admin') {
            window.location.href = '/dashboard.html';
        } else if (user.role === 'technician') {
            window.location.href = '/technician-dashboard.html';
        } else if (user.role === 'customer') {
            window.location.href = '/customer-dashboard.html';
        } else {
            window.location.href = '/index.html';
        }
    }
    
    static setupLogoutButton() {
        const btn = document.getElementById('logoutBtn');
        if (btn) {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.logout();
            });
        }
    }
    
    static updateUserInfo() {
        const user = this.getCurrentUser();
        if (user) {
            const nameEl = document.getElementById('currentUserName');
            const roleEl = document.getElementById('currentUserRole');
            if (nameEl) nameEl.textContent = user.username;
            if (roleEl) roleEl.textContent = user.role.charAt(0).toUpperCase() + user.role.slice(1);
        }
    }
}
