/**
 * LJV Engine Authentication API Handler
 * Handles all auth-related API calls with environment-aware configuration
 */

class AuthAPI {
    constructor() {
        // Detect API base URL
        this.apiBaseURL = this.getAPIBaseURL();
        this.sessionKey = 'ljv_session_id';
        this.userKey = 'ljv_user_email';
        this.tokenKey = 'ljv_auth_token';
    }

    /**
     * Get API base URL based on environment
     */
    getAPIBaseURL() {
        // In development
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            return 'http://127.0.0.1:8787';
        }
        
        // In production (Vercel or self-hosted)
        // Use the same origin as the current page
        return `${window.location.protocol}//${window.location.host}`;
    }

    /**
     * Get auth headers
     */
    getAuthHeaders(includeAuth = true) {
        const headers = {
            'Content-Type': 'application/json',
        };

        if (includeAuth) {
            const token = localStorage.getItem(this.tokenKey);
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
        }

        return headers;
    }

    /**
     * Make API request
     */
    async request(endpoint, method = 'GET', body = null, includeAuth = true) {
        const url = `${this.apiBaseURL}${endpoint}`;
        const options = {
            method,
            headers: this.getAuthHeaders(includeAuth),
        };

        if (body) {
            options.body = JSON.stringify(body);
        }

        try {
            const response = await fetch(url, options);

            // Handle unauthorized
            if (response.status === 401) {
                this.clearSession();
                window.location.href = '/login.html';
                throw new Error('Session expired. Please login again.');
            }

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || `API Error: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    }

    /**
     * Login with email and password
     */
    async login(email, password) {
        const data = await this.request('/auth/login', 'POST', { email, password }, false);
        this.setSession(data.session_id, email, data.access_token);
        return data;
    }

    /**
     * Sign up with email and password
     */
    async signup(email, password) {
        const data = await this.request('/auth/signup', 'POST', { email, password }, false);
        this.setSession(data.session_id, email, data.access_token);
        return data;
    }

    /**
     * Log out
     */
    async logout() {
        try {
            await this.request('/auth/logout', 'POST', {});
        } catch (error) {
            console.warn('Logout API call failed:', error);
        }
        this.clearSession();
    }

    /**
     * Check current session status
     */
    async checkStatus() {
        try {
            const data = await this.request('/auth/status', 'GET');
            return data;
        } catch (error) {
            return null;
        }
    }

    /**
     * Request password reset
     */
    async requestPasswordReset(email) {
        return this.request('/auth/request-password-reset', 'POST', { email }, false);
    }

    /**
     * Reset password with token
     */
    async resetPassword(token, newPassword) {
        return this.request('/auth/reset-password', 'POST', { token, new_password: newPassword }, false);
    }

    /**
     * Re-authenticate for sensitive operations
     */
    async reauthenticate(password) {
        return this.request('/auth/reauth', 'POST', { password }, true);
    }

    /**
     * Get current user info
     */
    getCurrentUser() {
        return {
            email: localStorage.getItem(this.userKey),
            isAuthenticated: !!localStorage.getItem(this.tokenKey),
        };
    }

    /**
     * Set session data
     */
    setSession(sessionId, email, token) {
        localStorage.setItem(this.sessionKey, sessionId);
        localStorage.setItem(this.userKey, email);
        localStorage.setItem(this.tokenKey, token);
    }

    /**
     * Clear session data
     */
    clearSession() {
        localStorage.removeItem(this.sessionKey);
        localStorage.removeItem(this.userKey);
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem('ljv_remember_email');
    }

    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        return !!localStorage.getItem(this.tokenKey);
    }
}

// Export for use
const authAPI = new AuthAPI();
