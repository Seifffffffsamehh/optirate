/**
 * prediction.js: Logic execution mapping UI state arrays targeting predictive neural hooks
 */
document.addEventListener('DOMContentLoaded', async () => {

    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = 'index.html';
        return;
    }

    let user = { role: 'free', username: 'Guest' };
    try {
        const liveUser = await window.syncCurrentUser?.();
        if (liveUser) user = liveUser;
    } catch (e) {}

    const btnRunModel = document.getElementById('btn-run-model');
    const currencySelect = document.getElementById('currency-select');
    const emptyState = document.getElementById('empty-state');
    const resultsState = document.getElementById('results-state');

    // UI payload targets seamlessly
    const fcFlag = document.getElementById('fc-flag');
    const fcPair = document.getElementById('fc-pair');
    const fcCurrent = document.getElementById('fc-current');
    const fcTarget = document.getElementById('fc-target');
    const fcTrend = document.getElementById('fc-trend');
    const fcBounds = document.getElementById('fc-bounds');
    const fcConfidence = document.getElementById('fc-confidence');
    const mlBadge = document.querySelector('.ml-badge');
    const btnForceRefresh = document.getElementById('btn-force-refresh');

    const headers = { 'Authorization': `Bearer ${token}` };

    // Populate Currency Dropdown dynamically from available endpoint
    try {
        const currListRes = await fetch(`${API_BASE_URL}/v2/currencies`, { headers });
        if (currListRes.status === 401) {
            localStorage.removeItem('access_token');
            window.location.href = 'index.html';
            return;
        }
        const currListData = await currListRes.json();
        if (currListData.status === 'success' && currListData.data) {
            currencySelect.innerHTML = '<option value="" disabled selected>Select Currency</option>';
            const seenCurrencies = new Set();
            const excludedCurrencies = new Set(['jpy', 'omr', 'kwd']);
            currListData.data.forEach(item => {
                const code = item.currency.toLowerCase();
                if (!seenCurrencies.has(code) && !excludedCurrencies.has(code)) {
                    seenCurrencies.add(code);
                    currencySelect.insertAdjacentHTML('beforeend', `<option value="${code}">${code.toUpperCase()} Base (EGP)</option>`);
                }
            });
        }
    } catch (e) {
        console.error("Failed to load currencies", e);
        // Fallback for UI testing
        currencySelect.innerHTML = '<option value="" disabled selected>Select Currency</option>';
        ['usd', 'eur', 'gbp', 'sar', 'aed'].forEach(code => {
            currencySelect.insertAdjacentHTML('beforeend', `<option value="${code}">${code.toUpperCase()} Base (EGP)</option>`);
        });
    }

        // --- FREEMIUM RESTRICTION LOGIC START ---
        function checkPredictionLimit(increment = false) {
            const plan = user.plan || user.role || 'free';
            let usageStr = localStorage.getItem('predictionUsage_' + user.username);
            let usage = usageStr ? JSON.parse(usageStr) : { predictions_used: 0, last_reset: Date.now(), plan: plan };
            
            const now = Date.now();
            if (now - usage.last_reset >= 24 * 60 * 60 * 1000) {
                usage.predictions_used = 0;
                usage.last_reset = now;
            }
            usage.plan = plan;

            if (plan === 'free') {
                if (usage.predictions_used >= 2) {
                    // Limit reached
                    const msLeft = (24 * 60 * 60 * 1000) - (now - usage.last_reset);
                    const hoursLeft = Math.floor(msLeft / (1000 * 60 * 60));
                    const minsLeft = Math.floor((msLeft % (1000 * 60 * 60)) / (1000 * 60));
                    
                    btnRunModel.innerHTML = `Daily prediction limit reached (2/2) - Resets in ${hoursLeft}h ${minsLeft}m`;
                    btnRunModel.disabled = true;
                    btnRunModel.style.opacity = '0.5';
                    btnRunModel.style.cursor = 'not-allowed';
                    
                    if (!document.getElementById('upgrade-prompt-limit')) {
                        const upgradePrompt = document.createElement('div');
                        upgradePrompt.id = 'upgrade-prompt-limit';
                        upgradePrompt.style.width = '100%';
                        upgradePrompt.style.marginTop = '15px';
                        upgradePrompt.style.textAlign = 'center';
                        upgradePrompt.style.fontSize = '0.95rem';
                        upgradePrompt.style.fontWeight = '600';
                        upgradePrompt.innerHTML = `<a href="javascript:void(0)" onclick="openPaymentModal()" style="color: #F59E0B; text-decoration: underline;">Upgrade to Premium for unlimited predictions 💎</a>`;
                        btnRunModel.parentElement.appendChild(upgradePrompt);
                        btnRunModel.parentElement.style.flexWrap = 'wrap';
                    }
                    return false;
                }
                
                if (increment) {
                    usage.predictions_used++;
                    localStorage.setItem('predictionUsage_' + user.username, JSON.stringify(usage));
                }
                return true;
            } else {
                if (increment) {
                    localStorage.setItem('predictionUsage_' + user.username, JSON.stringify(usage));
                }
                return true;
            }
        }
        
        // Initial check on load (without incrementing)
        // Wait slightly for user role to sync
        setTimeout(() => checkPredictionLimit(false), 500);
        // --- FREEMIUM RESTRICTION LOGIC END ---

        btnRunModel.addEventListener('click', async () => {
            const selected = currencySelect.value;
            if (!selected) {
                alert("Please select a valid currency pairing first.");
                return;
            }

            // Enforce and increment
            if (!checkPredictionLimit(true)) {
                return;
            }

        // Loading State
        const defaultText = btnRunModel.innerHTML;
        btnRunModel.innerHTML = `<span class="pulse-dot" style="display:inline-block; background-color:white; margin-right:8px;"></span> AI Analyzing ${selected.toUpperCase()}...`;
        btnRunModel.style.opacity = '0.8';
        emptyState.style.opacity = '0.3';
        resultsState.classList.add('hidden'); // Clear chart

        
        try {
            // Get Current Rate first (using average to match Dashboard exactly)
            const currRes = await fetch(`${API_BASE_URL}/v2/currencies?currency=${selected}&mode=average&_t=${Date.now()}`, { headers });
            const currData = await currRes.json();
            let currentPrice = 0;
            if (currData.status === 'success' && currData.data && currData.data.length > 0) {
                currentPrice = currData.data[0].avg_sell;
            }

            const predRes = await fetch(`${API_BASE_URL}/v3/predict/${selected}?refresh=true&_t=${Date.now()}`, { headers });
            
            if (currRes && currRes.status === 401 || predRes.status === 401) {
                localStorage.removeItem('access_token');
                window.location.href = 'index.html';
                return;
            }

            const predData = await predRes.json();

            if (predData.status === 'success' && predData.data) {
                const predictions = predData.data.predictions;
                const modelUsed = predData.data.model || 'Prophet Engine';
                
                if (!predictions || predictions.length === 0) {
                    throw new Error("No predictions returned.");
                }

                const lastPred = predictions[predictions.length - 1];
                const targetPrice = lastPred.expected;
                
                if (currentPrice === 0) currentPrice = predictions[0].expected; // fallback

                const diff = targetPrice - currentPrice;
                const changePct = ((diff) / currentPrice * 100).toFixed(2);
                
                const type = diff >= 0 ? 'up' : 'down';
                const trendIcon = diff >= 0 ? '&#8599;' : '&#8600;';
                const trendText = `${trendIcon} ${diff >= 0 ? '+' : ''}${changePct}%`;

                // Confidence
                const yhat = lastPred.expected;
                const lower = lastPred.lower;
                const upper = lastPred.upper;
                const conf = yhat > 0 ? (1 - (upper - lower) / yhat) * 100 : 0;
                const confidenceScore = Math.max(0, Math.min(100, conf)).toFixed(0);

                const flags = { 'usd': '🇺🇸', 'eur': '🇪🇺', 'gbp': '🇬🇧', 'sar': '🇸🇦', 'aed': '🇦🇪', 'kwd': '🇰🇼', 'qar': '🇶🇦', 'omr': '🇴🇲', 'cny': '🇨🇳', 'jpy': '🇯🇵', 'cad': '🇨🇦', 'aud': '🇦🇺' };
                
                // Hydrate
                fcFlag.textContent = flags[selected] || '🏳️';
                fcPair.textContent = `${selected.toUpperCase()} / EGP`;
                fcCurrent.textContent = currentPrice.toFixed(2);
                fcTarget.textContent = targetPrice.toFixed(2);
                fcTrend.innerHTML = trendText;
                fcBounds.textContent = `${lower.toFixed(2)} - ${upper.toFixed(2)}`;
                fcConfidence.textContent = `${confidenceScore}%`;

                if(type === 'down') {
                    fcTrend.className = 'trend-box trend-down'; 
                } else {
                    fcTrend.className = 'trend-box trend-up';
                }

                if (mlBadge) {
                    mlBadge.textContent = user.role === 'free' ? '2-Day Projection' : '14-Day Projection';
                }

                // Render Chart SVG
                const svgFill = document.querySelector('.fc-fill');
                const svgLine = document.querySelector('.fc-line');
                const pulseMarker = document.querySelector('.pulse-marker');

                if (svgFill && svgLine && pulseMarker) {
                    const maxUpper = Math.max(...predictions.map(p => p.upper));
                    const minLower = Math.min(...predictions.map(p => p.lower));
                    const range = (maxUpper - minLower) || 1; 

                    const padY = 20; 
                    const scaleY = (val) => 150 - padY - ((val - minLower) / range) * (150 - 2 * padY);
                    const stepX = predictions.length > 1 ? 1000 / (predictions.length - 1) : 0;

                    let linePath = `M0,${scaleY(predictions[0].expected)}`;
                    let fillPathUpper = `M0,${scaleY(predictions[0].upper)}`;
                    let fillPathLower = [];

                    predictions.forEach((p, i) => {
                        const x = i * stepX;
                        if (i > 0) {
                            linePath += ` L${x},${scaleY(p.expected)}`;
                            fillPathUpper += ` L${x},${scaleY(p.upper)}`;
                        }
                        fillPathLower.push(`${x},${scaleY(p.lower)}`);
                    });

                    let fillPath = fillPathUpper;
                    for (let i = fillPathLower.length - 1; i >= 0; i--) {
                        fillPath += ` L${fillPathLower[i]}`;
                    }
                    fillPath += ' Z';

                    svgLine.setAttribute('d', linePath);
                    svgFill.setAttribute('d', fillPath);

                    const lastX = (predictions.length - 1) * stepX;
                    const lastY = scaleY(predictions[predictions.length - 1].expected);
                    pulseMarker.setAttribute('cx', lastX);
                    pulseMarker.setAttribute('cy', lastY);

                    // If there's an overlay text for the model, update it
                    const overlayText = document.querySelector('.graph-overlay-text');
                    if (overlayText) {
                        overlayText.textContent = `Model Visual Output Trajectory (${modelUsed.replace(/_/g, ' ').toUpperCase()})`;
                    }
                }

                emptyState.classList.add('hidden');
                resultsState.classList.remove('hidden');
                window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
            } else {
                alert(predData.message || "Failed to fetch prediction.");
                emptyState.classList.remove('hidden');
                resultsState.classList.add('hidden');
            }
        } catch (err) {
            console.error(err);
            alert("Error running the AI model.");
            emptyState.classList.remove('hidden');
            resultsState.classList.add('hidden');
        } finally {
            btnRunModel.innerHTML = defaultText;
            btnRunModel.style.opacity = '1';
            emptyState.style.opacity = '1';
        }
    });

    if (currencySelect) {
        currencySelect.addEventListener('change', () => {
            // Hide the results state to clear the chart before the API call finishes
            resultsState.classList.add('hidden');
            emptyState.classList.remove('hidden');
            btnRunModel.click();
        });
    }

    btnForceRefresh.addEventListener('click', () => {
        const original = btnForceRefresh.innerHTML;
        btnForceRefresh.innerHTML = "Syncing Node...";
        if (currencySelect.value) {
            btnRunModel.click();
        }
        setTimeout(() => {
            btnForceRefresh.innerHTML = original;
        }, 800);
    });

    // Auto-refresh every 30 seconds
    setInterval(() => {
        if (!resultsState.classList.contains('hidden') && currencySelect.value) {
            btnRunModel.click();
        }
    }, 30000);
});
