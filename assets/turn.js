/** Full-turn step cards — click to reveal detail. */
(function () {
  function init() {
    const steps = document.querySelectorAll("[data-turn]");
    const details = document.querySelectorAll("[data-turn-detail]");
    if (!steps.length) return;

    function open(id) {
      steps.forEach((s) => s.classList.toggle("is-active", s.dataset.turn === id));
      details.forEach((d) =>
        d.classList.toggle("is-open", d.dataset.turnDetail === id),
      );
    }

    steps.forEach((step) => {
      step.addEventListener("click", () => open(step.dataset.turn));
      step.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          open(step.dataset.turn);
        }
      });
    });

    open(steps[0].dataset.turn);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
