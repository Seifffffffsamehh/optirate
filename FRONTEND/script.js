/**
 * @file script.js — OptiRate Landing Page Interactions & Animations
 *
 * Handles global UI behaviors for the public-facing landing page:
 *  - Smooth scrolling for in-page anchor links (e.g. #features, #pricing).
 *  - Logo click navigation that redirects authenticated users to the
 *    dashboard and unauthenticated users to the landing page.
 */
document.addEventListener("DOMContentLoaded", () => {
    
    // --- Smooth Scrolling for Anchor Links ---
    // Intercept clicks on any link whose href starts with "#" and animate
    // the scroll to the target section instead of using the browser's
    // default jump behavior. Links with href="#" only (no target) are ignored.
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            
            if (href !== "#") {
                e.preventDefault();
                const targetElement = document.querySelector(href);
                
                if (targetElement) {
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });

    // --- Logo Navigation Redirect ---
    // Makes every element with the .logo class clickable.
    // If the user has a valid access token (logged in), clicking the logo
    // navigates to the dashboard; otherwise, it goes to the landing page.
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
});
