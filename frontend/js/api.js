const API_BASE_URL = '/api';

class API {
    static async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json'
            }
        };

        // Inject JWT bearer token if exists
        const token = localStorage.getItem('token');
        if (token) {
            defaultOptions.headers['Authorization'] = `Bearer ${token}`;
        }

        const config = { ...defaultOptions, ...options };
        if (options.headers) {
            config.headers = { ...defaultOptions.headers, ...options.headers };
        }
        
        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }

        try {
            const response = await fetch(url, config);
            
            // Handle 401 Unauthorized globally
            if (response.status === 401 && endpoint !== '/login') {
                localStorage.removeItem('token');
                localStorage.removeItem('user');
                const isLoginPage = window.location.pathname.endsWith('index.html') || 
                                    window.location.pathname === '/' || 
                                    window.location.pathname === '' || 
                                    window.location.pathname.endsWith('register.html');
                if (!isLoginPage) {
                    window.location.href = '/index.html';
                }
                return null;
            }

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'API Request Failed');
            }
            
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    static get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }

    static post(endpoint, data) {
        return this.request(endpoint, { method: 'POST', body: data });
    }

    static put(endpoint, data) {
        return this.request(endpoint, { method: 'PUT', body: data });
    }
    
    static patch(endpoint, data) {
        return this.request(endpoint, { method: 'PATCH', body: data });
    }

    static delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }
}
