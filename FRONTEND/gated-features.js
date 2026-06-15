/**
 * gated-features.js: OptiRate Feature Gating System
 * Manages the UI state based on user plan (free/premium).
 */

const GatedFeatures = {
    isPremium: function() {
        const sessionUser = window.getSessionUser ? window.getSessionUser() : null;
        if (!sessionUser) return false;
        return sessionUser.role === 'premium' || sessionUser.role === 'admin';
    },

    applyGating: function() {
        const hasPremium = this.isPremium();
        const currentPage = window.location.pathname;

        if (currentPage.includes('metals.html')) {
            this.gateMetalsPage(hasPremium);
        } else if (currentPage.includes('recommendation.html')) {
            this.gateRecommendationPage(hasPremium);
        } else if (currentPage.includes('bank-rates.html')) {
            this.gateBankRatesPage(hasPremium);
        }
    },

    gateBankRatesPage: function(hasPremium) {
        // Bank page now uses dedicated gating logic in bank-rates.js.
        // Keep this method as no-op to avoid duplicate overlays.
        return;
    },

    showBankGateScreen: function() {
        const ratesTable = document.querySelector('.table-section');
        if (ratesTable) ratesTable.classList.add('hidden');

        let gateScreen = document.getElementById('bank-gate-screen');
        if (!gateScreen) {
            gateScreen = document.createElement('div');
            gateScreen.id = 'bank-gate-screen';
            gateScreen.className = 'recommendation-hero-gate section-spacing';
            gateScreen.style.marginTop = '40px';
            gateScreen.innerHTML = `
                <div class="gate-icon">🏦</div>
                <h2 class="gradient-text">Premium Currency Intelligence</h2>
                <p>Real-time rates for EUR, GBP, AED and 10+ other currencies are exclusive to Premium members.</p>
                <button class="btn btn-upgrade-glow" id="bank-upgrade-btn">Unlock All Currencies</button>
            `;
            const container = document.querySelector('.table-section').parentNode;
            container.insertBefore(gateScreen, document.querySelector('.table-section'));

            document.getElementById('bank-upgrade-btn').addEventListener('click', () => {
                const paymentModal = document.getElementById('payment-modal');
                if (paymentModal) paymentModal.classList.remove('hidden');
            });
        } else {
            gateScreen.classList.remove('hidden');
        }
    },

    lockBankRow: function(row) {
        if (row.querySelector('.premium-row-overlay')) return;

        row.classList.add('premium-locked');
        const overlay = document.createElement('div');
        overlay.className = 'premium-row-overlay';
        overlay.innerHTML = `
            <div class="lock-msg">
                <span>🔒</span> Unlock All Banks
            </div>
        `;
        
        overlay.addEventListener('click', (e) => {
            e.stopPropagation();
            const paymentModal = document.getElementById('payment-modal');
            if (paymentModal) paymentModal.classList.remove('hidden');
        });

        row.appendChild(overlay);
    },

    gateMetalsPage: function(hasPremium) {
        // Metals page now uses dedicated gating logic in metals.js.
        // Keep this method as no-op to avoid duplicate overlays.
        return;
    },

    gateRecommendationPage: function(hasPremium) {
        const formCard = document.querySelector('.rec-form-card');
        const resultsState = document.getElementById('results-state');
        
        if (!hasPremium && formCard) {
            // Hide the form and show the premium hero gate
            formCard.classList.add('hidden');
            if (resultsState) resultsState.classList.add('hidden');

            let gateHero = document.getElementById('recommendation-gate-hero');
            if (!gateHero) {
                gateHero = document.createElement('div');
                gateHero.id = 'recommendation-gate-hero';
                gateHero.className = 'recommendation-hero-gate section-spacing';
                gateHero.innerHTML = `
                    <div class="gate-icon">🧠</div>
                    <h2 class="gradient-text">Unlock AI Financial Intelligence</h2>
                    <p>Get real-time Buy/Sell recommendations based on advanced market analysis and Prophet AI forecasting models.</p>
                    <button class="btn btn-upgrade-glow" id="rec-upgrade-btn">Upgrade to Premium</button>
                `;
                formCard.parentNode.insertBefore(gateHero, formCard);

                document.getElementById('rec-upgrade-btn').addEventListener('click', () => {
                    const upgradeBtn = document.getElementById('upgrade-plan-btn');
                    if (upgradeBtn) upgradeBtn.click();
                    else {
                        // Fallback if profile modal isn't open
                        const paymentModal = document.getElementById('payment-modal');
                        if (paymentModal) paymentModal.classList.remove('hidden');
                    }
                });
            }
        } else if (hasPremium && formCard) {
            formCard.classList.remove('hidden');
            const gateHero = document.getElementById('recommendation-gate-hero');
            if (gateHero) gateHero.remove();
        }
    },

    lockElement: function(el, message) {
        if (el.querySelector('.premium-overlay')) return;

        el.classList.add('premium-locked');
        const overlay = document.createElement('div');
        overlay.className = 'premium-overlay';
        overlay.innerHTML = `
            <div class="lock-icon">🔒</div>
            <h3>Premium Feature</h3>
            <p>${message}</p>
            <button class="btn-upgrade-glow">Upgrade Now</button>
        `;
        
        overlay.querySelector('button').addEventListener('click', (e) => {
            e.stopPropagation();
            const upgradeBtn = document.getElementById('upgrade-plan-btn');
            if (upgradeBtn) upgradeBtn.click();
            else {
                const paymentModal = document.getElementById('payment-modal');
                if (paymentModal) paymentModal.classList.remove('hidden');
            }
        });

        el.appendChild(overlay);
    },

    unlockAll: function() {
        document.querySelectorAll('.premium-locked').forEach(el => {
            el.classList.remove('premium-locked');
            const overlay = el.querySelector('.premium-overlay');
            if (overlay) overlay.remove();
        });
        this.applyGating(); // Re-apply to handle structural changes like in recommendations
    }
};

// Initial application
document.addEventListener('DOMContentLoaded', async () => {
    try {
        if (window.syncCurrentUser) {
            await window.syncCurrentUser();
        }
    } catch (e) {}
    GatedFeatures.applyGating();
});

// Listen for custom event or check periodically if needed
// For Phase 3.3, we'll trigger GatedFeatures.unlockAll() from payment.js success
window.GatedFeatures = GatedFeatures;
