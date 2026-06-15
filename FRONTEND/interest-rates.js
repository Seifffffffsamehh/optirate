document.addEventListener('DOMContentLoaded', () => {
    // Auth guard
    if (!localStorage.getItem('access_token')) {
        window.location.href = 'auth.html';
        return;
    }

    // Logout
    const logoutBtn = document.getElementById('navbar-logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            sessionStorage.clear();
            window.location.href = 'index.html';
        });
    }

    // Interest rate data (admin-controlled static data)
    const rates = [
        {
            flag: '🇪🇬', institution: 'Central Bank of Egypt', region: 'Egypt',
            rate: '27.25', trend: 'cut', trendLabel: '▼ Cut', prevRate: '27.75',
            updated: 'May 22, 2025', accent: 'accent-amber'
        },
        {
            flag: '🇺🇸', institution: 'Federal Reserve', region: 'United States',
            rate: '4.50', trend: 'cut', trendLabel: '▼ Cut', prevRate: '4.75',
            updated: 'Dec 18, 2024', accent: 'accent-green'
        },
        {
            flag: '🇪🇺', institution: 'European Central Bank', region: 'Eurozone',
            rate: '2.65', trend: 'cut', trendLabel: '▼ Cut', prevRate: '2.90',
            updated: 'Mar 6, 2025', accent: 'accent-blue'
        }
    ];

    const grid = document.getElementById('ir-grid');
    const loading = document.getElementById('ir-loading');

    // Simulate brief loading for polish
    setTimeout(() => {
        if (loading) loading.remove();

        grid.innerHTML = rates.map((r, i) => `
            <div class="ir-card glass-card ${r.accent}" style="animation-delay: ${0.1 + i * 0.15}s">
                <span class="ir-flag">${r.flag}</span>
                <div class="ir-institution">${r.institution}</div>
                <div class="ir-region">${r.region}</div>
                <div class="ir-rate">${r.rate}%</div>
                <div class="ir-trend ${r.trend}">${r.trendLabel}</div>
                <div class="ir-prev">Previous: ${r.prevRate}%</div>
                <div class="ir-updated">Last Updated: ${r.updated}</div>
            </div>
        `).join('');
    }, 400);
});
