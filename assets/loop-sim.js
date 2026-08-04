/**
 * Loop simulator — step through one agent turn (reason → act → observe → exit).
 * Scenario mirrors Yar's OpenAI chat.completions tool loop (see loop/agent.py).
 */
(function () {
  const STEPS = [
    {
      phase: "start",
      iter: 0,
      en: "User asks to schedule lunch Friday 1pm. Working memory has system + history + this user message.",
      fa: "کاربر ناهار جمعه ساعت ۱ را می‌خواهد. حافظهٔ کاری: سیستم + تاریخچه + این پیام.",
      messages: [
        "system: SOUL + clock + …",
        "user: schedule lunch Friday 1pm",
      ],
      model: "—",
    },
    {
      phase: "reason",
      iter: 1,
      en: "Iteration 1 — reason: model returns a tool_call (not a final reply).",
      fa: "تکرار ۱ — استدلال: مدل tool_call می‌دهد (هنوز پاسخ نهایی نیست).",
      messages: [
        "system: SOUL + clock + …",
        "user: schedule lunch Friday 1pm",
        "assistant: tool_calls=[create_event]",
      ],
      model: 'tool_calls: create_event({title:"Lunch", …})',
    },
    {
      phase: "act",
      iter: 1,
      en: "Act: your code runs create_event and gets a string result (not the model).",
      fa: "عمل: کد شما create_event را اجرا می‌کند و یک رشته نتیجه می‌گیرد.",
      messages: [
        "system: SOUL + clock + …",
        "user: schedule lunch Friday 1pm",
        "assistant: tool_calls=[create_event]",
      ],
      model: 'execute → "created event id=42"',
    },
    {
      phase: "observe",
      iter: 1,
      en: "Observe: append role:tool with the output. messages is mutated in place — this is the traced working memory.",
      fa: "مشاهده: role:tool با خروجی اضافه می‌شود. messages درجا تغییر می‌کند — همان حافظهٔ کاری ردیابی‌شده.",
      messages: [
        "system: SOUL + clock + …",
        "user: schedule lunch Friday 1pm",
        "assistant: tool_calls=[create_event]",
        'tool: "created event id=42"',
      ],
      model: "ready for next LLM call",
    },
    {
      phase: "reason",
      iter: 2,
      en: "Iteration 2 — reason: model sees the tool result and replies to the human (no tool_calls).",
      fa: "تکرار ۲ — استدلال: مدل نتیجهٔ ابزار را می‌بیند و به انسان جواب می‌دهد (بدون tool_calls).",
      messages: [
        "system: SOUL + clock + …",
        "user: schedule lunch Friday 1pm",
        "assistant: tool_calls=[create_event]",
        'tool: "created event id=42"',
        "assistant: Done — lunch is on Friday at 1.",
      ],
      model: "content: final reply (no tools)",
    },
    {
      phase: "exit",
      iter: 2,
      en: "Guardrail 1: no tool_calls → return reply. Turn ends. (Guardrail 2 would be: hit max_iterations.)",
      fa: "حفاظ ۱: بدون tool_calls → برگرداندن پاسخ. نوبت تمام. (حفاظ ۲: رسیدن به max_iterations.)",
      messages: [
        "system: SOUL + clock + …",
        "user: schedule lunch Friday 1pm",
        "assistant: tool_calls=[create_event]",
        'tool: "created event id=42"',
        "assistant: Done — lunch is on Friday at 1.",
      ],
      model: "LoopResult.reply set · done",
    },
  ];

  function t(step) {
    return document.body.dataset.lang === "fa" ? step.fa : step.en;
  }

  function render(root, i) {
    const step = STEPS[i];
    const msgUl = root.querySelector("[data-sim-messages]");
    const modelEl = root.querySelector("[data-sim-model]");
    const narr = root.querySelector("[data-sim-narration]");
    const meta = root.querySelector("[data-sim-meta]");
    const prev = root.querySelector("[data-sim-prev]");
    const next = root.querySelector("[data-sim-next]");

    msgUl.innerHTML = step.messages
      .map((m, idx) => {
        const last = idx === step.messages.length - 1;
        return `<li class="${last ? "hl" : ""}">${m}</li>`;
      })
      .join("");
    modelEl.textContent = step.model;
    narr.textContent = t(step);
    meta.textContent =
      document.body.dataset.lang === "fa"
        ? `گام ${i + 1}/${STEPS.length} · تکرار ${step.iter || "—"} · ${step.phase}`
        : `step ${i + 1}/${STEPS.length} · iter ${step.iter || "—"} · ${step.phase}`;

    prev.disabled = i <= 0;
    next.disabled = i >= STEPS.length - 1;
    next.textContent =
      document.body.dataset.lang === "fa"
        ? i >= STEPS.length - 1
          ? "پایان"
          : "گام بعد"
        : i >= STEPS.length - 1
          ? "Done"
          : "Next step";
  }

  function bind(root) {
    let i = 0;
    const go = (n) => {
      i = Math.max(0, Math.min(STEPS.length - 1, n));
      render(root, i);
    };
    root.querySelector("[data-sim-prev]").addEventListener("click", () => go(i - 1));
    root.querySelector("[data-sim-next]").addEventListener("click", () => go(i + 1));
    root.querySelector("[data-sim-reset]").addEventListener("click", () => go(0));

    // Re-render narration when language toggles
    document.querySelectorAll("[data-lang-btn]").forEach((btn) => {
      btn.addEventListener("click", () => setTimeout(() => render(root, i), 0));
    });

    go(0);
  }

  function init() {
    document.querySelectorAll("[data-loop-sim]").forEach(bind);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
