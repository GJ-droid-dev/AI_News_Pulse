document.addEventListener("DOMContentLoaded", () => {
    const themeBtn = document.getElementById("theme-toggle");
    
    // 1. Check local storage or system preference for default theme
    const currentTheme = localStorage.getItem("theme");
    
    if (currentTheme) {
        document.body.className = currentTheme;
        updateIcon(currentTheme);
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        // Fallback to system OS preference
        document.body.className = "dark-mode";
        updateIcon("dark-mode");
    }

    // 2. Handle manual toggle
    themeBtn.addEventListener("click", () => {
        if (document.body.classList.contains("dark-mode")) {
            document.body.className = "light-mode";
            localStorage.setItem("theme", "light-mode");
            updateIcon("light-mode");
        } else {
            document.body.className = "dark-mode";
            localStorage.setItem("theme", "dark-mode");
            updateIcon("dark-mode");
        }
    });

    // Helper to swap the moon/sun icon
    function updateIcon(theme) {
        if (theme === "dark-mode") {
            themeBtn.textContent = "☀️";
            themeBtn.setAttribute("aria-label", "Toggle Light Mode");
        } else {
            themeBtn.textContent = "🌙";
            themeBtn.setAttribute("aria-label", "Toggle Dark Mode");
        }
    }
});
