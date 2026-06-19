document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('registerForm');
    const errorDiv = document.getElementById('registerError');
    const successDiv = document.getElementById('registerSuccess');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const username = document.getElementById('username').value.trim();
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;
        const fullName = document.getElementById('fullName').value.trim();
        const phone = document.getElementById('phone').value.trim();
        const address = document.getElementById('address').value.trim();
        const city = document.getElementById('city').value.trim();
        const state = document.getElementById('state').value.trim();
        const pincode = document.getElementById('pincode').value.trim();
        
        const submitBtn = form.querySelector('button[type="submit"]');

        try {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Creating account...';
            errorDiv.style.display = 'none';
            successDiv.style.display = 'none';

            await API.post('/register', {
                username,
                email,
                password,
                full_name: fullName,
                phone,
                address,
                city,
                state,
                pincode
            });

            successDiv.textContent = 'Account created successfully! Redirecting to login page...';
            successDiv.style.display = 'block';
            form.reset();

            setTimeout(() => {
                window.location.href = 'index.html';
            }, 2000);
        } catch (error) {
            errorDiv.textContent = error.message || 'Registration failed. Please check your inputs.';
            errorDiv.style.display = 'block';
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Create Account';
        }
    });
});
