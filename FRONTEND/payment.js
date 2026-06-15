/**
 * payment.js: OptiRate Phase 3.3 — Mock Premium Payment System
 * SECURITY: This is a MOCK system. Card data is NOT stored or transmitted to any real gateway.
 */
document.addEventListener('DOMContentLoaded', () => {
    // Dynamically inject payment modal if not already present
    if (!document.getElementById('payment-modal')) {
        const modalHTML = `
        <div id="payment-modal" class="payment-overlay hidden">
            <div class="payment-card">
                <div id="payment-form-state">
                    <div class="payment-header">
                        <button id="payment-close-btn" class="payment-close-btn">&times;</button>
                        <span class="diamond-icon">💎</span>
                        <h2>Upgrade to Premium</h2>
                        <p class="price-tag">Unlock all features for <strong>75 EGP/month</strong></p>
                    </div>
                    <div class="premium-features-strip">
                        <span class="feature-pill"><span class="pill-icon">📊</span> All Currencies</span>
                        <span class="feature-pill"><span class="pill-icon">🧠</span> AI Forecasts</span>
                        <span class="feature-pill"><span class="pill-icon">🥇</span> Gold &amp; Silver</span>
                        <span class="feature-pill"><span class="pill-icon">⚡</span> Priority Data</span>
                    </div>
                    <div id="payment-error-msg" class="payment-error"></div>

                    <!-- Interactive Credit Card Preview -->
                    <div class="credit-card-preview-container">
                        <div class="credit-card-preview" id="credit-card-preview">
                            <div class="cc-front">
                                <div class="cc-logo">OptiRate <span>Premium</span></div>
                                <div class="cc-chip"></div>
                                <div class="cc-number" id="cc-preview-number">•••• •••• •••• ••••</div>
                                <div class="cc-details">
                                    <div class="cc-name-wrapper">
                                        <span class="cc-label">Cardholder</span>
                                        <div class="cc-name" id="cc-preview-name">YOUR NAME</div>
                                    </div>
                                    <div class="cc-expiry-wrapper">
                                        <span class="cc-label">Expires</span>
                                        <div class="cc-expiry" id="cc-preview-expiry">MM/YY</div>
                                    </div>
                                </div>
                            </div>
                            <div class="cc-back">
                                <div class="cc-stripe"></div>
                                <div class="cc-cvv-wrapper">
                                    <span class="cc-label">CVV</span>
                                    <div class="cc-cvv-stripe" id="cc-preview-cvv">•••</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <form id="payment-form" autocomplete="off">
                        <div class="payment-body">
                            <div class="payment-form-group">
                                <label class="payment-label">Cardholder Name</label>
                                <input type="text" id="pay-name" class="payment-input" placeholder="e.g. Ahmed Mohamed" autocomplete="off">
                            </div>
                            <div class="payment-form-group">
                                <label class="payment-label">Card Number</label>
                                <div class="card-number-wrapper">
                                    <input type="text" id="pay-card" class="payment-input" placeholder="0000 0000 0000 0000" maxlength="19" inputmode="numeric" autocomplete="off">
                                    <span class="card-brand-icon">💳</span>
                                </div>
                            </div>
                            <div class="payment-row">
                                <div class="payment-form-group">
                                    <label class="payment-label">Expiry</label>
                                    <input type="text" id="pay-expiry" class="payment-input" placeholder="MM/YY" maxlength="5" autocomplete="off">
                                </div>
                                <div class="payment-form-group">
                                    <label class="payment-label">CVV</label>
                                    <input type="password" id="pay-cvv" class="payment-input" placeholder="•••" maxlength="4" inputmode="numeric" autocomplete="off">
                                </div>
                            </div>
                        </div>
                        <div class="payment-footer">
                            <button type="submit" id="btn-pay" class="btn-pay">💎 Activate Premium — 75 EGP</button>
                        </div>
                    </form>
                    <div class="payment-security-notice">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
                        Mock payment — no real charges. Secured by OptiRate.
                    </div>
                </div>
                <div id="payment-success-state" class="payment-success-state">
                    <div class="success-checkmark">✓</div>
                    <h3>Welcome to Premium!</h3>
                    <p>You now have full access to all OptiRate features.</p>
                    <p id="success-expiry" class="expiry-date"></p>
                    <button id="btn-done" class="btn-done">Continue to Dashboard →</button>
                </div>
            </div>
        </div>
        <canvas id="confetti-canvas"></canvas>`;
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    // Also inject payment.css if not already linked
    if (!document.querySelector('link[href*="payment.css"]')) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = 'payment.css';
        document.head.appendChild(link);
    }

    const paymentModal = document.getElementById('payment-modal');
    if (!paymentModal) return;

    const upgradePlanBtn = document.getElementById('upgrade-plan-btn');
    const paymentCloseBtn = document.getElementById('payment-close-btn');
    const paymentForm = document.getElementById('payment-form');
    const btnPay = document.getElementById('btn-pay');
    const paymentError = document.getElementById('payment-error-msg');
    const paymentFormState = document.getElementById('payment-form-state');
    const paymentSuccessState = document.getElementById('payment-success-state');
    const successExpiry = document.getElementById('success-expiry');
    const btnDone = document.getElementById('btn-done');

    function openPaymentModal() {
        const profileModal = document.getElementById('profile-modal');
        if (profileModal) profileModal.classList.add('hidden');
        resetPaymentModal();
        paymentModal.classList.remove('hidden');
    }

    window.openPaymentModal = openPaymentModal;

    function bindUpgradeClickInterceptor() {
        const upgradeSelector = '#upgrade-plan-btn, .premium-cta-btn, #bank-upgrade-btn, #rec-upgrade-btn, .premium-link';
        document.addEventListener('click', (e) => {
            const trigger = e.target.closest(upgradeSelector);
            if (!trigger) return;

            e.preventDefault();
            e.stopImmediatePropagation();
            openPaymentModal();
        }, true);
    }

    bindUpgradeClickInterceptor();

    // Open payment modal from "Upgrade to Premium" button
    if (upgradePlanBtn) {
        upgradePlanBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openPaymentModal();
        });
    }

    // Close
    if (paymentCloseBtn) {
        paymentCloseBtn.addEventListener('click', () => paymentModal.classList.add('hidden'));
    }
    paymentModal.addEventListener('click', (e) => {
        if (e.target === paymentModal) paymentModal.classList.add('hidden');
    });

    // Done button
    if (btnDone) {
        btnDone.addEventListener('click', () => {
            paymentModal.classList.add('hidden');
            window.location.reload();
        });
    }

    function resetPaymentModal() {
        if (paymentFormState) paymentFormState.style.display = 'block';
        if (paymentSuccessState) { paymentSuccessState.classList.remove('visible'); paymentSuccessState.style.display = 'none'; }
        if (paymentError) { paymentError.classList.remove('visible'); paymentError.textContent = ''; }
        if (btnPay) { btnPay.disabled = false; btnPay.innerHTML = '💎 Activate Premium — 75 EGP'; }
        const inputs = paymentModal.querySelectorAll('.payment-input');
        inputs.forEach(i => { i.value = ''; i.classList.remove('input-error'); });
    }

    function showPaymentError(msg) {
        if (paymentError) { paymentError.textContent = '⚠ ' + msg; paymentError.classList.add('visible'); }
    }

    // Card number formatting
    const cardInput = document.getElementById('pay-card');
    if (cardInput) {
        cardInput.addEventListener('input', (e) => {
            let v = e.target.value.replace(/\D/g, '').substring(0, 16);
            e.target.value = v.replace(/(.{4})/g, '$1 ').trim();
        });
    }

    // Credit Card Interactive Preview Logic
    const ccPreviewCard = document.getElementById('credit-card-preview');
    const ccPreviewName = document.getElementById('cc-preview-name');
    const ccPreviewNumber = document.getElementById('cc-preview-number');
    const ccPreviewExpiry = document.getElementById('cc-preview-expiry');
    const ccPreviewCvv = document.getElementById('cc-preview-cvv');

    const inputName = document.getElementById('pay-name');
    const inputNumber = document.getElementById('pay-card');
    const inputExpiry = document.getElementById('pay-expiry');
    const inputCvv = document.getElementById('pay-cvv');

    if (inputName && ccPreviewName) {
        inputName.addEventListener('input', (e) => {
            ccPreviewName.textContent = e.target.value.trim() || 'YOUR NAME';
        });
    }

    if (inputNumber && ccPreviewNumber) {
        inputNumber.addEventListener('input', (e) => {
            const val = e.target.value.trim();
            ccPreviewNumber.textContent = val || '•••• •••• •••• ••••';
        });
    }

    if (inputExpiry && ccPreviewExpiry) {
        inputExpiry.addEventListener('input', (e) => {
            ccPreviewExpiry.textContent = e.target.value.trim() || 'MM/YY';
        });
    }

    if (inputCvv && ccPreviewCvv && ccPreviewCard) {
        inputCvv.addEventListener('input', (e) => {
            ccPreviewCvv.textContent = e.target.value || '•••';
        });
        
        inputCvv.addEventListener('focus', () => {
            ccPreviewCard.classList.add('is-flipped');
        });
        
        inputCvv.addEventListener('blur', () => {
            ccPreviewCard.classList.remove('is-flipped');
        });
    }

    // Submit payment
    if (paymentForm) {
        paymentForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (paymentError) paymentError.classList.remove('visible');
            paymentModal.querySelectorAll('.payment-input').forEach(i => i.classList.remove('input-error'));

            const cardNumber = (document.getElementById('pay-card')?.value || '').replace(/\s/g, '');
            const cardName = (document.getElementById('pay-name')?.value || '').trim();
            const expiry = (document.getElementById('pay-expiry')?.value || '').trim();
            const cvv = (document.getElementById('pay-cvv')?.value || '').trim();

            if (!cardName) { document.getElementById('pay-name')?.classList.add('input-error'); showPaymentError('Cardholder name is required.'); return; }
            if (!/^\d{16}$/.test(cardNumber)) { document.getElementById('pay-card')?.classList.add('input-error'); showPaymentError('Card number must be exactly 16 digits.'); return; }
            if (!/^\d{2}\/\d{2}$/.test(expiry)) { document.getElementById('pay-expiry')?.classList.add('input-error'); showPaymentError('Expiry must be in MM/YY format.'); return; }
            if (!/^\d{3,4}$/.test(cvv)) { document.getElementById('pay-cvv')?.classList.add('input-error'); showPaymentError('CVV must be 3 or 4 digits.'); return; }

            btnPay.disabled = true;
            btnPay.innerHTML = '<span class="btn-spinner"></span> Processing...';

            const token = localStorage.getItem('access_token');
            if (!token) { showPaymentError('Session expired. Please log in again.'); btnPay.disabled = false; btnPay.innerHTML = '💎 Activate Premium — 75 EGP'; return; }

            try {
                const res = await fetch(`${API_BASE_URL}/v3/upgrade`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ card_number: cardNumber, name: cardName, expiry: expiry, cvv: cvv })
                });
                const data = await res.json();

                if (res.ok && data.status === 'success') {
                    if (data.data.access_token) {
                        localStorage.setItem('access_token', data.data.access_token);
                    }
                    await window.syncCurrentUser?.();

                    const badge = document.getElementById('profile-plan-badge');
                    if (badge) { badge.textContent = '💎 Premium'; badge.classList.add('premium'); }
                    if (upgradePlanBtn) upgradePlanBtn.classList.add('hidden');

                    if (paymentFormState) paymentFormState.style.display = 'none';
                    if (successExpiry) {
                        const expDate = new Date(data.data.subscription_expires);
                        successExpiry.textContent = 'Valid until: ' + expDate.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
                    }
                    if (paymentSuccessState) { paymentSuccessState.style.display = 'block'; paymentSuccessState.classList.add('visible'); }
                    launchConfetti();
                    if (window.GatedFeatures) window.GatedFeatures.unlockAll();
                } else {
                    showPaymentError(data.message || 'Payment failed. Please try again.');
                    btnPay.disabled = false;
                    btnPay.innerHTML = '💎 Activate Premium — 75 EGP';
                }
            } catch (err) {
                console.error('Payment error:', err);
                showPaymentError('Connection error. Please try again.');
                btnPay.disabled = false;
                btnPay.innerHTML = '💎 Activate Premium — 75 EGP';
            }
        });
    }

    function launchConfetti() {
        const canvas = document.getElementById('confetti-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        const particles = [];
        const colors = ['#6C5CE7', '#A29BFE', '#06B6D4', '#FFD700', '#10B981', '#FF5252', '#F59E0B'];
        for (let i = 0; i < 150; i++) {
            particles.push({ x: Math.random() * canvas.width, y: Math.random() * canvas.height - canvas.height, w: Math.random() * 10 + 5, h: Math.random() * 6 + 3, color: colors[Math.floor(Math.random() * colors.length)], vx: (Math.random() - 0.5) * 4, vy: Math.random() * 3 + 2, rot: Math.random() * 360, rotSpeed: (Math.random() - 0.5) * 8, opacity: 1 });
        }
        let frame = 0;
        function animate() {
            frame++;
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            let alive = false;
            particles.forEach(p => {
                if (p.opacity <= 0) return;
                alive = true;
                p.x += p.vx; p.y += p.vy; p.vy += 0.05; p.rot += p.rotSpeed;
                if (frame > 80) p.opacity -= 0.015;
                ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.rot * Math.PI / 180);
                ctx.globalAlpha = Math.max(0, p.opacity); ctx.fillStyle = p.color;
                ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h); ctx.restore();
            });
            if (alive) requestAnimationFrame(animate);
            else ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
        animate();
    }
});
