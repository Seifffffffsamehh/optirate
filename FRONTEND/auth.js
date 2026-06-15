/**
 * @file auth.js — OptiRate Authentication Page Controller
 *
 * Manages the Login / Register dual-view on auth.html:
 *  - Tab switching between Login and Sign-Up views, synchronized with the
 *    URL hash (#login / #signup) and the document title.
 *  - Login form submission: authenticates via POST /api/auth/login, stores
 *    the JWT access token and user object in localStorage, then redirects
 *    to the dashboard.
 *  - Registration form submission: registers a new "free" user via
 *    POST /api/auth/register. On success, auto-fills the login form with
 *    the new credentials so the user can log in immediately.
 *  - Inline error display for both forms (network errors and API errors).
 */
document.addEventListener('DOMContentLoaded', () => {

    // --- DOM references for the two auth views ---
    const loginView = document.getElementById('view-login');
    const signupView = document.getElementById('view-signup');
    
    // Navigation buttons that toggle between the login and signup views
    const btnToSignup = document.getElementById('nav-to-signup');
    const btnToLogin = document.getElementById('nav-to-login');

    // Form elements
    const loginForm = document.getElementById('login-form');
    const signupForm = document.getElementById('signup-form');

    // Error message containers displayed below each form
    const loginError = document.getElementById('login-error');
    const signupError = document.getElementById('signup-error');

    /**
     * Toggles visibility between the Login and Sign-Up views.
     * Also updates the URL hash and document title so the browser's
     * back/forward buttons and bookmarks work as expected.
     *
     * @param {boolean} showSignup - If true, show the Sign-Up view;
     *                               if false, show the Login view.
     */
    const switchView = (showSignup) => {
        if(showSignup) {
            loginView.classList.add('hidden');
            signupView.classList.remove('hidden');
            window.location.hash = 'signup';
            document.title = 'Sign Up | OptiRate';
        } else {
            signupView.classList.add('hidden');
            loginView.classList.remove('hidden');
            window.location.hash = 'login';
            document.title = 'Login | OptiRate';
        }
    };

    // On initial page load, check the URL hash to determine which view to show.
    // This allows direct links like auth.html#signup to work correctly.
    if(window.location.hash === '#signup') {
        switchView(true);
    }

    // --- Tab switch button event listeners ---
    if(btnToSignup) {
        btnToSignup.addEventListener('click', (e) => {
            e.preventDefault();
            switchView(true);
        });
    }

    if(btnToLogin) {
        btnToLogin.addEventListener('click', (e) => {
            e.preventDefault();
            switchView(false);
        });
    }

    // --- Login Form Submission ---
    // Sends username/email + password to the backend. On success, persists the
    // JWT token and user object in localStorage and redirects to the dashboard.
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            loginError.classList.add('hidden');
            
            // The identifier field accepts either a username or an email address
            const identifier = document.getElementById('login-email').value;
            const password = document.getElementById('login-password').value;
            
            try {
                const response = await fetch(`${API_BASE_URL}/auth/login`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    // Backend accepts both 'username' and 'email' — send both
                    // so the server can match on whichever the user provided.
                    body: JSON.stringify({ username: identifier, email: identifier, password })
                });
                
                const data = await response.json();
                
                if (response.ok && data.status === 'success') {
                    // Persist auth credentials for subsequent authenticated requests
                    localStorage.setItem('access_token', data.data.access_token);
                    localStorage.setItem('user', JSON.stringify(data.data.user));
                    window.location.href = 'dashboard.html';
                } else {
                    loginError.textContent = data.message || 'Login failed';
                    loginError.classList.remove('hidden');
                }
            } catch (err) {
                loginError.textContent = 'Network error occurred. Please try again.';
                loginError.classList.remove('hidden');
            }
        });
    }

    // --- Registration Form Submission ---
    // Creates a new user with the "free" role. On success, switches to the
    // login view and auto-fills the credentials for a seamless experience.
    if (signupForm) {
        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            signupError.classList.add('hidden');
            
            const username = document.getElementById('signup-username').value;
            const email = document.getElementById('signup-email').value;
            const password = document.getElementById('signup-password').value;
            
            try {
                const response = await fetch(`${API_BASE_URL}/auth/register`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    // New users default to the 'free' plan
                    body: JSON.stringify({ username, email, password, role: 'free' })
                });
                
                const data = await response.json();
                
                if (response.ok && data.status === 'success') {
                    // Auto-login after successful register or redirect to login
                    switchView(false);
                    document.getElementById('login-email').value = email;
                    document.getElementById('login-password').value = password;
                    loginError.textContent = 'Registration successful. Please log in.';
                    loginError.style.color = 'green';
                    loginError.classList.remove('hidden');
                } else {
                    signupError.textContent = data.message || 'Registration failed';
                    signupError.classList.remove('hidden');
                }
            } catch (err) {
                signupError.textContent = 'Network error occurred. Please try again.';
                signupError.classList.remove('hidden');
            }
        });
    }
});
