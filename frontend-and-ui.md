# Frontend and UI Practices

Applies to any client-rendered or server-rendered user interface, in any framework —
React, Vue, Svelte, Angular, Blazor, SwiftUI, Flutter, or plain HTML. Where a rule is
genuinely framework-specific it says so; everything else is a property of building
interfaces, not of the library you build them with.

**Read this before:** creating or modifying components, adding client state, building
forms, wiring up data fetching, or changing anything a user sees.

---

## 1. Core principles

These four sentences generate most of the rest of this document.

1. **The UI is a function of state.** If the same state can render two different screens,
   you have a bug waiting. Derive everything you can; store only what you cannot derive.
2. **Every async operation has four states**, not one: idle, loading, success, error. A UI
   that only handles success is unfinished.
3. **The browser already does this.** Native elements bring focus management, keyboard
   handling, screen-reader semantics, and form submission for free. Re-implementing them
   in `<div>`s means re-implementing all of it, badly.
4. **Users are on worse devices and worse networks than you are.** Assume a mid-range
   phone on a congested network until measurement proves otherwise.

---

## 2. Component design

### 2.1 Size and responsibility

- **Split a component when it has two reasons to change**, not when it hits a line count.
  A 300-line form that renders one form is fine. A 60-line component that both fetches
  data and formats currency is not.
- **Separate "what it looks like" from "where the data comes from."** A presentational
  component takes data as input and emits events; a container fetches, mutates, and
  routes. This is what makes components testable without a network, and reusable in a
  second context.

  ```jsx
  // Presentational: no fetching, no routing, no globals. Trivially testable.
  function InvoiceRow({ invoice, onMarkPaid }) { … }

  // Container: knows about the world.
  function InvoiceRowContainer({ id }) {
    const { data } = useInvoice(id);
    const markPaid = useMarkPaid();
    return <InvoiceRow invoice={data} onMarkPaid={() => markPaid(id)} />;
  }
  ```

- **Do not create an abstraction until the third use.** Two similar components are
  cheaper than one component with a `variant` prop, a `mode` prop, and four booleans.
  Premature component abstraction is the most common source of unmaintainable UI code.
- **Never add a boolean prop that changes layout structure.** `isCompact`, `isModal`,
  `showHeader` — past two of these, the component is really several components sharing a
  file. Split it.

### 2.2 Props and interfaces

- **Make illegal states unrepresentable in the prop types.** Prefer a discriminated union
  over independent booleans:

  ```ts
  // Bad: isLoading && error && data is representable and meaningless.
  type Props = { isLoading: boolean; error?: Error; data?: User };

  // Good: exactly one shape is valid at a time.
  type Props =
    | { status: 'loading' }
    | { status: 'error'; error: Error }
    | { status: 'ready'; data: User };
  ```

- **Pass data, not accessors.** `<Avatar user={user} />` over `<Avatar userId={id} />`
  when the parent already has the user — the second forces a second fetch or a global
  lookup and couples a leaf component to your data layer.
- **Name event props for what happened, not what to do.** `onSubmit`, `onRowSelect`,
  `onDismiss` — not `handleClick` or `doSave`. The child reports; the parent decides.
- **Default to the safe value.** A `dangerouslyAllowHtml`-style prop must default to off;
  a `confirmBeforeDelete` prop must default to on.

### 2.3 Composition over configuration

Prefer slots/children to a growing config object.

```jsx
// Configuration: every new need adds a prop, forever.
<Card title="X" subtitle="Y" footerButtonLabel="Z" onFooterClick={…} showBadge />

// Composition: the card owns layout, the caller owns content.
<Card>
  <Card.Header title="X" subtitle="Y"><Badge /></Card.Header>
  <Card.Footer><Button onClick={…}>Z</Button></Card.Footer>
</Card>
```

The test: if adding one more visual variant requires editing the shared component, the
API is configuration and it will keep growing.

---

## 3. State management

### 3.1 Classify state before choosing where to put it

There are five kinds. Most state bugs come from putting one kind in the container meant
for another.

