/** Minimal quiz: options must be equal length so layout doesn't leak the answer. */
(function () {
  function feedback(el, ok, en, fa) {
    const lang = document.body.dataset.lang === "fa" ? "fa" : "en";
    el.textContent = lang === "fa" ? fa : en;
    el.className = "quiz-feedback " + (ok ? "ok" : "bad");
  }

  function bindQuiz(root) {
    const answer = root.dataset.answer;
    const buttons = root.querySelectorAll("[data-choice]");
    const out = root.querySelector(".quiz-feedback");
    let locked = false;

    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        if (locked) return;
        locked = true;
        const choice = btn.dataset.choice;
        const correct = choice === answer;
        buttons.forEach((b) => {
          if (b.dataset.choice === answer) b.classList.add("is-correct");
          else if (b === btn) b.classList.add("is-wrong");
          b.disabled = true;
        });
        if (correct) {
          feedback(
            out,
            true,
            root.dataset.okEn || "Correct.",
            root.dataset.okFa || "درست.",
          );
        } else {
          feedback(
            out,
            false,
            root.dataset.badEn || "Not quite — look at the highlighted option.",
            root.dataset.badFa || "نه‌چندان — گزینهٔ درست مشخص شده است.",
          );
        }
      });
    });
  }

  function init() {
    document.querySelectorAll("[data-quiz]").forEach(bindQuiz);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
