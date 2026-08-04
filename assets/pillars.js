/** Pillar cards: click to reveal detail panel */
(function () {
  function init() {
    const cards = document.querySelectorAll("[data-pillar]");
    const details = document.querySelectorAll("[data-pillar-detail]");
    if (!cards.length) return;

    function open(id) {
      cards.forEach((c) => c.classList.toggle("is-active", c.dataset.pillar === id));
      details.forEach((d) =>
        d.classList.toggle("is-open", d.dataset.pillarDetail === id),
      );
    }

    cards.forEach((card) => {
      card.addEventListener("click", () => open(card.dataset.pillar));
      card.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          open(card.dataset.pillar);
        }
      });
    });

    open(cards[0].dataset.pillar);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
