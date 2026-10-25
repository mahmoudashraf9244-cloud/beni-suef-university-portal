// Course URLs remain usable as full pages when JavaScript is unavailable.
(() => {
    if (!window.fetch || !window.AbortController) return;
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const labels = document.body.dataset;
    let activeModal = null;
    let activeRequest = null;
    let opener = null;

    const closeModal = ({ restoreFocus = true } = {}) => {
        activeRequest?.abort();
        activeRequest = null;
        if (!activeModal) return;
        const modal = activeModal;
        activeModal = null;
        document.body.classList.remove('has-course-modal');
        const finish = () => {
            modal.remove();
            if (restoreFocus && opener?.isConnected) opener.focus({ preventScroll: true });
        };
        if (reducedMotion.matches || !modal.animate) return finish();
        const animation = modal.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 160, easing: 'ease-in' });
        animation.addEventListener('finish', finish, { once: true });
    };

    const keepFocusInside = (event) => {
        if (event.key !== 'Tab' || !activeModal) return;
        const controls = [...activeModal.querySelectorAll('button, a[href], input, select, textarea, [tabindex]:not([tabindex="-1"])')]
            .filter((item) => !item.hidden && !item.disabled);
        if (!controls.length) return;
        const first = controls[0];
        const last = controls.at(-1);
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault(); last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault(); first.focus();
        }
    };

    const buildModal = (details, cardLink) => {
        closeModal({ restoreFocus: false });
        opener = cardLink;
        const shell = document.createElement('div');
        shell.className = 'course-modal';
        shell.setAttribute('role', 'dialog');
        shell.setAttribute('aria-modal', 'true');
        const panel = document.createElement('div');
        panel.className = 'course-modal-panel';
        const heading = details.querySelector('h1');
        const headingId = `course-modal-title-${Date.now()}`;
        heading.id = headingId;
        shell.setAttribute('aria-labelledby', headingId);
        const close = document.createElement('button');
        close.type = 'button';
        close.className = 'modal-close';
        close.setAttribute('aria-label', labels.closeDetails);
        close.textContent = '×';
        close.addEventListener('click', () => closeModal());
        shell.addEventListener('click', (event) => { if (event.target === shell) closeModal(); });
        shell.addEventListener('keydown', keepFocusInside);
        if (labels.authenticated !== 'true') {
            details.querySelector('.detail-layout')?.remove();
            details.querySelector('.trainer-panel')?.remove();
            details.classList.add('guest-course-preview');
        }
        panel.append(close, details);
        shell.append(panel);
        document.body.append(shell);
        activeModal = shell;
        document.body.classList.add('has-course-modal');
        close.focus({ preventScroll: true });
        if (!reducedMotion.matches && panel.animate) {
            panel.animate(
                [{ opacity: 0, transform: 'translateY(28px) scale(.97)' }, { opacity: 1, transform: 'none' }],
                { duration: 340, easing: 'cubic-bezier(.2,.8,.2,1)' },
            );
        }
    };

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && activeModal) { event.preventDefault(); closeModal(); }
    });

    document.addEventListener('click', async (event) => {
        const link = event.target.closest('a.activity-card-link');
        if (!link || event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        const url = new URL(link.href);
        if (url.origin !== location.origin) return;
        event.preventDefault();
        closeModal({ restoreFocus: false });
        opener = link;
        const card = link.closest('.activity-card');
        const loading = document.createElement('p');
        loading.className = 'card-loading';
        loading.setAttribute('role', 'status');
        loading.textContent = labels.loadingDetails;
        card.setAttribute('aria-busy', 'true');
        card.append(loading);
        activeRequest = new AbortController();
        const controller = activeRequest;
        const timeout = setTimeout(() => controller.abort(), 12000);
        try {
            const response = await fetch(url, { credentials: 'same-origin', signal: controller.signal });
            if (!response.ok || response.redirected) throw new Error('Use detail page');
            const page = new DOMParser().parseFromString(await response.text(), 'text/html');
            const details = page.querySelector('.detail-card');
            if (!details || page.documentElement.lang !== document.documentElement.lang) throw new Error('Invalid details');
            buildModal(details, link);
        } catch (error) {
            if (error.name !== 'AbortError') location.assign(url.href);
        } finally {
            clearTimeout(timeout);
            if (activeRequest === controller) activeRequest = null;
            loading.remove();
            card.removeAttribute('aria-busy');
        }
    });
})();
