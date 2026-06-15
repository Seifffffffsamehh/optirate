/**
 * @file news-service.js — OptiRate News Ticker Service
 *
 * Provides a lightweight news feed component used on the dashboard:
 *  - fetchLatestNews(): Retrieves the latest financial news articles from
 *    the backend /v2/news endpoint, with optional limit and keyword filtering.
 *  - renderNewsTicker(): Renders the fetched articles into a vertically
 *    stacked list inside a specified container element.
 *  - Auto-initializes on page load if a #news-ticker-container element exists.
 */

/**
 * Fetches the latest news articles from the backend API.
 *
 * @async
 * @param {number} [limit=5] - Maximum number of articles to retrieve.
 * @param {string} [keyword=""] - Optional keyword to filter articles by topic.
 * @returns {Promise<Array<Object>>} An array of news article objects, or an
 *          empty array if the request fails.
 */
async function fetchLatestNews(limit = 5, keyword = "") {
    try {
        const query = new URLSearchParams();
        if (limit) query.append('limit', limit);
        if (keyword) query.append('keyword', keyword);
        
        const res = await fetch(`${API_BASE_URL}/v2/news?${query.toString()}`);
        if (!res.ok) throw new Error('Failed to fetch news');
        
        const data = await res.json();
        return data.data || [];
    } catch (e) {
        console.error("News API Error:", e);
        return [];
    }
}

/**
 * Renders an array of news articles into an HTML list inside the given container.
 * Each article displays its title (as a link), source badge, and publication date.
 * If no articles are available, a "No news available" placeholder is shown.
 *
 * @param {string} containerId - The DOM id of the container element to render into.
 * @param {Array<Object>} newsItems - Array of news article objects with properties:
 *        { title, url, source, published_at }.
 */
function renderNewsTicker(containerId, newsItems) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // Show a placeholder if there are no articles to display
    if (newsItems.length === 0) {
        container.innerHTML = '<p style="padding: 10px; color: var(--text-muted);">No news available at the moment.</p>';
        return;
    }
    
    let html = '<ul style="list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 15px;">';
    newsItems.forEach(item => {
        // Format the publication date; fall back to "Just now" if missing/invalid
        let displayDate = 'Just now';
        if (item.published_at) {
            try {
                displayDate = new Date(item.published_at).toLocaleDateString();
            } catch(e) {}
        }

        html += `
            <li style="border-bottom: 1px solid var(--border-color); padding-bottom: 10px;">
                <a href="${item.url}" target="_blank" style="color: #fff; text-decoration: none; font-weight: 500; display: block; margin-bottom: 5px;">
                    ${item.title}
                </a>
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-muted);">
                    <span><i class="source-badge" style="background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px;">${item.source}</i></span>
                    <span>${displayDate}</span>
                </div>
            </li>
        `;
    });
    html += '</ul>';
    
    container.innerHTML = html;
}

/**
 * Auto-initialization: On DOMContentLoaded, if a #news-ticker-container
 * element exists on the page, fetch the 4 most recent articles and render them.
 */
document.addEventListener('DOMContentLoaded', async () => {
    if (document.getElementById('news-ticker-container')) {
        const news = await fetchLatestNews(4);
        renderNewsTicker('news-ticker-container', news);
    }
});
