/**
 * metals.js: Defines specific Precious Metals state controllers triggering Grid Accordions natively
 */

document.addEventListener('DOMContentLoaded', async () => {

    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = 'index.html';
        return;
    }

    let user = { role: 'free' };
    try {
        const liveUser = await window.syncCurrentUser?.();
        if (liveUser) user = liveUser;
    } catch (e) {}

    const role = user?.role || 'free';
    const isPremium = role === 'premium' || role === 'admin';
    let metalsChart = null;

    // Role redirection removed to support selective gating (Phase 3.3)

    const btnExplore = document.getElementById('btn-explore');
    const extendedGrid = document.getElementById('extended-metals');
    const syncIndicator = document.getElementById('sync-indicator');

    // Accordion interaction logic
    if (btnExplore && extendedGrid) {
        btnExplore.addEventListener('click', (e) => {
            e.preventDefault();
            const isHidden = extendedGrid.classList.contains('hidden-extended');
            
            if (isHidden) {
                extendedGrid.classList.remove('hidden-extended');
                extendedGrid.classList.add('show-extended');
                btnExplore.innerHTML = "Hide Additional Assets &uarr;";
                btnExplore.classList.add('btn-active'); 
            } else {
                extendedGrid.classList.remove('show-extended');
                extendedGrid.classList.add('hidden-extended');
                btnExplore.innerHTML = "Explore Additional Assets &darr;";
                btnExplore.classList.remove('btn-active');
            }
        });
    }

    const formatCurrency = (amount) => new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount);

    function getOverlayBlock(message, buttonText = 'Upgrade Now') {
        return `
            <div class="premium-overlay">
                <div class="lock-icon">🔒</div>
                <h3>Unlock Premium Features</h3>
                <p>${message}</p>
                <button class="btn-upgrade-glow premium-cta-btn" type="button">${buttonText}</button>
            </div>
        `;
    }

    function bindUpgradeButtons() {
        document.querySelectorAll('.premium-cta-btn').forEach((btn) => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                if (typeof window.openPaymentModal === 'function') {
                    window.openPaymentModal();
                    return;
                }

                const paymentModal = document.getElementById('payment-modal');
                if (paymentModal) paymentModal.classList.remove('hidden');
            });
        });
    }

    function bindLockedGoldCards() {
        document.querySelectorAll('.metal-card.locked').forEach((card) => {
            card.addEventListener('click', () => {
                window.alert('Upgrade to Premium to unlock all gold prices');
            });
        });
    }

    async function fetchMetalsData() {
        try {
            if (syncIndicator) {
                syncIndicator.innerHTML = '<span class="pulse-dot" style="background-color: var(--soft-purple);"></span> Syncing...';
                syncIndicator.style.color = '';
            }

            const headers = { 'Authorization': `Bearer ${token}` };

            const [goldRes, silverRes] = await Promise.all([
                fetch(`${API_BASE_URL}/v2/gold`, { headers }),
                fetch(`${API_BASE_URL}/v2/silver`, { headers })
            ]);

            if (goldRes.status === 401 || silverRes.status === 401) {
                localStorage.removeItem('access_token');
                window.location.href = 'auth.html#login';
                return;
            }

            const goldData = await goldRes.json();
            const silverData = await silverRes.json();

            let hasError = false;

            if (goldData.status === 'success' && goldData.data && goldData.data.length > 0) {
                const metalsGridMain = document.querySelector('.metals-cards .metal-grid');
                const extendedGridMain = document.getElementById('extended-metals');

                // Remove loading spinner
                const loadingEl = document.getElementById('metals-loading');
                if (loadingEl) loadingEl.remove();

                if (metalsGridMain) metalsGridMain.innerHTML = '';
                if (extendedGridMain) extendedGridMain.innerHTML = '';

                goldData.data.forEach(gold => {
                    let targetGrid = metalsGridMain;
                    let title = `GOLD (${gold.karat})`;
                    
                    if (gold.karat === '14K' || gold.karat === 'Coin' || gold.karat === 'Ounce USD') {
                        targetGrid = extendedGridMain;
                        if (gold.karat === 'Coin') title = 'Gold Coin (الجنيه الذهب)';
                        if (gold.karat === 'Ounce USD') title = 'Gold Ounce (USD)';
                    }
                    
                    if (!targetGrid) return;

                    const currency = gold.currency || 'EGP';
                    const shouldLockGoldCard = !isPremium && gold.karat !== '18K';
                    const cardContent = `
                        <div class="metal-header">
                            <div class="metal-title"><span class="metal-dot gold"></span> ${title}</div>
                            <div class="metal-ticker">XAU</div>
                        </div>
                        <div class="metal-body" style="display:flex; justify-content:space-between; margin-top: 10px;">
                            <div class="price-block">
                                <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 6px; font-weight: 500;">Buy (أنت تشتري)</div>
                                <div class="metal-price" style="font-size: 1.8rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px;"><span class="currency-symbol" style="font-size: 1rem; color: #10B981;">${currency}</span> ${formatCurrency(gold.buy)}</div>
                            </div>
                            <div class="price-block" style="text-align: right;">
                                <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 6px; font-weight: 500;">Sell (أنت تبيع)</div>
                                <div class="metal-price" style="font-size: 1.8rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px;"><span class="currency-symbol" style="font-size: 1rem; color: #EF4444;">${currency}</span> ${formatCurrency(gold.sell)}</div>
                            </div>
                        </div>
                        <div class="metal-footer">
                            <div class="update-time">Source: ${gold.source || 'edahabapp'}</div>
                        </div>
                    `;

                    targetGrid.insertAdjacentHTML('beforeend', `
                        <div class="metal-card glass-card ${shouldLockGoldCard ? 'premium-lock locked' : ''}">
                            ${shouldLockGoldCard
                                ? `<div class="content premium-blur">${cardContent}</div>
                                   <div class="blur-overlay"></div>
                                   <span class="lock-icon">🔒 Premium</span>
                                   ${getOverlayBlock('🔒 Premium Only<br>Unlock all gold prices')}`
                                : cardContent}
                        </div>
                    `);
                });

                // Populate Calculator
                const calcSelect = document.getElementById('calc-karat');
                if (calcSelect) {
                    calcSelect.innerHTML = '';
                    goldData.data.forEach(gold => {
                        if (!isPremium && (gold.karat === '24K' || gold.karat === '21K')) return;
                        const label = gold.karat === 'Coin' ? 'Gold Coin (8g)' : (gold.karat === 'Ounce USD' ? 'Gold Ounce (USD)' : `Gold ${gold.karat}`);
                        // Use buy price for calculator as requested
                        calcSelect.insertAdjacentHTML('beforeend', `<option value="${gold.buy}" data-currency="${gold.currency || 'EGP'}">${label} - ${formatCurrency(gold.buy)} (Buy)</option>`);
                    });
                    
                    // Trigger initial calculation
                    setTimeout(() => {
                        const event = new Event('change');
                        calcSelect.dispatchEvent(event);
                    }, 100);
                }
            } else {
                hasError = true;
            }

            if (silverData.status === 'success' && silverData.data) {
                const metalsGridMain = document.querySelector('.metals-cards .metal-grid');
                const silverList = Array.isArray(silverData.data) ? silverData.data : [silverData.data];
                silverList.forEach(silver => {
                    if (!metalsGridMain) return;
                    const currency = silver.currency || 'EGP';
                    const cardContent = `
                        <div class="metal-header">
                            <div class="metal-title"><span class="metal-dot silver"></span> محلي - 999 (Silver)</div>
                            <div class="metal-ticker">XAG</div>
                        </div>
                        <div class="metal-body" style="display:flex; justify-content:space-between; margin-top: 10px;">
                            <div class="price-block">
                                <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 6px; font-weight: 500;">Buy (أنت تشتري)</div>
                                <div class="metal-price" style="font-size: 1.8rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px;"><span class="currency-symbol" style="font-size: 1rem; color: #10B981;">${currency}</span> ${formatCurrency(silver.buy)}</div>
                            </div>
                            <div class="price-block" style="text-align: right;">
                                <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 6px; font-weight: 500;">Sell (أنت تبيع)</div>
                                <div class="metal-price" style="font-size: 1.8rem; font-weight: 800; color: #F8FAFC; letter-spacing: -0.5px;"><span class="currency-symbol" style="font-size: 1rem; color: #EF4444;">${currency}</span> ${formatCurrency(silver.sell)}</div>
                            </div>
                        </div>
                        <div class="metal-footer">
                            <div class="update-time">Source: ${silver.source || 'dahabmasr'} | Updated: ${silver.timestamp ? new Date(silver.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'Just now'}</div>
                        </div>
                    `;

                    metalsGridMain.insertAdjacentHTML('beforeend', `
                        <div class="metal-card glass-card ${!isPremium ? 'premium-lock locked' : ''}">
                            ${!isPremium 
                                ? `<div class="content premium-blur">${cardContent}</div>
                                   <div class="blur-overlay"></div>
                                   <span class="lock-icon">🔒 Premium</span>
                                   ${getOverlayBlock('🔒 Premium Only<br>Unlock silver prices')}`
                                : cardContent}
                        </div>
                    `);
                });
            } else {
                hasError = true;
            }

            if (hasError) {
                if (syncIndicator) {
                    syncIndicator.innerHTML = '<span class="pulse-dot" style="background-color: #EF4444;"></span> Partial Sync Data';
                    syncIndicator.style.color = '#EF4444';
                }
                const metalsGridMain = document.querySelector('.metals-cards .metal-grid');
                if (metalsGridMain && metalsGridMain.innerHTML.trim() === '') {
                    metalsGridMain.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted); width: 100%; grid-column: 1 / -1;">Data temporarily unavailable.</div>';
                }
            } else {
                if (syncIndicator) {
                    syncIndicator.innerHTML = '<span class="pulse-dot" style="background-color: #10B981;"></span> Live Sync Active';
                    syncIndicator.style.color = '#10B981';
                }
            }
            
            if (!isPremium) {
                const calculatorCard = document.querySelector('.calculator-section .glass-card');
                if (calculatorCard) {
                    calculatorCard.classList.add('premium-lock');
                    if (!calculatorCard.querySelector('.premium-overlay')) {
                        const existingContent = calculatorCard.innerHTML;
                        calculatorCard.innerHTML = `
                            <div class="content premium-blur">${existingContent}</div>
                            ${getOverlayBlock('Upgrade to use calculator')}
                        `;
                    }
                }

                // Lock Expansion Section (Additional Assets)
                const expansionSection = document.querySelector('.expansion-section');
                if (expansionSection) {
                    expansionSection.classList.add('premium-lock');
                    if (!expansionSection.querySelector('.premium-overlay')) {
                        const existingContent = expansionSection.innerHTML;
                        expansionSection.innerHTML = `
                            <div class="content premium-blur">${existingContent}</div>
                            ${getOverlayBlock('🔒 Premium Only<br>Unlock 14K, Gold Coins, Ounce USD and more.')}
                        `;
                    }
                }
            }

            bindUpgradeButtons();
            bindLockedGoldCards();

        } catch (error) {
            console.error('Error fetching metals data:', error);
            if (syncIndicator) {
                syncIndicator.innerHTML = '<span class="pulse-dot" style="background-color: #EF4444;"></span> Connection Error';
                syncIndicator.style.color = '#EF4444';
            }
        }
    }

    // Calculator Event Listeners
    const calcKarat = document.getElementById('calc-karat');
    const calcWeight = document.getElementById('calc-weight');
    const calcResult = document.getElementById('calc-result');

    const updateCalc = () => {
        if (!isPremium) return;
        if (!calcKarat || !calcWeight || !calcResult || !calcKarat.value) return;
        const price = parseFloat(calcKarat.value);
        const weight = parseFloat(calcWeight.value) || 0;
        const currency = calcKarat.options[calcKarat.selectedIndex].getAttribute('data-currency') || 'EGP';
        
        const total = price * weight;
        calcResult.innerHTML = `${currency} ${formatCurrency(total)}`;
    };

    if (calcKarat) calcKarat.addEventListener('change', updateCalc);
    if (calcWeight) calcWeight.addEventListener('input', updateCalc);

    if (!isPremium) {
        if (calcKarat) calcKarat.disabled = true;
        if (calcWeight) calcWeight.disabled = true;
    }

    fetchMetalsData();
});
