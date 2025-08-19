// Initialize particles.js
particlesJS.load('particles-js', '/static/js/particles.json', function() {
  console.log('particles.js loaded - callback');
});

// Initialize particles.js
particlesJS.load('particles-js', '/static/js/particles.json', function() {
  console.log('particles.js loaded - callback');
});

// Sidebar toggle with smooth transition and focus management
document.addEventListener("DOMContentLoaded", function () {
  const sidebarToggle = document.getElementById('sidebar-toggle');
  const sidebar = document.getElementById('sidebar');

  if (sidebarToggle && sidebar) {
    // Ensure sidebar is visible by default
    if (!sidebar.classList.contains('active')) {
      sidebar.classList.add('active');
      sidebar.style.display = 'block';
      sidebarToggle.setAttribute('aria-expanded', 'true');
    }

    sidebarToggle.addEventListener('click', () => {
      sidebar.classList.toggle('active');
      if (sidebar.classList.contains('active')) {
        sidebar.style.display = 'block';
        sidebarToggle.setAttribute('aria-expanded', 'true');
        sidebarToggle.focus();
      } else {
        sidebar.style.display = 'none';
        sidebarToggle.setAttribute('aria-expanded', 'false');
      }
    });
  }
});

// Light/Dark mode toggle with smooth transition
const modeToggle = document.getElementById('mode-toggle');
const body = document.body;

if (modeToggle) {
  modeToggle.addEventListener('click', () => {
    body.classList.toggle('dark-mode');
    if (body.classList.contains('dark-mode')) {
      modeToggle.textContent = '☀️';
      document.documentElement.style.setProperty('--background-color', '#121212');
      document.documentElement.style.setProperty('--text-color', '#e0e0e0');
    } else {
      modeToggle.textContent = '🌙';
      document.documentElement.style.setProperty('--background-color', '#ffffff');
      document.documentElement.style.setProperty('--text-color', '#121212');
    }
  });
}

fetch("../footer.html") // go one folder up

// script.js
document.addEventListener("DOMContentLoaded", function () {
  fetch("footer.html")
    .then(res => res.text())
    .then(data => {
      document.getElementById("footer-placeholder").innerHTML = data;
    })
    .catch(err => console.error("Footer load error:", err));
});


document.querySelector('.analysis-form-container')?.classList.add('loading');