| Kind | Example | Where it belongs |
|---|---|---|
| **Server state** | Fetched user, product list | A data-fetching cache (React Query, SWR, Apollo, RTK Query). Never hand-rolled in a global store. |
| **URL state** | Current page, filters, tab, search query, opened detail id | The URL. It is shareable, bookmarkable, and survives reload for free. |
| **Local UI state** | Dropdown open, input draft, hover | `useState` in the component that owns it. |
| **Shared UI state** | Theme, sidebar collapsed, toast queue | Context or a small global store. Small, serializable, rarely written. |
| **Form state** | Field values, dirty, errors | A form library or a single reducer — not N `useState` calls. |

- **Anything a user would expect to survive a refresh or be shareable via link belongs in
  the URL.** Filters, sort order, pagination, active tab, selected entity. This one rule
  eliminates a whole class of "why did my state reset" bugs and makes deep-linking free.
- **Server state is not application state.** It is a cache of something you do not own. It
  needs staleness, revalidation, deduplication, and invalidation — which is exactly what
  a data-fetching library gives you and what a global store does not. Putting fetched data
  into Redux/Pinia/Zustand by hand means reimplementing cache invalidation manually.

### 3.2 Placement and derivation

- **Lift state to the lowest common ancestor, and no higher.** State lifted too far causes
  re-renders across unrelated subtrees and makes components impossible to reuse.
- **Derive, don't sync.** If `fullName` can be computed from `firstName` and `lastName`,
  compute it during render. Every `useEffect` that writes state in response to other state
  is a bug in waiting — two sources of truth that will drift.

  ```js
  // Bad: an extra render, and a window where the two disagree.
  useEffect(() => { setTotal(items.reduce(sum, 0)); }, [items]);

  // Good.
  const total = items.reduce(sum, 0);
  ```

- **Reach for a reducer when transitions have rules.** Multiple fields that must change
  together, or actions only legal in certain states, belong in a reducer or state machine —
  not scattered `setX` calls whose ordering is load-bearing.

### 3.3 Effects

`useEffect` (and equivalents) is for **synchronizing with something outside the component
system** — the DOM, a subscription, a timer, an analytics SDK. It is not a lifecycle hook.

Do not use an effect to:
- transform data for rendering → compute during render
- reset state when a prop changes → change the component `key` instead
- handle a user event → put the logic in the event handler
- fetch data → use a data-fetching library, or the framework's loader/server component

**Every effect that subscribes must unsubscribe.** Timers, listeners, observers, sockets,
and in-flight requests all need teardown. A component that mounts and unmounts a thousand
times must leave nothing behind.

```js
useEffect(() => {
  const controller = new AbortController();
  fetchThing({ signal: controller.signal }).then(setThing).catch(ignoreAbort);
  return () => controller.abort();   // ← not optional
}, [id]);
```

**Guard against out-of-order responses.** If `id` changes fast, response 1 can land after
response 2. Abort the previous request, or check that the result still matches the current
input before committing it.

---

## 4. Data fetching and async UI

- **Handle all four states, always.** Idle, loading, error, empty-success. "Empty" is a
  distinct design problem: zero results needs different copy than zero-ever-created.
- **Show skeletons that match the final layout**, not a centered spinner that collapses to
  content. Matching skeletons eliminate layout shift and read as faster.
- **Never render a spinner for under ~200ms of work.** A flash of loading state is worse
  than a brief pause. Delay the indicator.
- **Make errors recoverable.** Every error state needs a retry affordance and text that
  says what the user can do. "Something went wrong" with no action is a dead end.
- **Distinguish error kinds.** Network failure (retry), 401 (re-authenticate), 403 (you
  cannot do this), 404 (gone), 422 (fix your input), 5xx (our fault, retry later). They
  need different UI.
- **Prevent double-submit at the source.** Disable the trigger while a mutation is in
  flight and make the handler idempotent. Users double-click; slow networks make it worse.
- **Optimistic updates require a rollback path.** Apply the change locally, and on failure
  restore the previous value *and* tell the user it failed. An optimistic update with no
  rollback silently lies about persisted data.
- **Cancel in-flight requests on unmount and on input change.** Especially search-as-you-
  type, which should also be debounced (~250–300ms) — with the trailing call guaranteed.
- **Paginate or virtualize anything unbounded.** Any list that can grow with usage —
  results, feeds, logs, notifications — needs a limit. Rendering 10,000 rows freezes the
  main thread regardless of framework.

---

## 5. Forms

Forms are where most real UI complexity lives. They deserve deliberate design.

