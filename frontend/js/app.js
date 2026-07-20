const PROD_API_URL = "http://ainewspulse-production-402d.up.railway.app";
const LOCAL_API_URL = "http://localhost:8000/v1";
const API_BASE_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? LOCAL_API_URL
    : PROD_API_URL;

document.addEventListener("DOMContentLoaded", () => {
    // Determine which page is loading
    const isArchivePage = window.location.pathname.includes("archive.html");

    if (isArchivePage) {
        loadArchive();
    } else {
        loadDigest();
    }
});

/**
 * Fetches the digest for today, or a specific date if provided in the URL query parameters.
 */
async function loadDigest() {
    try {
        // Support linking from the archive page via ?date=YYYY-MM-DD
        const urlParams = new URLSearchParams(window.location.search);
        const dateParam = urlParams.get('date');

        const endpoint = dateParam
            ? `${API_BASE_URL}/digest/${dateParam}`
            : `${API_BASE_URL}/digest/today`;

        const response = await fetch(endpoint);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
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
    document.getElementById("executive-summary").innerHTML = marked.parse(summaryText);

    // 3. Parse and Inject Markdown Categories
    const markdown = data.markdown_content;
    const sections = parseMarkdownSections(markdown);

    const container = document.getElementById("categories-container");
    container.innerHTML = ""; // Clear placeholders

    sections.forEach((section, index) => {
        // Create Accordion Container
        const accordionItem = document.createElement("div");
        accordionItem.className = `accordion-item glass-panel ${index === 0 ? 'active' : ''}`;

        // Create Accordion Header
        const header = document.createElement("button");
        header.className = "accordion-header";
        header.innerHTML = `
            <span>${section.title}</span>
            <span class="accordion-icon">▼</span>
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
