const PROD_API_URL = "https://ainewspulse-production-402d.up.railway.app/v1";
const LOCAL_API_URL = "http://localhost:8000/v1";
const API_BASE_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? LOCAL_API_URL
    : PROD_API_URL;

document.addEventListener("DOMContentLoaded", () => {
    // Determine which page is loading
    const isArchivePage = window.location.pathname.includes("archive.html");
    const isTodayPage = window.location.pathname.includes("today.html");

    if (isArchivePage) {
        loadArchive();
    } else if (isTodayPage) {
        loadDigest(false);
    } else {
        loadDigest(true);
    }
});

/**
 * Fetches the digest for today, or the latest if on Home page
 */
async function loadDigest(isHome = false) {
    try {
        // Support linking from the archive page via ?date=YYYY-MM-DD
        const urlParams = new URLSearchParams(window.location.search);
        const dateParam = urlParams.get('date');

        let endpoint = `${API_BASE_URL}/digest/today`;
        if (dateParam) {
            endpoint = `${API_BASE_URL}/digest/${dateParam}`;
        } else if (isHome) {
            endpoint = `${API_BASE_URL}/digest/latest`;
        }

        const response = await fetch(endpoint);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        // Show banner if Home page but digest is not from today
        if (isHome && !data.is_today) {
            const banner = document.getElementById("nothing-new-banner");
            if (banner) banner.classList.remove("hidden");
        }

        renderDigest(data);

    } catch (error) {
        console.error("Failed to load digest:", error);
        document.getElementById("last-updated-text").textContent = "Update failed or digest unavailable.";
        document.getElementById("error-container").classList.remove("hidden");
    }
}

/**
 * Parses the Markdown/JSON and injects it into the DOM structure
 */
function renderDigest(data) {
    // 1. Update Status Bar
    const dateStr = new Date(data.generated_at).toLocaleString();
    document.getElementById("last-updated-text").textContent = `Generated on: ${dateStr}`;

    // 2. Inject Executive Summary (Hero Card)
    const summaryText = data.highlight_json?.executive_summary || "No executive summary available for this date.";
    document.getElementById("executive-summary").innerHTML = `<md-ripple></md-ripple>${marked.parse(summaryText)}`;

    // 3. Parse and Inject Markdown Categories
    const markdown = data.markdown_content;
    const sections = parseMarkdownSections(markdown);

    const container = document.getElementById("categories-container");
    container.innerHTML = ""; // Clear placeholders

    sections.forEach((section, index) => {
        // Create Accordion Container
        const accordionItem = document.createElement("div");
        accordionItem.className = `accordion-item m3-card ${index === 0 ? 'active' : ''}`;
        accordionItem.style.position = 'relative';

        // Add M3 Elevation
        accordionItem.innerHTML = '<md-elevation></md-elevation>';

        // Create Accordion Header
        const header = document.createElement("button");
        header.className = "accordion-header";
        
        // Add Category Count Badge
        const count = data.metadata_json?.category_counts?.[section.title];
        const countBadge = count ? `<span class="badge count-badge">${count} articles</span>` : '';
        
        header.innerHTML = `
            <md-ripple></md-ripple>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span>${section.title}</span>
                ${countBadge}
            </div>
            <md-icon class="accordion-icon">expand_more</md-icon>
        `;

        // Create Accordion Content Container
        const content = document.createElement("div");
        content.className = "accordion-content";

        // Parse the markdown bullets into HTML
        const inner = document.createElement("div");
        inner.className = "accordion-inner";
        inner.innerHTML = marked.parse(section.content);

        content.appendChild(inner);
        accordionItem.appendChild(header);
        accordionItem.appendChild(content);
        container.appendChild(accordionItem);

        // Setup Toggle Logic for Collapsible Sections
        header.addEventListener("click", () => {
            const isActive = accordionItem.classList.contains("active");

            if (isActive) {
                accordionItem.classList.remove("active");
                content.style.maxHeight = null;
            } else {
                accordionItem.classList.add("active");
                content.style.maxHeight = content.scrollHeight + "px";
            }
        });

        // Auto-expand the very first section on load
        if (index === 0) {
            setTimeout(() => {
                content.style.maxHeight = content.scrollHeight + "px";
            }, 50);
        }
    });

    // Reveal the fully rendered content
    document.getElementById("digest-content").classList.remove("hidden");
}

/**
 * Helper to split the raw markdown string into logical sections based on H2 tags
 */
function parseMarkdownSections(markdown) {
    // Split text by H2 markdown tags (## )
    const parts = markdown.split(/\n## /);

    // parts[0] is the main title (# AI News Pulse) and intro, we skip it for the accordions.
    const sections = [];
    for (let i = 1; i < parts.length; i++) {
        const text = parts[i];
        const lineBreakIndex = text.indexOf('\n');

        let title = "";
        let content = "";

        if (lineBreakIndex !== -1) {
            title = text.substring(0, lineBreakIndex).trim();
            content = text.substring(lineBreakIndex + 1).trim();
        } else {
            title = text.trim();
        }

        // Clean up markdown formatting from titles if present
        title = title.replace(/\*\*/g, '');

        sections.push({ title, content });
    }
    return sections;
}

/**
 * Fetches the paginated list of historical digests for the archive page
 */
async function loadArchive() {
    try {
        const response = await fetch(`${API_BASE_URL}/digest/archive/list`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const digests = await response.json();
        renderArchiveList(digests);

    } catch (error) {
        console.error("Failed to load archive:", error);
        document.getElementById("archive-list").innerHTML = "";
        document.getElementById("error-container").classList.remove("hidden");
    }
}

/**
 * Renders the archive list grid
 */
function renderArchiveList(digests) {
    const container = document.getElementById("archive-list");
    container.innerHTML = "";

    if (digests.length === 0) {
        container.innerHTML = "<p class='loading-text'>No past digests found.</p>";
        return;
    }

    digests.forEach(digest => {
        const dateObj = new Date(digest.date);
        const dateString = dateObj.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            timeZone: 'UTC'
        });

        const summary = digest.highlight_json?.executive_summary || "No summary available.";

        const card = document.createElement("a");
        // Linking back to index.html with the target date!
        card.href = `index.html?date=${digest.date}`;
        card.className = "archive-card glass-panel";
        card.innerHTML = `
            <div class="archive-date">${dateString}</div>
            <div class="archive-snippet">${summary}</div>
        `;

        container.appendChild(card);
    });
}
