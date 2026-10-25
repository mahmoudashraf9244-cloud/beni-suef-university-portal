document.querySelectorAll('[data-password-toggle]').forEach((toggle) => {
    const input = document.getElementById(toggle.dataset.passwordToggle);
    if (!input) return;
    toggle.hidden = false;
    toggle.addEventListener('click', () => {
        const wasVisible = input.type === 'text';
        input.type = wasVisible ? 'password' : 'text';
        toggle.textContent = wasVisible ? toggle.dataset.show : toggle.dataset.hide;
        toggle.setAttribute('aria-label', wasVisible ? toggle.dataset.showLabel : toggle.dataset.hideLabel);
        toggle.setAttribute('aria-pressed', String(!wasVisible));
    });
});
