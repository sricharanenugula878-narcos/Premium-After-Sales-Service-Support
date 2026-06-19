document.addEventListener('DOMContentLoaded', async () => {
    // Check if already logged in
    const user = await Auth.checkSession();
    if (user) {
        Auth.redirectToRoleDashboard(user);
        return;
    }

    const form = document.getElementById('loginForm');
    const errorDiv = document.getElementById('loginError');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;
        const submitBtn = form.querySelector('button[type="submit"]');

        try {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Signing in...';
            errorDiv.style.display = 'none';

            const data = await Auth.login(username, password);
            Auth.redirectToRoleDashboard(data.user);
        } catch (error) {
            errorDiv.textContent = error.message || 'Login failed. Please try again.';
            errorDiv.style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Sign In';
        }
    });
});
