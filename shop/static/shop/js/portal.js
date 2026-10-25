(() => {
    const root = document.documentElement;
    const themeButton = document.querySelector('[data-theme-toggle]');
    const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
    const updateThemeButton = () => {
        if (!themeButton) return;
        const dark = root.dataset.theme === 'dark';
        themeButton.hidden = false;
        themeButton.setAttribute('aria-pressed', String(dark));
        themeButton.setAttribute('aria-label', dark ? themeButton.dataset.lightLabel : themeButton.dataset.darkLabel);
        themeButton.title = themeButton.getAttribute('aria-label');
    };
    updateThemeButton();
    themeButton?.addEventListener('click', () => {
        root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
        try { localStorage.setItem('bsu-theme', root.dataset.theme); } catch (_) { /* Use session theme. */ }
        updateThemeButton();
    });
    systemTheme.addEventListener('change', (event) => {
        try { if (localStorage.getItem('bsu-theme')) return; } catch (_) { return; }
        root.dataset.theme = event.matches ? 'dark' : 'light';
        updateThemeButton();
    });
})();
