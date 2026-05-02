/**
 * main.js for nutritrack
 * using in dashboard for graphing etc
 */

document.addEventListener('DOMContentLoaded', () => {

    //auto dismiss flash messages after 4 seconds ---
    document.querySelectorAll('.flash').forEach(el => {
        setTimeout(() => {
            el.style.transition = 'opacity 0.5s';
            el.style.opacity = '0';
            setTimeout(() => el.remove(), 500);
        }, 4000);
    });



    // star rating: highlight stars when hovering mouse
    const starRatings = document.querySelectorAll('.star-rating');
    starRatings.forEach(container => {

        const labels = Array.from(container.querySelectorAll('.star-label'));

        labels.forEach((label, idx) => {
            const star = label.querySelector('.star');
            const input = label.querySelector('input');


            label.addEventListener('mouseenter', () => {
                labels.forEach((l, i) => {
                    l.querySelector('.star').style.color = i <= idx ? 'var(--amber)' : 'var(--text-dim)';
                });
            });



            label.addEventListener('mouseleave', () => {
                const checked = container.querySelector('input:checked');
                const checkedIdx = checked ? labels.indexOf(checked.parentElement) : -1;
                labels.forEach((l, i) => {
                    l.querySelector('.star').style.color = i <= checkedIdx ? 'var(--amber)' : 'var(--text-dim)';
                });
            });


            input.addEventListener('change', () => {
                labels.forEach((l, i) => {
                    l.querySelector('.star').style.color = i <= idx ? 'var(--amber)' : 'var(--text-dim)';
                });
            });
        });
    });

    //confirm delete prompts
    document.querySelectorAll('[data-confirm]').forEach(el => {
        el.addEventListener('click', e => {
            if (!confirm(el.dataset.confirm)) e.preventDefault();
        });
    });

});