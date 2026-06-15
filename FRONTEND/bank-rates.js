/**
 * bank-rates.js: Table State Manager connected to /api/v2/currencies
 */

document.addEventListener('DOMContentLoaded', async () => {

    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = 'index.html';
        return;
    }

    let role = 'free';
    try {
        const liveUser = await window.syncCurrentUser?.();
        if (liveUser?.role) role = liveUser.role;
    } catch (e) {
        role = 'free';
    }

    const isPremium = role === 'premium' || role === 'admin';
    let bankData = [];
    let isSortedHighToLow = true; 
    function getOverlayBlock(buttonText) {
        return `
            <div class="premium-overlay">
                <div class="lock-icon">🔒</div>
                <h3>Unlock Premium Features</h3>
                <p>Access full gold prices, bank comparisons, and AI insights.</p>
                <button class="btn-upgrade-glow premium-cta-btn" type="button">${buttonText}</button>
            </div>
        `;
    }

    function openUpgradePayment() {
        if (typeof window.openPaymentModal === 'function') {
            window.openPaymentModal();
            return;
        }

        const paymentModal = document.getElementById('payment-modal');
        if (paymentModal) {
            paymentModal.classList.remove('hidden');
        }
    }

    function bindUpgradeButtons() {
        document.querySelectorAll('.premium-cta-btn').forEach((btn) => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                openUpgradePayment();
            });
        });
    }


    const ratesBody = document.getElementById('rates-body');
    const btnSort = document.getElementById('btn-sort');
    const sortOrderText = document.getElementById('sort-order');
    const currencySelect = document.getElementById('currency-select');
    const syncIndicator = document.getElementById('sync-indicator');

    function generateTrendHTML(trend) {
        if (!trend) return "";
        if (trend === "up") return `<span class="trend-icon trend-up-icon">&#8599;</span>`;
        if (trend === "down") return `<span class="trend-icon trend-down-icon">&#8600;</span>`;
        return "";
    }

    function renderTable(dataArray, totalCountOverride = null) {
        ratesBody.innerHTML = ''; 

        if (!dataArray || dataArray.length === 0) {
            ratesBody.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">Data temporarily unavailable.</div>';
            return;
        }

        dataArray.forEach((bank, idx) => {
            const arabicToIso = {
                'اليوان الصينى': 'CNY', 'يوان صيني': 'CNY',
                'الدرهم الإماراتي': 'AED', 'درهم إماراتي': 'AED',
                'دينار كويتي': 'KWD', 'الدينار الكويتي': 'KWD',
                'دولار أمريكي': 'USD', 'الدولار الأمريكي': 'USD',
                'يورو': 'EUR', 'اليورو': 'EUR',
                'جنيه إسترليني': 'GBP', 'الجنيه الإسترليني': 'GBP',
                'ريال سعودي': 'SAR', 'الريال السعودي': 'SAR',
                'ريال قطري': 'QAR', 'الريال القطري': 'QAR',
                'ريال عماني': 'OMR', 'الريال العماني': 'OMR',
                'ين ياباني': 'JPY', 'الين الياباني': 'JPY',
                'دولار كندي': 'CAD', 'الدولار الكندي': 'CAD',
                'دولار أسترالي': 'AUD', 'الدولار الأسترالي': 'AUD'
            };
            
            let currRaw = bank.currency;
            if (typeof currRaw === 'string') {
                currRaw = currRaw.trim();
                if (currRaw.length === 3) currRaw = currRaw.toUpperCase();
            }
            const normalizedCurrency = arabicToIso[currRaw] || currRaw;
            console.log("Rendering Row for:", normalizedCurrency, "with Data:", bank);

            const bidVal = (bank.bid !== null && bank.bid !== undefined) ? bank.bid.toFixed(2) : '---';
            const askVal = (bank.ask !== null && bank.ask !== undefined) ? bank.ask.toFixed(2) : '---';
            const spread = (bank.ask > 0 && bank.bid > 0) ? ((bank.ask - bank.bid) / bank.ask * 100).toFixed(2) : '---';
            const bankName = bank.name || bank.source || 'Unknown Bank';
            
            // Randomly assign icons for banks since API doesn't provide them
            const icons = ['🏛️', '📈', '🌍', '🏦', '💹'];
            const icon = icons[idx % icons.length];

            const rowHTML = `
                <div class="rate-row" style="grid-template-columns: 2fr 1fr 1fr 1fr 1fr;">
                    <div class="col-inst">
                        <div class="bank-logo">${icon}</div>
                        ${bankName}
                    </div>
                    
                    <div class="col-currency" style="font-weight: 600; color: var(--text-muted);">
                        ${normalizedCurrency}
                    </div>

                    <div class="col-price buy-price">
                        ${bidVal}
                        ${generateTrendHTML(bank.trendBid)}
                    </div>
                    
                    <div class="col-price sell-price">
                        ${askVal}
                        ${generateTrendHTML(bank.trendAsk)}
                    </div>
                    
                    <div>
                        <span class="col-spread ${spread !== '---' && parseFloat(spread) < 2 ? 'tight-spread' : ''}">% ${spread}</span>
                    </div>
                </div>
            `;
            ratesBody.insertAdjacentHTML('beforeend', rowHTML);
        });

        const effectiveTotal = totalCountOverride !== null ? totalCountOverride : dataArray.length;
        if (!isPremium && effectiveTotal > 1) {
            const hiddenCount = effectiveTotal - 1;
            ratesBody.insertAdjacentHTML('beforeend', `
                <div class="premium-preview-banner premium-lock">
                    <div class="content">
                        <p class="preview-hidden-count">🔒 + ${hiddenCount} more banks hidden</p>
                    </div>
                    ${getOverlayBlock('Compare All Banks')}
                </div>
            `);
            bindUpgradeButtons();
        }
    }

    async function fetchBankRates(currencyCode) {
        try {
            if (syncIndicator) {
                syncIndicator.innerHTML = '<span class="pulse-dot" style="background-color: var(--soft-purple);"></span> Syncing...';
                syncIndicator.style.color = '';
            }
            ratesBody.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-muted);">Loading data...</div>';
            
            const url = currencyCode ? `${API_BASE_URL}/v2/currencies?currency=${currencyCode}` : `${API_BASE_URL}/v2/currencies`;
            const res = await fetch(url, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (res.status === 401) {
                localStorage.removeItem('access_token');
                window.location.href = 'index.html';
                return;
            }

            const data = await res.json();
            
            if (data.status === 'success' && data.data) {
                console.log("Full Data Received:", data);
                let rawData = data.data;
                if (!Array.isArray(rawData) && typeof rawData === 'object') {
                    rawData = Object.keys(rawData).map(k => ({ currency_key: k, ...rawData[k] }));
                }

                // Map API keys to table logic
                bankData = rawData.map((item, index) => ({
                    id: index,
                    name: item.bank,
                    currency: item.currency || item.currency_key || 'EGP',
                    source: item.source,
                    bid: item.buy !== undefined ? item.buy : null,
                    ask: item.sell !== undefined ? item.sell : null,
                    trendBid: '',
                    trendAsk: ''
                }));

                // Filter out banks with inaccurate rates for specific currencies
                const selectedCurrency = (currencyCode || '').toLowerCase();
                if (selectedCurrency === 'kwd') {
                    bankData = bankData.filter(b => {
                        const name = b.name || '';
                        return !name.includes('الإسكندرية') && !name.includes('الاسكندرية') && !name.includes('ABK') && !name.includes('الأهلي الكويتي');
                    });
                } else if (selectedCurrency === 'jpy') {
                    bankData = bankData.filter(b => {
                        const name = b.name || '';
                        return !name.includes('العقاري المصري') && !name.includes('بيريوس');
                    });
                }

                sortData();
                renderTable(isPremium ? bankData : bankData.slice(0, 1), bankData.length);
                
                if (syncIndicator) {
                    syncIndicator.innerHTML = '<span class="pulse-dot" style="background-color: #10B981;"></span> Live Sync Active';
                    syncIndicator.style.color = '#10B981';
                }
            } else {
                bankData = [];
                renderTable(bankData);
                if (syncIndicator) {
                    syncIndicator.innerHTML = '<span class="pulse-dot" style="background-color: #EF4444;"></span> Sync Failed';
                    syncIndicator.style.color = '#EF4444';
                }
            }
        } catch (error) {
            console.error('Error fetching bank rates:', error);
            bankData = [];
            renderTable(bankData);
            if (syncIndicator) {
                syncIndicator.innerHTML = '<span class="pulse-dot" style="background-color: #EF4444;"></span> Connection Error';
                syncIndicator.style.color = '#EF4444';
            }
        }
    }

    function sortData() {
        bankData.sort((a, b) => {
            const valA = a.bid || 0;
            const valB = b.bid || 0;
            return isSortedHighToLow ? (valB - valA) : (valA - valB);
        });
    }

    if (btnSort) {
        if (!isPremium) {
            btnSort.disabled = true;
            btnSort.classList.add('premium-disabled');
            btnSort.title = 'Upgrade to compare all banks and sort rates';
        }
        btnSort.addEventListener('click', () => {
            if (!isPremium) return;
            isSortedHighToLow = !isSortedHighToLow;
            sortData();
            if(isSortedHighToLow) {
                sortOrderText.innerHTML = "High &rarr; Low";
            } else {
                sortOrderText.innerHTML = "Low &rarr; High";
            }
            renderTable(isPremium ? bankData : bankData.slice(0, 1), bankData.length);
        });
    }

    if (currencySelect) {
        currencySelect.addEventListener('change', (e) => {
            fetchBankRates(e.target.value);
        });
        // Initial fetch defaults to USD preview/comparison flow
        if (!currencySelect.value) {
            currencySelect.value = 'usd';
        }
        fetchBankRates(currencySelect.value);
    } else {
        fetchBankRates('USD');
    }
});
