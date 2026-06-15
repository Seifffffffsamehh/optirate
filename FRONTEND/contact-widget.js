/**
 * @file contact-widget.js — OptiRate Floating Feedback / Contact Widget
 *
 * Dynamically injects a floating action button (FAB) into the bottom-right
 * corner of every page. When clicked, it reveals a slim input bar where the
 * user can type feedback or a question. Submitting opens the user's default
 * email client via a mailto: link addressed to optirate0@gmail.com.
 *
 * Interaction highlights:
 *  - Toggle open/close with the FAB button (chat ↔ ✕ icon swap).
 *  - Submit via the send button or by pressing Enter.
 *  - Dismiss the bar by pressing Escape.
 */
document.addEventListener("DOMContentLoaded", () => {

    // --- 1. Create Widget Container ---
    // The entire widget (toggle button + input bar) is built programmatically
    // so it can be included on any page without touching the page's HTML.
    const widget = document.createElement('div');
    widget.id = 'contact-widget';
    widget.className = 'contact-widget';
    
    // --- 2. Widget HTML (Premium UI) ---
    // Contains a hidden input bar and a visible floating toggle button.
    // Two SVG icons are used: one for "open" (chat bubble) and one for "close" (✕).
    widget.innerHTML = `
        <div id="contact-bar" class="contact-bar hidden">
            <input type="text" id="contact-input" placeholder="Feedback or questions..." aria-label="Message to OptiRate">
            <button id="contact-send-btn" title="Send Email">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            </button>
        </div>
        <button id="contact-toggle" class="contact-toggle" title="Contact Us">
            <svg id="toggle-icon-open" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
            <svg id="toggle-icon-close" class="hidden" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </button>
    `;
    
    document.body.appendChild(widget);
    
    // --- 3. Cache DOM References ---
    const toggleBtn = document.getElementById('contact-toggle');
    const contactBar = document.getElementById('contact-bar');
    const openIcon = document.getElementById('toggle-icon-open');
    const closeIcon = document.getElementById('toggle-icon-close');
    const sendBtn = document.getElementById('contact-send-btn');
    const input = document.getElementById('contact-input');
    
    // --- 4. Toggle Interaction ---
    // Clicking the FAB alternates between showing/hiding the input bar
    // and swapping the chat-bubble icon with the close (✕) icon.
    toggleBtn.addEventListener('click', () => {
        const isHidden = contactBar.classList.contains('hidden');
        if (isHidden) {
            contactBar.classList.remove('hidden');
            openIcon.classList.add('hidden');
            closeIcon.classList.remove('hidden');
            input.focus();
        } else {
            contactBar.classList.add('hidden');
            openIcon.classList.remove('hidden');
            closeIcon.classList.add('hidden');
        }
    });
    
    // --- 5. Send Mechanism (mailto integration) ---
    // Composes a mailto: URL with the user's message as the email body
    // and opens the system's default email client. After sending, the
    // input is cleared and the bar collapses automatically.
    const sendMessage = () => {
        const message = input.value.trim();
        if (message) {
            const subject = encodeURIComponent("OptiRate User Feedback");
            const body = encodeURIComponent(message);
            const mailtoUrl = `mailto:optirate0@gmail.com?subject=${subject}&body=${body}`;
            
            // Open user's email client
            window.location.href = mailtoUrl;
            
            // Reset and close
            input.value = '';
            contactBar.classList.add('hidden');
            openIcon.classList.remove('hidden');
            closeIcon.classList.add('hidden');
        }
    };
    
    sendBtn.addEventListener('click', sendMessage);
    
    // Allow submitting by pressing Enter inside the input field
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // --- 6. Dismiss on Escape ---
    // Close on escape key (only when the bar is currently visible)
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !contactBar.classList.contains('hidden')) {
            contactBar.classList.add('hidden');
            openIcon.classList.remove('hidden');
            closeIcon.classList.add('hidden');
        }
    });
});
