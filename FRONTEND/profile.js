/**
 * @file profile.js — OptiRate User Settings Modal Controller
 *
 * Controls the profile/settings modal that appears across authenticated pages:
 *  - Opens when the user clicks the profile icon; closes on button, overlay
 *    click, or Escape key.
 *  - Fetches user data from two endpoints (/me for role, /auth/profile for
 *    editable fields) and populates the form.
 *  - Displays the correct plan badge (Free / 💎 Premium / 🛡️ Admin) and
 *    conditionally shows or hides the "Upgrade" button.
 *  - Allows the user to update their display name via PATCH /auth/update-profile.
 *  - Injects an "Admin Dashboard" button into the navbar for admin users.
 *  - Handles logout by calling POST /auth/logout, then clearing all local
 *    storage and redirecting to the landing page.
 */
document.addEventListener('DOMContentLoaded', async () => {
    const profileModal = document.getElementById('profile-modal');
    if (!profileModal) return; // Modal not present on this page

    const userProfileIcon = document.querySelector('.user-profile');
    const closeModalBtn = document.getElementById('close-modal-btn');

    // --- Admin Dashboard Button Injection ---
    // If the current user is an admin, dynamically inject an "Admin Dashboard"
    // link into the navigation bar.
    try {
        await window.syncCurrentUser?.();
    } catch (e) {}
    const sessionUser = window.getSessionUser?.();
    if (sessionUser && sessionUser.role === 'admin') {
        const navActions = document.querySelector('.nav-actions');
        if (navActions && !document.getElementById('admin-btn')) {
            const adminBtn = document.createElement('a');
            adminBtn.href = 'admin.html';
            adminBtn.className = 'btn btn-primary btn-sm';
            adminBtn.id = 'admin-btn';
            adminBtn.style.marginRight = '15px';
            adminBtn.textContent = 'Admin Dashboard';
            navActions.insertBefore(adminBtn, navActions.firstChild);
        }
    }

    // --- Profile Form DOM References ---
    const profileNameInput = document.getElementById('profile-name-input');
    const profileEmailInput = document.getElementById('profile-email-input');
    const profilePlanBadge = document.getElementById('profile-plan-badge');
    const updateNameBtn = document.getElementById('update-name-btn');
    const upgradePlanBtn = document.getElementById('upgrade-plan-btn');
    const toast = document.getElementById('toast-notification');

    // --- Open Modal ---
    // Clicking the profile icon opens the modal and fetches the latest data.
    if (userProfileIcon) {
        userProfileIcon.addEventListener('click', async () => {
            profileModal.classList.remove('hidden');
            await fetchProfile();
        });
    }

    // --- Close Modal (button) ---
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => {
            profileModal.classList.add('hidden');
        });
    }

    // --- Close Modal (click outside) ---
    profileModal.addEventListener('click', (e) => {
        if (e.target === profileModal) {
            profileModal.classList.add('hidden');
        }
    });

    /**
     * Fetches user profile data from two parallel endpoints:
     *  - /me: provides the user's role (free, premium, admin).
     *  - /auth/profile: provides editable fields (username, email).
     *
     * Updates the plan badge, upgrade button visibility, and form fields.
     * Shows a loading state on the "Update" button while requests are in-flight.
     * @async
     */
    const fetchProfile = async () => {
        const token = localStorage.getItem('access_token');
        if (!token) return;

        try {
            updateNameBtn.textContent = 'Loading...';
            updateNameBtn.disabled = true;

            // Fetch role info and profile data concurrently
            const [meRes, profileRes] = await Promise.all([
                fetch(`${API_BASE_URL}/me`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                }),
                fetch(`${API_BASE_URL}/auth/profile`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                })
            ]);

            // --- Plan Badge & Upgrade Button Logic ---
            if (meRes.ok) {
                const meData = await meRes.json();
                const me = meData.data;
                console.log("Role from API:", me.role);

                const isPremium = me.role === 'premium';
                const isAdmin = me.role === 'admin';

                if (isAdmin) {
                    profilePlanBadge.textContent = '🛡️ Admin';
                    profilePlanBadge.classList.add('premium');
                    upgradePlanBtn.classList.add('hidden');
                } else if (isPremium) {
                    profilePlanBadge.textContent = '💎 Premium';
                    profilePlanBadge.classList.add('premium');
                    upgradePlanBtn.classList.add('hidden');
                } else {
                    profilePlanBadge.textContent = 'Free';
                    profilePlanBadge.classList.remove('premium');
                    upgradePlanBtn.classList.remove('hidden');
                }
            }

            // --- Populate Editable Fields ---
            if (profileRes.ok) {
                const data = await profileRes.json();
                const user = data.data;
                profileNameInput.value = user.username;
                profileEmailInput.value = user.email;
            }
        } catch (error) {
            console.error('Failed to fetch profile', error);
        } finally {
            updateNameBtn.textContent = 'Update';
            updateNameBtn.disabled = false;
        }
    };

    // --- Name Update Handler ---
    // Sends the new username to the server and updates the UI on success,
    // including the navbar greeting and localStorage.
    if (updateNameBtn) {
        updateNameBtn.addEventListener('click', async () => {
            const token = localStorage.getItem('access_token');
            if (!token) return;

            const newName = profileNameInput.value.trim();
            if (!newName) return;

            try {
                updateNameBtn.textContent = 'Saving...';
                updateNameBtn.disabled = true;

                const res = await fetch(`${API_BASE_URL}/auth/update-profile`, {
                    method: 'PATCH',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ username: newName })
                });

                const data = await res.json();

                if (res.ok && data.status === 'success') {
                    // Update UI: update in navbar logic if it exists (some files might not have it or have it dynamically)
                    // The main dashboard has #user-name.
                    const userNameEl = document.getElementById('user-name');
                    if (userNameEl) {
                        userNameEl.textContent = data.data.username;
                    }
                    
                    // Update LocalStorage
                    localStorage.setItem('user', JSON.stringify(data.data));

                    // Show Toast — visible for 3 seconds, then fades out
                    toast.classList.remove('hidden');
                    toast.classList.add('show');
                    setTimeout(() => {
                        toast.classList.remove('show');
                        setTimeout(() => toast.classList.add('hidden'), 300);
                    }, 3000);
                } else {
                    alert(data.message || 'Failed to update profile');
                }
            } catch (error) {
                console.error('Failed to update profile', error);
                alert('An error occurred while updating profile.');
            } finally {
                updateNameBtn.textContent = 'Update';
                updateNameBtn.disabled = false;
            }
        });
    }

    // Upgrade button is now handled by payment.js (Phase 3.3)

    // --- Logo Navigation ---
    // Same pattern as script.js: redirect based on auth state.
    const logoElements = document.querySelectorAll('.logo');
    logoElements.forEach(logo => {
        logo.style.cursor = 'pointer';
        logo.addEventListener('click', () => {
            const token = localStorage.getItem('access_token');
            if (token) {
                window.location.href = 'dashboard.html';
            } else {
                window.location.href = 'index.html';
            }
        });
    });

    // --- Logout Logic ---
    // Handles both the modal logout button and the navbar logout button.
    // Sends a POST to /auth/logout to invalidate the token server-side,
    // then clears all client-side storage and redirects to the landing page.
    const logoutBtns = document.querySelectorAll('#modal-logout-btn, #navbar-logout-btn');
    logoutBtns.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const token = localStorage.getItem('access_token');
            
            // Visual feedback
            toast.textContent = 'Logging out...';
            toast.classList.remove('hidden');
            toast.classList.add('show');

            // Attempt server-side token invalidation (best-effort)
            if (token) {
                try {
                    await fetch(`${API_BASE_URL}/auth/logout`, {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                } catch(e) {
                    console.log('Backend logout failed', e);
                }
            }
            
            // Brief delay so the user sees "Logging out…" before redirect
            setTimeout(() => {
                localStorage.removeItem('access_token');
                localStorage.removeItem('user');
                sessionStorage.clear();
                window.location.replace('index.html');
            }, 500);
        });
    });
});
