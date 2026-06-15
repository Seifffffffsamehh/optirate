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

    // Format number with commas
    const fmt = (n, decimals = 2) => {
        return Number(n).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
    };

    // Oil data
    const oilData = [
        {
            name: 'Brent Crude Oil', price: 72.48, change: -0.34, changePct: -0.47,
            unit: '/bbl', trend: 'down',
            spark: 'M0,15 Q15,18 30,20 T60,25 T90,22 T120,28'
        },
        {
            name: 'WTI Crude Oil', price: 68.15, change: +0.22, changePct: +0.32,
            unit: '/bbl', trend: 'up',
            spark: 'M0,30 Q15,28 30,25 T60,20 T90,15 T120,12'
        }
    ];

    // Stock data
    const stockData = [
        {
            name: 'S&P 500', price: 5942.47, change: +86.37, changePct: +1.47,
            trend: 'up',
            spark: 'M0,35 Q20,30 40,28 T70,18 T100,10 T120,8'
        },
        {
            name: 'NASDAQ Composite', price: 19256.89, change: +344.12, changePct: +1.82,
            trend: 'up',
            spark: 'M0,32 Q20,30 40,25 T70,15 T100,8 T120,5'
        },
        {
            name: 'Dow Jones', price: 42654.74, change: +401.38, changePct: +0.95,
            trend: 'up',
            spark: 'M0,30 Q20,28 40,26 T70,20 T100,14 T120,10'
        }
    ];

    function buildCard(item, idx, isOil) {
        const dir = item.trend === 'up' ? 'up' : 'down';
        const sign = item.change >= 0 ? '+' : '';
        const strokeColor = dir === 'up' ? '#10B981' : '#EF4444';
        const gradId = `grad_${isOil ? 'oil' : 'stk'}_${idx}`;
        const priceStr = isOil ? `$${fmt(item.price)}` : fmt(item.price);

        return `
        <div class="inv-card glass-card trend-${dir}" style="animation-delay: ${0.1 + idx * 0.12}s">
            <div class="inv-card-header">
                <span class="inv-asset-name">${item.name}</span>
                <span class="inv-live-badge"><span class="inv-live-dot"></span> LIVE</span>
            </div>
            <div class="inv-price">${priceStr} <span class="inv-unit">${item.unit || ''}</span></div>
            <div class="inv-change ${dir}">${sign}${fmt(item.change)} (${sign}${fmt(item.changePct)}%)</div>
            <div class="inv-sparkline-wrap">
                <svg class="inv-sparkline" viewBox="0 0 120 40" preserveAspectRatio="none">
                    <defs>
                        <linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stop-color="${strokeColor}" stop-opacity="0.2"/>
                            <stop offset="100%" stop-color="${strokeColor}" stop-opacity="0"/>
                        </linearGradient>
                    </defs>
                    <path d="${item.spark}" fill="url(#${gradId})" stroke="none"/>
                    <path d="${item.spark}" fill="none" stroke="${strokeColor}" stroke-width="2" stroke-linecap="round"/>
                </svg>
            </div>
        </div>`;
    }

    // Render with brief loading state
    const oilGrid = document.getElementById('oil-grid');
    const stockGrid = document.getElementById('stock-grid');

    setTimeout(() => {
        // Remove loaders
        document.querySelectorAll('.inv-loading').forEach(el => el.remove());

        // Render oil cards
        oilGrid.innerHTML = oilData.map((item, i) => buildCard(item, i, true)).join('');

        // Render stock cards
        stockGrid.innerHTML = stockData.map((item, i) => buildCard(item, i, false)).join('');

        // Update summary
        const now = new Date();
        const h = now.getHours();
        const isOpen = h >= 9 && h < 16; // simplified NYSE hours
        document.getElementById('market-status').innerHTML = `
            <span class="inv-status-dot ${isOpen ? 'open' : 'closed'}"></span>
            ${isOpen ? 'Markets Open' : 'Markets Closed'}`;
        document.getElementById('last-refresh').textContent = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    }, 350);
});
