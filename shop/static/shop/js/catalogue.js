// Enhance ordinary GET links/forms; a failed request falls back to full navigation.
(() => {
    const form = document.getElementById('catalogue-filters');
    const announcement = document.getElementById('catalogue-announcement');
    if (!form || !announcement || !window.fetch || !window.AbortController) return;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let pending;
    let requestId = 0;
    const syncFilters = (url) => {
        form.elements.q.value = url.searchParams.get('q') || '';
        form.elements.category.value = url.searchParams.get('category') || '';
    };
    const navigate = async (url, addHistory = true) => {
        const id = ++requestId;
        pending?.abort();
        pending = new AbortController();
        const controller = pending;
        const current = document.getElementById('catalogue-results');
        current.setAttribute('aria-busy', 'true');
        announcement.textContent = announcement.dataset.loading;
        const timeout = window.setTimeout(() => controller.abort(), 12000);
        try {
            const response = await fetch(url, { signal: controller.signal, credentials: 'same-origin' });
            if (!response.ok || response.redirected) throw new Error('Full navigation required');
            const page = new DOMParser().parseFromString(await response.text(), 'text/html');
            const next = page.getElementById('catalogue-results');
            if (id !== requestId) return;
            if (!next) throw new Error('Missing results');
            if (page.documentElement.lang !== document.documentElement.lang) throw new Error('Language changed');
            // Commit URL and content together, only for the latest request.
            if (addHistory) history.pushState({ catalogue: true }, '', url);
            current.replaceWith(next);
            syncFilters(url);
            document.title = page.title;
            const count = next.querySelector('#results-count').textContent;
            const position = next.querySelector('.page-position')?.textContent || '';
            announcement.textContent = `${count}. ${position}`;
            next.focus({ preventScroll: true });
            next.scrollIntoView({ block: 'start', behavior: reducedMotion.matches ? 'instant' : 'smooth' });
            if (!reducedMotion.matches && next.animate) {
                next.animate([{ opacity: .25, transform: 'translateY(12px)' }, { opacity: 1, transform: 'translateY(0)' }], { duration: 300, easing: 'ease-out' });
            }
        } catch (_) {
            if (id === requestId) window.location.assign(url.href);
        } finally {
            clearTimeout(timeout);
            if (id === requestId) document.getElementById('catalogue-results')?.setAttribute('aria-busy', 'false');
        }
    };
    document.addEventListener('click', (event) => {
        const link = event.target.closest('a[data-catalogue-link]');
        if (!link || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || link.target || link.hasAttribute('download')) return;
        const url = new URL(link.href);
        if (url.origin !== location.origin || url.pathname !== location.pathname) return;
        event.preventDefault();
        navigate(url);
    });
    form.addEventListener('submit', (event) => {
        event.preventDefault();
        const url = new URL(form.action);
        url.search = new URLSearchParams(new FormData(form)).toString();
        navigate(url);
    });
    window.addEventListener('popstate', () => navigate(new URL(location.href), false));
})();
