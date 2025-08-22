(function () {
  const key = "theme";
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const saved = localStorage.getItem(key);
  const theme = saved || (prefersDark ? "dark" : "light");
  document.documentElement.setAttribute("data-theme", theme);
  const logo = document.getElementById("brand-logo");
  function setLogo(t) {
    logo.src = t==="dark"
      ? "/static/img/logo-dark.svg"
      : "/static/img/logo-light.svg";
  }
  setLogo(theme);
  document.getElementById("theme-toggle")
    .addEventListener("click", () => {
      const t = document.documentElement.getAttribute("data-theme")==="dark"?"light":"dark";
      document.documentElement.setAttribute("data-theme",t);
      localStorage.setItem(key,t);
      setLogo(t);
    });
})();

// theme.js excerpt
function setLogo(theme) {
  document.getElementById("brand-logo").src =
    theme === "dark"
      ? "/static/img/logo-dark.svg"
      : "/static/img/logo-light.svg";
}

// app/static/js/main.js

document.addEventListener('DOMContentLoaded', () => {
  // 1. Theme toggle (light ↔ dark)
  const themeToggle = document.querySelector('#theme-toggle');
  const savedTheme = localStorage.getItem('theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  if (themeToggle) {
    themeToggle.checked = savedTheme === 'dark';
    themeToggle.addEventListener('change', () => {
      const theme = themeToggle.checked ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('theme', theme);
    });
  }

  // 2. Mobile nav toggle
  const navToggle = document.querySelector('#nav-toggle');
  if (navToggle) {
    navToggle.addEventListener('click', () => {
      document.body.classList.toggle('nav-open');
    });
  }

  // 3. Smooth-scroll for in-page links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', e => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // 4. Reveal .feature cards on scroll
  const features = document.querySelectorAll('.feature');
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries, obs) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed');
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.2 });

    features.forEach(card => observer.observe(card));
  } else {
    // Fallback: reveal all immediately
    features.forEach(card => card.classList.add('revealed'));
  }
});

