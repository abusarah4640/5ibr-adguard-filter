(() => {
  "use strict";

  const root = document.documentElement;
  const storedTheme = localStorage.getItem("fivebr-theme");
  const preferredTheme = storedTheme || root.dataset.themePreference || "auto";

  function resolvedTheme(theme) {
    return theme === "auto"
      ? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
      : theme;
  }

  function applyTheme(theme) {
    root.dataset.bsTheme = resolvedTheme(theme);
    root.dataset.themePreference = theme;
    document.querySelectorAll("[data-theme-label]").forEach((label) => {
      label.textContent = label.dataset[`label${theme[0].toUpperCase()}${theme.slice(1)}`];
    });
    document.querySelectorAll("[data-theme-icon]").forEach((icon) => {
      icon.className = `bi ${theme === "dark" ? "bi-moon-stars" : theme === "light" ? "bi-sun" : "bi-circle-half"}`;
    });
  }

  applyTheme(preferredTheme);
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (root.dataset.themePreference === "auto") applyTheme("auto");
  });

  document.querySelector("[data-theme-toggle]")?.addEventListener("click", () => {
    const order = ["light", "dark", "auto"];
    const next = order[(order.indexOf(root.dataset.themePreference) + 1) % order.length];
    localStorage.setItem("fivebr-theme", next);
    applyTheme(next);
  });

  document.querySelectorAll(".toast").forEach((element) => {
    bootstrap.Toast.getOrCreateInstance(element, { delay: 5500 }).show();
  });

  document.querySelectorAll('form[method="post"]').forEach((form) => {
    form.addEventListener("submit", () => {
      const button = form.querySelector('button[type="submit"], button:not([type])');
      if (button && !button.disabled) {
        button.classList.add("is-loading");
        button.setAttribute("aria-busy", "true");
      }
    });
  });

  document.querySelectorAll(".table").forEach((table) => {
    table.classList.add("table-hover");
  });
})();