- **Use a native `<form>` with a submit handler.** This gives you Enter-to-submit, implicit
  submission, autofill, and the browser's own validation semantics. A `<div>` with a
  clickable button gives you none of these.
- **Validate on the right event.** On blur for the first pass, on change *after* a field
  has already errored (so the error clears as they fix it), and always on submit. Validating
  on every keystroke before the user has finished typing is hostile.
- **Server validation is authoritative; client validation is a courtesy.** Mirror the rules
  for fast feedback, but always re-check server-side — the client can be bypassed entirely.
  See `security.md` §4.
- **Map server field errors back to their fields.** An API returning
  `{ errors: { email: "already taken" } }` should surface next to the email input, not in a
  generic banner. Design the error contract for this (see `backend-and-api.md` §4).
- **Never clear a user's input on failure.** Retaining what they typed is the difference
  between an annoyance and a lost form.
- **Disable submit while submitting, not while invalid.** A permanently disabled button
  with no explanation is a dead end — let them submit and show them what's wrong.
- **Associate every input with a `<label>`** via `htmlFor`/`id` or wrapping. Placeholders
  are not labels: they vanish on focus, fail contrast, and are skipped by some screen
  readers.
- **Wire up autocomplete and input types.** `type="email"`, `inputmode="numeric"`,
  `autocomplete="one-time-code"`, `autocomplete="new-password"`. These change the mobile
  keyboard and enable password-manager integration — cheap, high-impact.
- **Warn before discarding unsaved changes** on navigation away from a dirty form.

---

## 6. Accessibility

Not optional, not a phase-two item, and in many jurisdictions a legal requirement. The
majority of the value comes from a small number of rules.

### 6.1 Semantics

- **Use the correct element.** `<button>` for actions, `<a href>` for navigation,
  `<input>`/`<select>` for input, `<ul>/<li>` for lists, `<table>` for tabular data. Never
  `<div onClick>` — it is not focusable, not keyboard-activatable, and not announced.
- **One `<h1>` per page; don't skip heading levels.** Screen-reader users navigate by
  headings the way sighted users skim. Style with CSS, not by picking a different level.
- **Landmarks**: `<header>`, `<nav>`, `<main>`, `<footer>`. Exactly one `<main>`.
- **ARIA is a last resort.** The first rule of ARIA is not to use ARIA. Incorrect ARIA is
  worse than none — `role="button"` on a div still doesn't make it keyboard-operable.

### 6.2 Keyboard

- **Everything interactive must be reachable and operable by keyboard alone.** Test by
  unplugging the mouse and doing the primary flow with Tab / Shift-Tab / Enter / Space /
  Escape / arrows.
- **Never remove focus outlines without replacing them.** `outline: none` alone is a
  serious accessibility defect. Use `:focus-visible` for a clear, high-contrast indicator.
- **Manage focus on route change and on overlay open/close.** Opening a modal moves focus
  into it, traps it there, closes on Escape, and returns focus to the trigger on close.
  Route changes should move focus to the new page heading.
- **Never create positive `tabindex` values.** Use `0` or `-1`; DOM order should be the
  tab order. If they disagree, fix the DOM order.

### 6.3 Visual and content

- **Contrast**: at least 4.5:1 for body text, 3:1 for large text and for the boundaries of
  interactive controls. Verify with a tool; do not eyeball it.
- **Never convey information by color alone.** Add an icon, label, or pattern — for error
  states, chart series, status badges, and diffs.
- **Every meaningful image needs `alt`; every decorative image needs `alt=""`.** Alt text
  describes function in context, not appearance: an icon-only delete button is
  "Delete invoice", not "trash can icon".
- **Respect `prefers-reduced-motion`** — disable parallax, autoplay, large transforms.
- **Support 200% zoom and 400% at mobile widths** without horizontal scroll or clipping.
  Use relative units (`rem`) for typography and spacing.
- **Announce async changes** that aren't in the focus path via a polite live region —
  toasts, validation summaries, "3 results found".

---

## 7. Performance

Optimize what users perceive, in the order they perceive it.

### 7.1 Loading

- **Budget your JavaScript.** Every dependency is a permanent tax on every user. Before
  adding one, check the bundle cost and whether the platform already does it (`Intl` for
  dates and number formatting, `fetch`, `URLSearchParams`, CSS grid).
