/**
 * Garment Core — Navigasyon yardımcıları
 * Sticky header scroll efekti, smooth scroll, bottom nav
 */
(document => {
    const header = document.querySelector('[data-sticky-nav]');
    if (header) {
        let lastScroll = 0;
        window.addEventListener('scroll', () => {
            const scrolled = window.scrollY > 50;
            header.classList.toggle('scrolled', scrolled);
            header.classList.toggle('bg-opacity-90', scrolled);
            header.classList.toggle('backdrop-blur-md', scrolled);
            lastScroll = window.scrollY;
        });
    }

    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href === '#') return;
            const target = document.querySelector(href);
            if (target) {
                e.preventDefault();
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
})();
