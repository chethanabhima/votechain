// Vote Chain — Main JS

// Animate elements on scroll
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.style.opacity = '1';
      e.target.style.transform = 'translateY(0)';
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.glass, .block-card, .audit-section, .admin-section').forEach(el => {
  el.style.opacity = '0';
  el.style.transform = 'translateY(16px)';
  el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
  observer.observe(el);
});

// Tally bars animate in
document.querySelectorAll('.tally-bar').forEach(bar => {
  const width = bar.style.width;
  bar.style.width = '0';
  setTimeout(() => { bar.style.width = width; }, 300);
});

// Copy hash on click
document.querySelectorAll('.hash-val').forEach(el => {
  el.style.cursor = 'pointer';
  el.title = 'Click to copy';
  el.addEventListener('click', () => {
    navigator.clipboard.writeText(el.textContent.trim()).then(() => {
      const orig = el.textContent;
      el.textContent = '✓ Copied!';
      setTimeout(() => { el.textContent = orig; }, 1200);
    });
  });
});

// Form submit loading state
document.querySelectorAll('form').forEach(form => {
  form.addEventListener('submit', () => {
    const btn = form.querySelector('button[type=submit]');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Processing…';
    }
  });
});