- **Code-split at route boundaries first**, then at heavy-component boundaries (editors,
  charts, maps, video players). Never ship an admin dashboard's code to logged-out users.
- **Never block first render on non-critical work.** Analytics, chat widgets, A/B tooling,
  and feature-flag SDKs load async, after interactive.
- **Serve modern image formats, sized correctly, with explicit `width`/`height`.**
  Dimensions prevent layout shift. Lazy-load below-the-fold images; eagerly load the
  largest above-the-fold one and preload it.
- **Self-host or preconnect fonts, subset them, and use `font-display: swap`.** Invisible
  text while a webfont loads is a common, avoidable failure.

### 7.2 Runtime

- **Measure before optimizing.** Use the profiler to find what actually re-renders. Adding
  memoization by intuition usually adds cost without benefit.
- **Fix re-render causes, not symptoms.** A new object/array/function literal in props on
  every render defeats memoization. Move state down, split components, or stabilize the
  reference — in that order of preference.
- **Keep list keys stable and unique.** Never use array index as key for a list that can
  reorder, insert, or delete — it corrupts component state and DOM identity.
- **Virtualize long lists** (roughly >100 rows, or any row with meaningful render cost).
- **Debounce/throttle high-frequency handlers** — scroll, resize, mousemove, input. Prefer
  `IntersectionObserver` and `ResizeObserver` over scroll/resize listeners entirely.
- **Never do heavy synchronous work on the main thread.** Parsing, crypto, image
  processing, large sorts → a Web Worker or the server.
- **Animate `transform` and `opacity` only.** Animating `width`, `top`, `margin`, or
  `box-shadow` forces layout/paint every frame.

### 7.3 Core Web Vitals

Track LCP (< 2.5s), INP (< 200ms), and CLS (< 0.1) from **field data**, not just lab runs.
Lab numbers on a fast laptop tell you almost nothing about your actual users.

---

## 8. Styling and design system

- **Use design tokens, never raw values.** Colors, spacing, radii, type scale, shadows,
  breakpoints, and z-index live in one place and are referenced everywhere else. A
  hard-coded `#3b7dd8` or `13px` is a future inconsistency.
- **Define z-index as a named scale** (`dropdown: 100, sticky: 200, modal: 400, toast: 600`).
  Arbitrary `z-index: 9999` values are how stacking wars start.
- **Scope styles to components.** CSS Modules, scoped styles, or utility classes. Global
  selectors on element names or generic classes (`.card`, `.active`) will collide.
- **Mobile-first, and design at the breakpoints where content breaks**, not at device
  widths. Test at 320px, 768px, 1280px, and one very wide viewport.
- **Support dark mode by defining semantic tokens** (`surface`, `text-primary`,
  `border-subtle`) rather than literal ones (`gray-100`). Then a theme is a token swap
  instead of a rewrite. Respect `prefers-color-scheme`, and persist an explicit override.
- **Never set a fixed height on anything containing text.** Translations, long names, and
  user-set font sizes will overflow it. Constrain with `min-height` and let content grow.
- **Design for the real content extremes**: the 60-character name, the zero-item list, the
  1,000-item list, the missing avatar, the RTL language, the German compound noun.

---

## 9. Routing and navigation

- **URLs are an API.** They are shared, bookmarked, and indexed. Design them
  deliberately, keep them stable, and redirect when they must change.
- **Back and forward must always work.** Every meaningful view change should produce a
  history entry; transient state (an open dropdown) should not.
- **Preserve scroll position on back navigation**, reset it on forward navigation.
- **Handle unknown routes with a real 404 page** that offers a way onward.
- **Guard protected routes on the server as well as the client.** A client-side redirect
  is UX, not security — the data must be protected at the API. See `security.md` §3.

---

## 10. Error handling and resilience

- **Wrap route subtrees in error boundaries.** One failing widget must not white-screen the
  application. Boundaries should render a useful fallback with a retry.
- **Never show a raw exception, stack trace, or backend error string to a user.** Log the
  detail; show a human sentence plus a correlation id they can quote to support.
- **Handle offline and flaky connections.** Detect offline state, queue or block mutations,
  and tell the user. Retry idempotent GETs with backoff; never blind-retry non-idempotent
  requests.
