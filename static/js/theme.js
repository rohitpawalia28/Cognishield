// Shared light/dark theme toggle for every CogniShield page.
(function () {
  const root = document.documentElement;
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const current = () => root.dataset.theme || (media.matches ? "dark" : "light");

  function label(button) {
    const next = current() === "dark" ? "light" : "dark";
    button.setAttribute("aria-label", `Switch to ${next} theme`);
    button.title = `Switch to ${next} theme`;
  }

  document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    label(button);
    button.addEventListener("click", () => {
      const next = current() === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      try { localStorage.setItem("cognishield-theme", next); } catch (_) { /* storage unavailable */ }
      label(button);
    });
  });
})();
