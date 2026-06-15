/**
 * recommendation.js: UI state management dynamically analyzing input configurations mimicking Prophet Neural Engine logically
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

    const isPremium = user?.role === 'premium' || user?.role === 'admin';

    // ---- Premium gating for Recommendations ----
    if (!isPremium) {
        const formSection = document.querySelector('.form-section');
        if (formSection) {
            formSection.classList.add('premium-lock');
            const existingOverlay = formSection.querySelector('.premium-overlay');
            if (!existingOverlay) {
                const overlay = document.createElement('div');
                overlay.className = 'premium-overlay';
                overlay.innerHTML = `
                    <div class="lock-icon">🔒</div>
                    <h3>Premium Feature</h3>
                    <p>AI Recommendations are exclusive to Premium members. Unlock the full power of Prophet AI.</p>
                    <button class="btn-upgrade-glow" type="button">Upgrade Now</button>
                `;
                overlay.querySelector('button').addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (typeof window.openPaymentModal === 'function') {
                        window.openPaymentModal();
                    } else {
                        const paymentModal = document.getElementById('payment-modal');
                        if (paymentModal) paymentModal.classList.remove('hidden');
                    }
                });
                formSection.appendChild(overlay);
            }
        }
    }
    // -------------------------------------------

    const buyBtn = document.querySelector('.buy-btn');
    const sellBtn = document.querySelector('.sell-btn');
    const radios = document.querySelectorAll('.hidden-radio');

    radios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            if(e.target.value === 'buy') {
                buyBtn.classList.add('active');
                sellBtn.classList.remove('active');
            } else {
                sellBtn.classList.add('active');
                buyBtn.classList.remove('active');
            }
        });
    });

    const currencySelect = document.getElementById('rec-currency');
    const inputTag = document.getElementById('input-tag');

    // Base currencies (USD, EUR, GBP, SAR, AED) are all available to free users.

    currencySelect.addEventListener('change', (e) => {
        inputTag.textContent = e.target.value.toUpperCase();
    });

    const btnGetRec = document.getElementById('btn-get-rec');
    const loadingState = document.getElementById('loading-state');
    const resultsState = document.getElementById('results-state');
    const recAmount = document.getElementById('rec-amount');

    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };

    btnGetRec.addEventListener('click', async (e) => {
        e.preventDefault();
        
        const amount = parseFloat(recAmount.value);
        if(!amount || amount <= 0) {
            alert('Please manually enter a valid Trade Volume (e.g., 1000).');
            return;
        }

        resultsState.classList.add('hidden');
        loadingState.classList.remove('hidden');

        setTimeout(() => {
            window.scrollTo({ top: loadingState.offsetTop - 80, behavior: 'smooth' });
        }, 50);

        try {
            const curr = currencySelect.value;
            const action = document.querySelector('.hidden-radio:checked').value;

            // Fetch live rate first to calculate EGP equivalents
            const currRes = await fetch(`${API_BASE_URL}/v2/currencies?currency=${curr}&mode=average&_t=${Date.now()}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const currData = await currRes.json();
            let liveRate = 0;
            if (currData.status === 'success' && currData.data && currData.data.length > 0) {
                liveRate = currData.data[0].avg_sell; // matching dashboard spot rate exactly
            }

            // Fetch Recommendation
            const payload = { currency: curr, amount: amount, action: action };
            const recRes = await fetch(`${API_BASE_URL}/v3/recommend?refresh=true&_t=${Date.now()}`, {
                method: 'POST',
                headers,
                body: JSON.stringify(payload)
            });
            
            const recData = await recRes.json();

            loadingState.classList.add('hidden');
            
            if (currRes.status === 401 || recRes.status === 401) {
                localStorage.removeItem('access_token');
                window.location.href = 'index.html';
                return;
            }

            if (recData.status === 'success' && recData.data) {
                const result = recData.data;

                // --- DYNAMIC HTML INJECTION FOR AGGRESSIVE BROWSER CACHE ---
                if (!document.getElementById('res-signal')) {
                    resultsState.innerHTML = `
            <!-- Top Bar (Decision) Metric Node Matrix -->
            <div class="decision-bar glass-card text-center">
                <div class="decision-main">
                    <div class="decision-verdict" id="res-verdict"></div>
                    <div class="decision-simple-summary" id="res-simple-summary" style="font-size:1.2rem; margin-top:8px; color:var(--text-color);"></div>
                    <div class="decision-metadata mt-3">
                        <p class="verdict-reasoning" id="res-reasoning" style="font-size:0.95rem; color:var(--text-muted); max-width:600px; margin:0 auto;"></p>
                    </div>
                </div>
            </div>
            <!-- Dashboard Grid -->
            <div class="ai-insight-grid mt-4" style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
                <div class="insight-card glass-card text-center" style="padding: 20px;">
                    <div class="insight-label" style="font-size:0.85rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">Market Mood</div>
                    <div class="insight-value" id="res-market-mood" style="font-size:1.4rem; font-weight:700;"></div>
                </div>
                <div class="insight-card glass-card text-center" style="padding: 20px;">
                    <div class="insight-label" style="font-size:0.85rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">Risk Level</div>
                    <div class="insight-value" id="res-risk" style="font-size:1.4rem; font-weight:700;"></div>
                </div>
                <div class="insight-card glass-card text-center" style="padding: 20px;">
                    <div class="insight-label" style="font-size:0.85rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">AI Signal Strength</div>
                    <div class="insight-value" id="res-signal" style="font-size:1.2rem; font-weight:700; color:var(--primary-color);"></div>
                </div>
            </div>
            <!-- Confidence Progress -->
            <div class="confidence-bar-container glass-card mt-4" style="padding:25px;">
                <div class="conf-header" style="display:flex; justify-content:space-between; margin-bottom:12px; font-weight:600;">
                    <span class="conf-label" style="color:var(--text-muted);">Forecast Confidence</span>
                    <span class="conf-percent" id="res-conf" style="font-size:1.2rem; color:var(--primary-light);"></span>
                </div>
                <div class="progress-bg" style="height:12px; background:rgba(255,255,255,0.05); border-radius:10px; overflow:hidden;">
                    <div class="progress-fill" id="res-conf-bar" style="height:100%; width: 0%; background:linear-gradient(90deg, var(--primary-color), #8B5CF6); border-radius:10px; transition:width 1s ease;"></div>
                </div>
            </div>
            <!-- Scenarios & Money Impact -->
            <div class="money-impact-container glass-card mt-4" style="padding:25px; border-left:4px solid var(--primary-color);">
                <div class="comp-header" style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
                    <div class="comp-icon wait-icon" style="color:var(--primary-color);">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                    </div>
                    <h3 class="comp-title" style="margin:0; font-size:1.2rem;">"If You Wait" Scenario</h3>
                </div>
                <div class="comp-body">
                    <p class="money-impact-text" id="res-wait-scenario" style="font-size:1.3rem; font-weight:600; line-height:1.5;"></p>
                </div>
            </div>
            <!-- Best/Worst Case -->
            <div class="scenarios-grid mt-4" style="display:grid; grid-template-columns: 1fr 1fr; gap:20px;">
                <div class="scenario-card glass-card best-case" style="padding:20px; border-top:3px solid #10B981;">
                    <h4 class="scenario-title" style="color:#10B981; margin:0 0 10px 0; font-size:1.1rem;">Best Case</h4>
                    <p class="scenario-text" id="res-best-case" style="margin:0; font-size:0.95rem; color:var(--text-muted); line-height:1.5;"></p>
                </div>
                <div class="scenario-card glass-card worst-case" style="padding:20px; border-top:3px solid #EF4444;">
                    <h4 class="scenario-title" style="color:#EF4444; margin:0 0 10px 0; font-size:1.1rem;">Worst Case</h4>
                    <p class="scenario-text" id="res-worst-case" style="margin:0; font-size:0.95rem; color:var(--text-muted); line-height:1.5;"></p>
                </div>
            </div>`;
                }

                // Bind decision verdict with color coding
                const verdictNode = document.getElementById('res-verdict');
                verdictNode.textContent = result.decision;

                if (result.decision.includes('WAIT') || result.decision === 'HOLD') {
                    verdictNode.style.color = '#F59E0B'; // Yellow
                } else if (result.decision === 'BUY NOW') {
                    verdictNode.style.color = '#10B981'; // Green
                } else {
                    verdictNode.style.color = '#EF4444'; // Red
                }

                // Simple Summary and Reasoning
                document.getElementById('res-simple-summary').textContent = result.simple_summary || result.decision;
                document.getElementById('res-reasoning').textContent = result.reason || "Model analysis complete.";

                // Market Mood
                document.getElementById('res-market-mood').textContent = result.market_mood || "Stable ➖";

                // Risk Level
                let riskColor = "#10B981"; // green
                if ((result.risk_level || "").includes("HIGH")) riskColor = "#EF4444"; // red
                else if ((result.risk_level || "").includes("MEDIUM")) riskColor = "#F59E0B"; // yellow
                document.getElementById('res-risk').innerHTML = `<span style="color:${riskColor}">${result.risk_level || "UNKNOWN"}</span>`;

                // Recommendation Signal
                let signalColor = "#F59E0B";
                if ((result.recommendation_strength || "").includes("STRONG")) signalColor = "#10B981";
                else if ((result.recommendation_strength || "").includes("WEAK")) signalColor = "#EF4444";
                document.getElementById('res-signal').style.color = signalColor;
                document.getElementById('res-signal').textContent = result.recommendation_strength || "ANALYSIS COMPLETE";

                // Confidence
                const confScore = result.confidence_score || 0;
                document.getElementById('res-conf').textContent = `${confScore}%`;
                document.getElementById('res-conf-bar').style.width = `${confScore}%`;

                // Calculate monetary impact (If you wait)
                let diffText = "";
                if (liveRate > 0) {
                    const currentCostEGP = amount * liveRate;
                    const waitGainPct = result.scenarios.wait.expected_gain;
                    const diffEGP = (currentCostEGP * Math.abs(waitGainPct) / 100).toLocaleString('en-US', { maximumFractionDigits: 0 });
                    
                    if (action === 'buy') {
                        if (waitGainPct > 0) diffText = `If you wait, you may save approximately ${diffEGP} EGP.`;
                        else diffText = `If you wait, you may pay approximately ${diffEGP} EGP more.`;
                    } else {
                        if (waitGainPct > 0) diffText = `If you wait before selling, you could gain approximately ${diffEGP} EGP more.`;
                        else diffText = `If you wait, you could lose approximately ${diffEGP} EGP.`;
                    }
                } else {
                    diffText = "Unable to calculate exact EGP impact due to missing live rates.";
                }
                document.getElementById('res-wait-scenario').textContent = diffText;

                // Best / Worst Case Scenarios
                document.getElementById('res-best-case').textContent = result.scenarios.best_case_text || "The market may move in your favor.";
                document.getElementById('res-worst-case').textContent = result.scenarios.worst_case_text || "Unexpected volatility may affect outcomes.";

                resultsState.classList.remove('hidden');
                window.scrollTo({ top: resultsState.offsetTop - 50, behavior: 'smooth' });

            } else {
                alert(recData.message || "Failed to fetch recommendation.");
            }
            
        } catch (err) {
            console.error(err);
            loadingState.classList.add('hidden');
            alert("Error connecting to the recommendation engine.");
        }
    });

});
