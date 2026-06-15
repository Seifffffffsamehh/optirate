/**
 * @file dashboard.js — OptiRate Internal Dashboard Interface Controller
 *
 * The main authenticated dashboard that displays:
 *  - Personalized user greeting (username).
 *  - Live USD and EUR average sell rates from all tracked banks.
 *  - Live 18K gold price widget.
 *  - A quick currency conversion calculator seeded with live exchange rates.
 *  - Conditional "upsell" vs. "view metals" link depending on user plan.
 *
 * Data is fetched on load and refreshed every 30 seconds to stay current.
 * If the access token is missing or expired the user is redirected to the
 * landing page immediately.
 */

document.addEventListener('DOMContentLoaded', async () => {

    // --- Auth Guard ---
    // Redirect unauthenticated visitors back to the landing page.
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = 'index.html';
        return;
    }

    // --- Resolve Current User ---
    // Attempt a live sync first; fall back to the cached session if the
    // network call fails (offline tolerance).
    let user = { role: 'free', username: 'Guest' };
    try {
        const liveUser = await window.syncCurrentUser?.();
        if (liveUser) {
            user = liveUser;
        } else {
            const fallbackUser = window.getSessionUser?.();
            if (fallbackUser) user = fallbackUser;
        }
    } catch (e) {}

    // Display the user's name in the dashboard greeting
    const userNameNode = document.getElementById('user-name');
    if (userNameNode && user.username) {
        userNameNode.textContent = user.username;
    }

    // --- Premium Upsell / Metals Link ---
    // Free users see a CTA to unlock premium metals; premium users see a
    // neutral "View all Metals" link.
    if (user.role === 'free') {
        const upsellLink = document.querySelector('.link-upsell');
        if (upsellLink) {
            upsellLink.innerHTML = 'Unlock 21K, 24K & Silver 🔒 &rarr;';
        }
    } else {
        const upsellLink = document.querySelector('.link-upsell');
        if (upsellLink) {
            upsellLink.innerHTML = 'View all Metals &rarr;';
        }
    }

    // Authorization header used for all authenticated API calls
    const headers = {
        'Authorization': `Bearer ${token}`
    };

    // --- Exchange Rate Defaults ---
    // These fallback rates (in EGP) are used by the calculator until live
    // data arrives from the API. Values are overwritten once fetched.
    let exchangeRates = {
        "EGP": 1,
        "USD": 48.20,
        "EUR": 52.15,
        "GBP": 61.20,
        "AED": 13.12
    };

    // --- Dashboard Currency Widget DOM References ---
    const usdPriceEl = document.getElementById('usd-price');
    const usdTrendEl = document.getElementById('usd-trend');
    const usdUpdatedEl = document.getElementById('usd-updated');
    
    const eurPriceEl = document.getElementById('eur-price');
    const eurTrendEl = document.getElementById('eur-trend');
    const eurUpdatedEl = document.getElementById('eur-updated');
    
    const goldPriceEl = document.getElementById('gold-price');
    
    // --- Quick Conversion Calculator DOM References ---
    const calcAmount = document.getElementById('calc-amount');
    const calcFrom = document.getElementById('calc-from');
    const calcTo = document.getElementById('calc-to');
    const calcResult = document.getElementById('calc-result');

    /**
     * Formats a numeric amount as a locale-aware string with exactly 2
     * decimal places (e.g. 48,200.00).
     * @param {number} amount - The value to format.
     * @returns {string} The formatted currency string.
     */
    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount);
    };

    /**
     * Converts an ISO timestamp into a human-readable "time ago" label.
     * Returns "Updated: just now", "Updated: 3 minutes ago", etc.
     * @param {string|null} isoTs - ISO 8601 timestamp string.
     * @returns {string} A friendly "Updated: …" string.
     */
    const timeAgoLabel = (isoTs) => {
        if (!isoTs) return 'Updated: unavailable';
        const updated = new Date(isoTs);
        if (Number.isNaN(updated.getTime())) return 'Updated: unavailable';
        const diffMs = Date.now() - updated.getTime();
        const mins = Math.max(0, Math.floor(diffMs / 60000));
        if (mins < 1) return 'Updated: just now';
        if (mins === 1) return 'Updated: 1 minute ago';
        if (mins < 60) return `Updated: ${mins} minutes ago`;
        const hours = Math.floor(mins / 60);
        if (hours === 1) return 'Updated: 1 hour ago';
        return `Updated: ${hours} hours ago`;
    };

    // --- Calculator Core Logic ---
    // Converts an amount from one currency to another via EGP as the
    // intermediary (all exchange rates are expressed in EGP per unit).
    const calculateExchange = () => {
        const amount = parseFloat(calcAmount.value) || 0;
        const fromRate = exchangeRates[calcFrom.value] || 1;
        const toRate = exchangeRates[calcTo.value] || 1;
        
        // Convert source currency → EGP → target currency
        const resultInEGP = amount * fromRate;
        const finalResult = resultInEGP / toRate;
        
        calcResult.innerHTML = `${formatCurrency(finalResult)} <span class="calc-currency">${calcTo.value}</span>`;
    };

    // Bind calculator inputs so the result updates in real time
    if(calcAmount && calcFrom && calcTo) {
        calcAmount.addEventListener('input', calculateExchange);
        calcFrom.addEventListener('change', calculateExchange);
        calcTo.addEventListener('change', calculateExchange);
    }

    /**
     * Fetches live currency averages and gold prices from the backend,
     * then hydrates every dashboard widget with fresh data.
     * Also updates the exchangeRates object so the calculator uses live values.
     *
     * @async
     * @returns {Promise<boolean>} true if data was loaded successfully.
     */
    const fetchAndHydrateDashboard = async () => {
        try {
            // Fetch currency averages and gold prices in parallel
            const [currResponse, goldResponse] = await Promise.all([
                fetch(`${API_BASE_URL}/v2/currencies?mode=average`, { headers }),
                fetch(`${API_BASE_URL}/v2/gold`, { headers })
            ]);
            
            // If either endpoint returns 401, the token is expired — redirect
            if (currResponse.status === 401 || goldResponse.status === 401) {
                localStorage.removeItem('access_token');
                window.location.href = 'index.html';
                return false;
            }

            const currData = await currResponse.json();

            // --- Populate Currency Widgets (USD, EUR) & update calculator rates ---
            if (currData.status === 'success' && currData.data) {
                const usd = currData.data.find(c => c.currency === 'USD');
                const eur = currData.data.find(c => c.currency === 'EUR');
                const gbp = currData.data.find(c => c.currency === 'GBP');
                const aed = currData.data.find(c => c.currency === 'AED');

                if (usd) {
                    usdPriceEl.innerHTML = `${formatCurrency(usd.avg_sell)} <span style="font-size: 1rem; color: var(--text-muted);">EGP</span>`;
                    usdTrendEl.innerHTML = '';
                    exchangeRates["USD"] = usd.avg_sell;
                    if (usdUpdatedEl) usdUpdatedEl.textContent = timeAgoLabel(usd.last_updated);
                    console.log("Banks used for AVG calculation:", usd.banks_used || []);
                }
                if (eur) {
                    eurPriceEl.innerHTML = `${formatCurrency(eur.avg_sell)} <span style="font-size: 1rem; color: var(--text-muted);">EGP</span>`;
                    eurTrendEl.innerHTML = '';
                    exchangeRates["EUR"] = eur.avg_sell;
                    if (eurUpdatedEl) eurUpdatedEl.textContent = timeAgoLabel(eur.last_updated);
                    console.log("Banks used for AVG calculation:", eur.banks_used || []);
                }
                // Update calculator rates for GBP and AED (no dedicated widgets)
                if (gbp) exchangeRates["GBP"] = gbp.avg_sell;
                if (aed) exchangeRates["AED"] = aed.avg_sell;
            }

            // --- Populate Gold Widget ---
            const goldData = await goldResponse.json();

            if (goldData.status === 'success' && goldData.data) {
                // Prefer 18K gold price for the dashboard card
                const gold18k = goldData.data.find(g => g.karat === '18K');
                if (gold18k) {
                    goldPriceEl.innerHTML = `${formatCurrency(gold18k.sell)} <span style="font-size: 1rem; color: var(--text-muted);">EGP</span>`;
                } else if (goldData.data.length > 0) {
                    // fallback to first if 18k not found
                    goldPriceEl.innerHTML = `${formatCurrency(goldData.data[0].sell)} <span style="font-size: 1rem; color: var(--text-muted);">EGP</span>`;
                }
            }

            // Recalculate the converter with fresh rates
            calculateExchange();
            return true;
        } catch (err) {
            console.error('Error fetching dashboard data:', err);
            return false;
        }
    };

    // --- Initial Data Load ---
    // Attempt the first fetch; if it fails, display fallback "unavailable" messages.
    const firstLoadOk = await fetchAndHydrateDashboard();
    if (!firstLoadOk) {
        usdPriceEl.innerHTML = '<span style="font-size: 0.9rem; color: var(--text-muted);">Data temporarily unavailable.</span>';
        eurPriceEl.innerHTML = '<span style="font-size: 0.9rem; color: var(--text-muted);">Data temporarily unavailable.</span>';
        goldPriceEl.innerHTML = '<span style="font-size: 0.9rem; color: var(--text-muted);">Data temporarily unavailable.</span>';
        if (usdUpdatedEl) usdUpdatedEl.textContent = 'Updated: unavailable';
        if (eurUpdatedEl) eurUpdatedEl.textContent = 'Updated: unavailable';
    }

    // --- Auto-Refresh ---
    // Keep average prices live by refreshing every 30 seconds.
    setInterval(fetchAndHydrateDashboard, 30000);
});
