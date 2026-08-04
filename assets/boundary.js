/** Boundary drill: is this Harness or Loop? Immediate feedback. */
(function () {
  function bind(item) {
    const answer = item.dataset.answer;
    const fb = item.querySelector(".fb");
    let locked = false;

    item.querySelectorAll("[data-pick]").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (locked) return;
        locked = true;
        const pick = btn.dataset.pick;
        const ok = pick === answer;
        item.querySelectorAll("[data-pick]").forEach((b) => {
          if (b.dataset.pick === answer) b.classList.add("is-correct");
          else if (b === btn) b.classList.add("is-wrong");
          b.disabled = true;
        });
        const lang = document.body.dataset.lang === "fa" ? "fa" : "en";
        if (ok) {
          fb.className = "fb ok";
          fb.textContent =
            lang === "fa"
              ? item.dataset.okFa || "درست."
              : item.dataset.okEn || "Correct.";
        } else {
          fb.className = "fb bad";
          fb.textContent =
            lang === "fa"
              ? item.dataset.badFa || "نه‌چندان."
              : item.dataset.badEn || "Not quite.";
        }
      });
    });
  }

  function init() {
    document.querySelectorAll("[data-boundary]").forEach(bind);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
