/**
 * @file api.js — OptiRate API Configuration & Session Management
 *
 * Central configuration module shared across the entire frontend.
 * Provides:
 *  - API_BASE_URL: The root URL prefix for all backend API requests.
 *  - syncCurrentUser(): Fetches the authenticated user from the server and
 *    stores the result in both an in-memory singleton and browser storage.
 *  - getSessionUser(): Returns the cached user object without a network call.
 *
 * Every page-level script (dashboard.js, bank-rates.js, etc.) depends on
 * API_BASE_URL and uses syncCurrentUser / getSessionUser for role-based logic.
 */

/**
 * Base URL prefix for all API requests.
 * Uses a relative path so the browser resolves it against the current origin,
 * making the app work seamlessly behind a reverse proxy or in production.
 * @constant {string}
 */
const API_BASE_URL = '/api';

/**
 * Global in-memory session object.
 * Shared across all scripts on the same page to avoid redundant API calls.
 * Initialized lazily — `user` is null until syncCurrentUser() succeeds.
 * @type {{ user: Object|null }}
 */
window.OptiRateSession = window.OptiRateSession || { user: null };

/**
 * Fetches the currently authenticated user from the backend `/me` endpoint
 * and synchronizes the result into three locations:
 *  1. window.OptiRateSession.user  (in-memory, fastest reads)
 *  2. sessionStorage 'session_user' (survives soft navigations)
 *  3. localStorage 'user'          (survives full page reloads)
 *
 * If the token is missing or the server returns 401 (expired/invalid),
 * all stored credentials are cleared and null is returned.
 *
 * @async
 * @returns {Promise<Object|null>} The user data object on success, or null.
 */
async function syncCurrentUser() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.OptiRateSession.user = null;
        return null;
    }

    const res = await fetch(`${API_BASE_URL}/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });

    // Token is expired or revoked — clear everything
    if (res.status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        window.OptiRateSession.user = null;
        return null;
    }

    const payload = await res.json();
    if (!res.ok || payload.status !== 'success' || !payload.data) {
        return null;
    }

    console.log("Role from API:", payload.data.role);
    window.OptiRateSession.user = payload.data;
    sessionStorage.setItem('session_user', JSON.stringify(payload.data));
    localStorage.setItem('user', JSON.stringify(payload.data));
    return payload.data;
}

/**
 * Returns the cached user object without making a network request.
 * Checks the in-memory singleton first, then falls back to sessionStorage.
 * Returns null if neither source contains valid user data.
 *
 * @returns {Object|null} The cached user data, or null if unavailable.
 */
function getSessionUser() {
    if (window.OptiRateSession.user) return window.OptiRateSession.user;
    const raw = sessionStorage.getItem('session_user');
    if (!raw) return null;
    try {
        const parsed = JSON.parse(raw);
        window.OptiRateSession.user = parsed;
        return parsed;
    } catch (e) {
        return null;
    }
}

// Export for ES modules or attach to window for standard scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { API_BASE_URL, syncCurrentUser, getSessionUser };
} else {
    window.API_BASE_URL = API_BASE_URL;
    window.syncCurrentUser = syncCurrentUser;
    window.getSessionUser = getSessionUser;
}
