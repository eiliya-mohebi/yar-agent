# yar-agent — specs

Three documents describe the system. Read them in this order; each assumes the one before it.

| # | Doc | Answers | Read it when |
|---|-----|---------|--------------|
| 1 | **[ARCHITECTURE.md](ARCHITECTURE.md)** | How the whole thing works — the four pillars, the loop, memory, language support, evals, and what's deliberately out of scope. | Always first. It's the only doc that explains *why*. |
| 2 | **[api.md](api.md)** | The `/api/*` route and payload contract the backend serves on `:7777`. | Building either side of the client/server line. |
| 3 | **[frontend.md](frontend.md)** | The dashboard SPA — shell layout, pages, chat dock, RTL rules, rebuild order. | Building the UI. |

Rules for *how to write the code* live outside this folder, in the AGENTS files:
[`../AGENTS.md`](../AGENTS.md) (universal), [`../backend/AGENTS.md`](../backend/AGENTS.md),
[`../frontend/AGENTS.md`](../frontend/AGENTS.md). Setup and prerequisites:
[`../README.md`](../README.md).

## Start here, by task

| Task | Path through the docs |
|------|-----------------------|
| Rebuild the backend from scratch | [ARCHITECTURE §12](ARCHITECTURE.md#12-rebuild-order-suggested) (rebuild order) → [§§1–7](ARCHITECTURE.md#1-the-whiteboard-file-path-on-every-box) for each step |
| Rebuild the SPA | [frontend.md §14](frontend.md#14-rebuild-order) (rebuild order) → [api.md](api.md) for every call |
| Add a tool | [ARCHITECTURE §5](ARCHITECTURE.md#5-tools), then the deterministic eval rules in [§8](ARCHITECTURE.md#8-ops--eval) |
| Add or change memory behavior | [ARCHITECTURE §6](ARCHITECTURE.md#6-memory), plus [§7](ARCHITECTURE.md#7-language-support-persian-and-english) — every search path is bilingual |
| Add an endpoint | [api.md](api.md) (update it in the same change), then [frontend.md §5](frontend.md#5-dashboarddata-get-apidata) |
| Understand a cut feature | [ARCHITECTURE §13](ARCHITECTURE.md#13-deliberately-out-of-scope) — each cut names the seam it would reattach at |

## Two things to know before you start

**These are a port guide, not a standalone spec.** Contracts are complete; some long literals are
not — prompt texts, the full FTS5 DDL, the token price map, the architecture SVG, design token
values, eval cases. [ARCHITECTURE §14](ARCHITECTURE.md#14-reference-implementation) maps each one to
the file it lives in inside the reference implementation,
[waku-agent](https://github.com/ShenSeanChen/waku-agent), and lists the modules and known defects
**not** to port.

**Persian and English are both required**, and Persian fails silently rather than loudly — an ASCII
tokenizer reduces a Persian sentence to zero tokens, so skills stop matching and memory searches
return empty with no error. If you touch matching, search, prompts, dates, or UI text, read
[ARCHITECTURE §7](ARCHITECTURE.md#7-language-support-persian-and-english) first.
