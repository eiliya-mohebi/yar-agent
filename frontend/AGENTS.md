# Frontend — agent notes

This is the React SPA for Yar. Read [`../AGENTS.md`](../AGENTS.md) first — universal building
rules live there. This file adds frontend-specific conventions.

**Reference:** the UI is a port of the vanilla-JS cockpit at `waku/ops/static/` in
[waku-agent](https://github.com/ShenSeanChen/waku-agent) (`main` @
[`871c4ac`](https://github.com/ShenSeanChen/waku-agent/tree/871c4ac)). Feature-by-feature
blueprint and the old-module → React map: [`../docs/frontend.md`](../docs/frontend.md).

## Stack

- **Plain React SPA** (Vite + TypeScript, strict). **Not Next.js** — do not suggest Next, SSR,
  server components, or file-based routing.
- **Tailwind CSS** for styling. No CSS modules, styled-components, Emotion, or `.module.css`
  files for component styles. Global theme tokens live in `src/index.css`.
- **shadcn/ui** for UI primitives. Add components with `pnpm dlx shadcn@latest add <name>` —
  don't hand-roll what shadcn already ships.
- **React Router** for routing.
- Talks to the Python backend over JSON (`VITE_API_BASE_URL`). No separate auth layer for the
  local dashboard (bound to `127.0.0.1`); do not invent OAuth/SSO unless explicitly asked.

## Package manager

**`pnpm` only.** Do not use `npm install` or `yarn add`. The lockfile is `pnpm-lock.yaml`. If
you see `package-lock.json` or `yarn.lock` appear, that's a bug — delete it.

**Minimum release age: 7 days.** Configured via `.npmrc` (`minimum-release-age=10080` minutes).
pnpm will refuse to install any package version published less than 7 days ago. This defends
against typosquat / compromised-release attacks where a malicious version of a popular package
goes live and gets pulled within hours.

If a fresh package is genuinely required (e.g. urgent security fix in a dep we already use),
override per-install and justify in the commit message — don't lower the global threshold.

## Dependency policy

See universal policy in [`../AGENTS.md`](../AGENTS.md). Frontend-specific:

- **HTTP:** use the native `fetch` API through a thin client in `src/lib/http.ts` and the `api`
  singleton in `src/lib/api.ts`. **No axios, ky, got, superagent, redaxios.**
- **Dates:** use native `Date` and `Intl.DateTimeFormat`. No moment, dayjs, date-fns unless
  genuinely needed.
- **Utilities:** use native `Array` / `Object` / `Map` methods. No lodash, ramda.
- **State:** `useState` / `useReducer` / `useContext` first. Only reach for external state
  libraries when the pain is real.
- **Forms:** native `<form>` + `FormData` first.
- **Validation:** only add a schema library when we actually need runtime validation at
  boundaries.
- **UI components:** shadcn primitives via `pnpm dlx shadcn@latest add <name>`. Don't hand-roll
  what shadcn already ships.

Before adding a package, check:

1. Is there a native browser or TS/JS API that does this?
2. Does shadcn/ui already cover it?
3. Is it small, well-maintained, and worth the maintenance cost?

If yes to (3), add it — but flag the decision in the commit message.

## Layout (to be created during build)

```text
frontend/
├── src/
│   ├── components/        # App components. shadcn primitives under components/ui/
│   ├── lib/               # Framework-agnostic helpers (http, api, env)
│   ├── pages/             # Route-level components (Overview, Loop, Memory, Compare, …)
│   ├── App.tsx            # Router
│   ├── main.tsx
│   └── index.css          # Tailwind directives + global theme tokens
├── index.html
├── vite.config.ts
├── tsconfig.json
├── .npmrc                 # minimum-release-age=10080
└── package.json
```

Keep imports consistent with the `@/*` alias (e.g. `@/lib/api`, `@/components/ui/button`).

## Code style (frontend-specific)

- **TypeScript strict.** No `any` unless there's no alternative; prefer `unknown` and narrow.
- **Small, composable functions and components** over clever abstractions. Three similar lines >
  a premature generic.
- **One component = one file.** Components stay small enough to fit on one screen.
- **Tailwind classes inline.** No CSS modules, styled-components, Emotion, or `.module.css` for
  component styles. Global tokens live in `src/index.css`.
- **Logical CSS properties, always.** Persian is a first-class language and the SPA must work in
  RTL, so use `ms-*`/`me-*`/`ps-*`/`pe-*` and `text-start`/`text-end` — **never** `ml-*`/`mr-*`/
  `text-left`/`text-right`. Any element rendering user or model text gets `dir="auto"`; code,
  model ids, paths, SQL, numbers and the architecture SVG stay explicitly `dir="ltr"`. Full rules:
  [frontend.md §11](../docs/frontend.md#11-rtl-and-bilingual-ui-persian--english).
- **No emojis** in any UI surface (project rule).

## Configuration

- All env reads go through a single `src/lib/env.ts` module that validates required vars at
  boot. Never read `import.meta.env.X` directly in components.
- Env vars are prefixed `VITE_` (Vite convention). Anything not prefixed is not exposed to the
  client.

## Backend integration

- Talks to the Python backend over JSON. URL comes from `VITE_API_BASE_URL` (default
  `http://127.0.0.1:7777`). Prefer a Vite `server.proxy` to that origin during `pnpm dev`.
- Always use `api.get/post/put/patch/delete` from `@/lib/api` — it handles base URL, JSON,
  timeouts, and typed `ApiError`s (including an `isNetworkError` flag that distinguishes
  CORS/network from HTTP errors).
- Full route list and payloads: [`../docs/api.md`](../docs/api.md).
- The dashboard is local-first and bound to loopback. Do not thread secrets through component
  props or invent a client-side auth flow.

## Testing

**No frontend tests.** Do not write `*.test.ts` / `*.test.tsx` files or introduce a test runner.
We verify the frontend manually in the browser plus `pnpm tsc --noEmit` and `pnpm lint`. If you
find yourself reaching for vitest, Playwright, or Cypress — stop. That's not what this project
does. Correctness for shared logic comes from keeping it simple and well-typed, not from a test
suite.

## Anti-patterns (rejected)

- Reading `import.meta.env.X` directly outside `lib/env.ts`.
- Importing an HTTP library when `fetch` would do.
- Mixing client state libraries (Zustand + Jotai + Redux) for one project.
- `any` annotations to silence the type-checker.
- Custom CSS files / styled-components alongside Tailwind.
- Directional utilities (`ml-*`, `mr-*`, `text-left`, `text-right`, `left-0`, `right-0`) — they
  break RTL. Use the logical equivalents.
- Hand-rolled direction detection in JS when `dir="auto"` does it in the browser.
- Re-implementing a shadcn primitive by hand.
- Reaching for Next.js, SSR, or any framework that requires a Node server in front of the SPA.
