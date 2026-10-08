# Browser workspace

A local operator workspace for reviewing a proposal and deciding the next step.
The UI uses native HTML/JavaScript and official Primer CSS 22.3.2 components. It
adds no frontend runtime, remote fonts, analytics, or credential storage.

## Case review

![Case review with a synthetic access proposal](assets/case-review.jpg)

The screenshot shows the real application with disposable **synthetic** data.
The preview token is a public fixture, accepted only by the isolated preview server.

1. Enter a supervisor token and case ID on the existing lab at port 5681.
2. Read the tenant, action, resource, access level, policy, and verification state.
3. Approve the reviewed version. A separate worker executes; target read-back
   determines whether the case can close.

Closed cases remain readable. Started or uncertain actions cannot enable another
approval. Editing the token or case invalidates the loaded review, including late
responses. Technical evidence remains available in a disclosure below the proposal.

For a credential-free preview, run `python scripts/preview_workspace.py`. Open the
printed loopback URL on port 5683 and use `preview-only-` followed by 32 `x`
characters. It uses an in-memory case and target, with no worker, Jira, Docker,
model calls, or private config. Stopping the process discards its fixture state.

## AI practice

![Evidence and next-step guidance](assets/ai-practice.jpg)

Run `python scripts/business_pilot.py` and open `http://127.0.0.1:5682/practice`.
Four cached OpenAI examples support quote selection, field evidence, missing-field
questions, and an explicit recommendation with a reason. The operator still selects
the next step. Practice performs no model calls, business actions, or answer writes.
The completed human pilot and its original observations are unchanged.

## Design audit and implementation

The original approval page showed a raw JSON block beneath a single narrow form;
practice stacked all three tasks vertically. The revision makes the action readable
as labeled fields and places the source beside evidence and the next decision.

- Direction: calm, evidence-focused product workspace; variance 4, motion 2, density 5.
- Design system: official Primer buttons, forms, base styles and light palette,
  with green `#24584a` carried forward from the original approval page.
- Typography: system sans, 34/28px page title, 16px section titles, 15px body;
  12px supporting text. No font downloads or decorative imagery.
- Spacing: 20/24px panels, 24px desktop gutter, a 300px connection column;
  one column below 800px, compact field stacking below 480px.
- Accessibility: native controls, visible labels and focus, skip navigation,
  live feedback, semantic headings, no hover-only actions or motion.
- Preserved: token then case field order, IDs, backend authorization, case URL
  query, exact-quote behavior, cached examples, and independent execution.
- Marketing-page patterns, image generation, carousels and animation are not
  applicable to this operator workspace. No Lighthouse score is claimed.

Rebuild the vendored, MIT-licensed CSS with `npm ci --prefix frontend` then
`npm run build --prefix frontend`. `frontend/build.mjs` selects official component
styles and the official light palette; runtime serves only explicit asset paths.

## Validation, 2026-10-09

- 183 Python tests, 8 MCP tests, 14 quote/next-step assertions, and 7 approval UI
  behavioral tests passed after the revision.
- Browser: actual proposal load and synthetic approval passed; approval did not
  trigger execution. Cached clarification example returned the correct feedback.
- Desktop 1280px and mobile 390px checked. Both pages fit the mobile viewport
  without horizontal overflow. [Mobile capture](assets/ai-practice-mobile.jpg).
- Behavioral tests cover stale responses, changed identity/case, text-safe untrusted
  content, payload-bound approval, closed/uncertain cases, and token clearing.
- Runtime health was ready after reloading only this project's API and practice server.

Phase 5–8 reports remain evidence for their recorded revisions. This UI extension
has its own validation above; it does not retroactively change those snapshots.
