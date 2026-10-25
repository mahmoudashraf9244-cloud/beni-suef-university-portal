// Run before CSS to avoid a flash of the wrong theme.
(() => {
    let preference;
    try { preference = localStorage.getItem('bsu-theme'); } catch (_) { /* Storage can be blocked. */ }
    const dark = preference === 'dark' || (preference !== 'light' && window.matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
})();