- **Report client errors to a monitoring service** with enough context (route, release,
  user id if permitted, breadcrumbs) to reproduce — and **scrub PII before sending**.

---

## 11. Testing

Test what the user does, not how the component is built.

- **Query by accessible role and name**, not by CSS class or test id, wherever possible.
  `getByRole('button', { name: 'Save' })` fails when the button stops being announced as a
  button — which is exactly when you want it to fail.
- **Never assert on internal state or private methods.** Assert on rendered output and
  emitted events. Tests coupled to implementation break on every refactor and catch nothing.
- **Mock at the network boundary** (MSW or equivalent), not by stubbing your own modules.
  This exercises your real data layer, including error and loading paths.
- **Test the error and empty paths.** They are the least-tested and most-hit code in most
  applications.
- **Add an automated accessibility check** (axe) to component tests. It catches contrast,
  labeling, and role mistakes cheaply — it will not catch keyboard flow, so still test that
  by hand for critical paths.
- **Reserve end-to-end tests for critical user journeys** — signup, checkout, the primary
  workflow. They are slow and flaky at scale; a small, reliable suite beats a large,
  ignored one.
- **Snapshot tests are for stable, small output only.** Large auto-updated snapshots are
  reviewed by nobody and assert nothing.

---

## 12. Anti-patterns

Recognize these on sight:

- `useEffect` that only calls `setState` from other state → derive it during render.
- A global store containing fetched server data → use a fetching/cache library.
- `<div onClick>` → `<button>`.
- `outline: none` with no `:focus-visible` replacement.
- Array index as a `key` in a reorderable list.
- `dangerouslySetInnerHTML` / `v-html` with anything but sanitized, trusted content.
- `z-index: 9999`.
- A component with more than ~3 boolean layout props.
- `any` / untyped props on a shared component.
- Business logic (pricing, permissions, tax) computed only on the client.
- Secrets, API keys, or tokens in client code or env vars shipped to the browser. Anything
  in the bundle is public.
- `localStorage` used for auth tokens (readable by any XSS) — see `security.md` §2.3.
- Fixed pixel heights around text.
- Infinite lists with no virtualization or pagination.

---

## Review checklist

**Component & state**
- [ ] Presentation separated from data fetching
- [ ] No illegal states representable in props
- [ ] State lives at the lowest common ancestor
- [ ] Derived values computed in render, not synced via effects
- [ ] Shareable/refresh-surviving state (filters, tabs, pagination) is in the URL
- [ ] Server data is in a fetch cache, not a hand-rolled global store

**Effects & async**
- [ ] Every subscription/timer/listener/request is cleaned up
- [ ] Out-of-order responses are guarded against
- [ ] Loading, error, empty, and success states all handled
- [ ] Errors are recoverable and distinguish network / auth / validation / server
- [ ] Double-submit prevented; optimistic updates roll back on failure

**Forms**
- [ ] Native `<form>` + submit handler
- [ ] Every input has a real `<label>`, correct `type`, and `autocomplete`
- [ ] Server errors map to their fields; user input is never cleared on failure
- [ ] Client validation mirrored server-side

**Accessibility**
- [ ] Semantic elements; no `<div>` acting as a control
- [ ] Full keyboard operation; visible `:focus-visible` indicator
- [ ] Focus managed on modal open/close and route change
- [ ] Contrast ≥ 4.5:1; information never conveyed by color alone
- [ ] Meaningful `alt` text; `prefers-reduced-motion` respected
- [ ] Automated axe check passes

**Performance**
- [ ] Routes and heavy components code-split
- [ ] Images sized, modern format, dimensions set
- [ ] Long lists virtualized or paginated; stable keys
- [ ] Animations limited to `transform`/`opacity`
- [ ] No new heavy dependency without a bundle-cost justification

**Styling**
- [ ] Design tokens used; no hard-coded colors, spacing, or z-index
- [ ] Styles scoped, not global
- [ ] Responsive down to 320px and at 200% zoom
- [ ] No fixed heights around text; long/empty content tested

**Testing & errors**
- [ ] Queries by role/name, not implementation details
- [ ] Network mocked at the boundary; error paths covered
- [ ] Error boundaries at route level
- [ ] No raw exception text shown to users; client errors reported with PII scrubbed
