# Review checklist: Frontend and UI Practices

The condensed form of the `frontend-practices` skill. Use it as a review pass over a diff, or as a
pull-request template. Each item maps to a numbered section of that skill's SKILL.md,
so read the section when an item needs its reasoning.

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
- [ ] All errors for a field shown, not only the first
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
- [ ] Layout shift addressed: media dimensions, scrollbar gutter, font metrics
- [ ] Theme applied before first paint, with no flash of the wrong theme

**Styling**
- [ ] Design tokens used; no hard-coded colors, spacing, or z-index
- [ ] Styles scoped, not global
- [ ] Responsive down to 320px and at 200% zoom
- [ ] Components sized by container query, not viewport, where reusable
- [ ] No fixed heights around text; long/empty content tested

**Testing & errors**
- [ ] Queries by role/name, not implementation details
- [ ] Network mocked at the boundary; error paths covered
- [ ] Error boundaries at route level
- [ ] No raw exception text shown to users; client errors reported with PII scrubbed
