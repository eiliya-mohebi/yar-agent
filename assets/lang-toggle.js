/** Language toggle: persists EN | fa in localStorage */
(function () {
  const KEY = "yar-lesson-lang";

  function apply(lang) {
    const next = lang === "fa" ? "fa" : "en";
    document.body.dataset.lang = next;
    document.documentElement.lang = next === "fa" ? "fa" : "en";
    document.documentElement.dir = next === "fa" ? "rtl" : "ltr";
    document.querySelectorAll("[data-lang-btn]").forEach((btn) => {
      btn.setAttribute("aria-pressed", String(btn.dataset.langBtn === next));
    });
    try {
      localStorage.setItem(KEY, next);
    } catch (_) {
      /* ignore */
    }
  }

  function init() {
    let start = "en";
    try {
      start = localStorage.getItem(KEY) || start;
    } catch (_) {
      /* ignore */
    }
    apply(start);
    document.querySelectorAll("[data-lang-btn]").forEach((btn) => {
      btn.addEventListener("click", () => apply(btn.dataset.langBtn));
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
