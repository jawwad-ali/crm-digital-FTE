# Tasks: Web Support Form

**Input**: Design documents from `/specs/005-web-support-form/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included — SC-008 requires "unit tests for components, integration tests for the polling flow, and accessibility audits."

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1–US5) this task belongs to

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create the Next.js 15 project with all tooling configured

- [x] T001 Initialize Next.js 15 project in `web/` — run `npx create-next-app@latest web` with TypeScript, Tailwind CSS, App Router, src/ directory. Verify `npm run dev` starts on port 3000.
- [x] T002 Configure Tailwind CSS v4 — ensure `web/src/app/globals.css` uses `@import "tailwindcss"`, `web/postcss.config.mjs` uses `@tailwindcss/postcss` plugin. Remove any v3-style `tailwind.config.ts` if generated.
- [x] T003 Configure Vitest + React Testing Library — create `web/vitest.config.ts` with jsdom environment and path aliases matching tsconfig. Install `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `jsdom`. Add `test` and `test:watch` scripts to `web/package.json`.
- [x] T004 [P] Create TypeScript interfaces in `web/src/lib/types.ts` — define `Message`, `Conversation`, `ChatRequest`, `JobAccepted`, `JobStatus`, `ChatResponse`, `HealthStatus`, `ValidationErrors` per data-model.md.
- [x] T005 [P] Create API client in `web/src/lib/api.ts` — implement `submitChat()`, `getJobStatus()`, `checkHealth()` functions using `fetch()` with `NEXT_PUBLIC_API_URL` base URL per contracts/api-integration.md.
- [x] T006 [P] Create `.env.example` in `web/` with `NEXT_PUBLIC_API_URL=http://localhost:8000` and copy to `.env.local`.

**Checkpoint**: `npm run dev` serves an empty page at localhost:3000, `npm test` runs (0 tests), API client and types are ready.

---

## Phase 2: Foundational (Shared Hooks)

**Purpose**: Custom hooks that all user stories depend on. MUST complete before any user story.

- [x] T007 [P] Implement `useConversation` hook in `web/src/hooks/useConversation.ts` — manages `Conversation` state with `addCustomerMessage()`, `updateMessageStatus()`, `setCustomerInfo()` per component-contracts.md.
- [x] T008 [P] Implement `useJobPolling` hook in `web/src/hooks/useJobPolling.ts` — accepts `jobId`, `onComplete`, `onError` callbacks. Uses `setTimeout` chain with `retry_after` interval. Stops on completed/failed. Timeout at 5 minutes. Network retry up to 3 failures per polling-flow in research.md.
- [x] T009 [P] Implement `useHealthCheck` hook in `web/src/hooks/useHealthCheck.ts` — calls `GET /health` once on mount, returns `{ isHealthy: boolean | null }`.
- [x] T010 [P] Implement `useCooldown` hook in `web/src/hooks/useCooldown.ts` — `startCooldown()` sets `isCoolingDown` to true for configurable duration (default 10000ms).
- [x] T011 Write hook tests in `web/src/__tests__/hooks/` — test `useConversation` (add message, update status, set customer info), `useJobPolling` (polling lifecycle, timeout, network retry), `useHealthCheck` (healthy/unhealthy), `useCooldown` (timer behavior). Use `renderHook` from RTL, mock `fetch` with `vi.fn()`.

**Checkpoint**: All 4 hooks implemented and tested. `npm test` passes hook tests.

---

## Phase 3: User Story 1 — Submit a Support Request (Priority: P1) MVP

**Goal**: Customer fills form (name, email, message), submits, sees processing indicator, receives AI agent response displayed in a chat area.

**Independent Test**: Open form → fill fields → submit → processing spinner appears → agent response appears.

### Implementation

- [x] T012 [P] [US1] Create `MarkdownRenderer` component in `web/src/components/MarkdownRenderer.tsx` — renders markdown string via `react-markdown` with `remark-gfm`. Install `react-markdown` and `remark-gfm`. Links open in new tab (`target="_blank"`). XSS-safe by default (FR-018).
- [x] T013 [P] [US1] Create `StatusIndicator` component in `web/src/components/StatusIndicator.tsx` — shows health check status (green/red dot), processing spinner animation (pulsing dots), and error banner with optional retry callback.
- [x] T014 [P] [US1] Create `MessageInput` component in `web/src/components/MessageInput.tsx` — textarea with character counter (`{count} / 2000`), submit button, Enter to submit (Shift+Enter for newline), `disabled` prop, ARIA label (FR-011).
- [x] T015 [P] [US1] Create `ChatMessage` component in `web/src/components/ChatMessage.tsx` — customer messages right-aligned (plain text), agent messages left-aligned (rendered via MarkdownRenderer), processing state shows pulsing dots, failed state shows error text. Timestamp display.
- [x] T016 [US1] Create `ChatThread` component in `web/src/components/ChatThread.tsx` — renders array of `ChatMessage` components. Auto-scrolls to bottom on new messages via `useEffect` + `scrollIntoView`. ARIA `role="log"` and `aria-live="polite"` (FR-014).
- [x] T017 [US1] Create `InitialForm` component in `web/src/components/InitialForm.tsx` — renders name, email, message fields. Basic required-field validation (all three must be non-empty). `onSubmit` callback receives (name, email, message). Disables submit while `isSubmitting` is true (FR-010).
- [x] T018 [US1] Create `SupportForm` orchestrator in `web/src/components/SupportForm.tsx` — `'use client'` directive. Uses `useConversation`, `useHealthCheck`, `useJobPolling`, `useCooldown` hooks. Handles submit flow: add customer message → call `submitChat()` → start polling → on complete, add agent message to conversation. Shows `InitialForm`, `ChatThread`, `StatusIndicator`.
- [x] T019 [US1] Create root layout in `web/src/app/layout.tsx` — HTML shell with metadata (title: "Customer Support"), Tailwind globals import. Create main page in `web/src/app/page.tsx` — server component shell that renders `<SupportForm />` centered on page with max-width container.

### Tests

- [x] T020 [US1] Write component tests in `web/src/__tests__/components/` — test `InitialForm` (renders fields, submit callback), `ChatMessage` (customer vs agent display, markdown rendering), `ChatThread` (renders messages), `MessageInput` (char counter, submit on Enter), `StatusIndicator` (health states), `MarkdownRenderer` (renders bold, lists, links).
- [x] T021 [US1] Write integration test in `web/src/__tests__/integration/test-submit-flow.test.tsx` — render `SupportForm`, fill form, submit, mock `fetch` for POST /api/chat (202) then GET /api/jobs (processing → completed). Verify: processing indicator appears, agent response displays in chat thread.

**Checkpoint**: Form loads at localhost:3000, customer can submit message and see agent response. `npm test` passes US1 tests. This is the MVP.

---

## Phase 4: User Story 2 — Conversation Thread with Follow-ups (Priority: P2)

**Goal**: After first response, name/email collapse into header bar, message-only input shown, customer sends follow-ups, full conversation visible as chat thread.

**Independent Test**: Submit first message → receive response → name/email collapse → send follow-up → both exchanges visible in thread.

### Implementation

- [x] T022 [P] [US2] Create `CustomerHeader` component in `web/src/components/CustomerHeader.tsx` — compact bar showing customer name and email (e.g., "Ali (ali@test.com)"). Visible only in follow-up mode (FR-017).
- [x] T023 [US2] Add follow-up mode to `SupportForm` in `web/src/components/SupportForm.tsx` — after first response received, set `isFollowUpMode = true`. Conditionally render `CustomerHeader` + `MessageInput` instead of `InitialForm`. Follow-up submits reuse stored name/email from conversation state.

### Tests

- [x] T024 [US2] Write tests for follow-up mode in `web/src/__tests__/integration/test-followup-flow.test.tsx` — verify: after first response, InitialForm hidden, CustomerHeader visible, message-only input shown. Submit follow-up, verify both exchanges in thread. Multiple follow-ups maintain full history.

**Checkpoint**: Multi-turn conversation works. Name/email collapse after first response. `npm test` passes US2 tests.

---

## Phase 5: User Story 3 — Input Validation and Error Recovery (Priority: P2)

**Goal**: Comprehensive client-side validation with inline errors. Graceful error handling for network failures, timeouts, and expired jobs. Retry without data loss.

**Independent Test**: Submit empty form → inline errors. Simulate network error → error banner with retry. Wait 5+ minutes → timeout message.

### Implementation

- [x] T025 [US3] Enhance `InitialForm` validation in `web/src/components/InitialForm.tsx` — add email format validation (regex), 2000 character limit on message, inline error messages below each field, character counter turns red when approaching/exceeding limit (FR-002).
- [x] T026 [US3] Add error recovery to `SupportForm` in `web/src/components/SupportForm.tsx` — handle network errors (fetch throws), server errors (non-2xx status), timeout (polling > 5 min), expired jobs (404 from polling). Display error via `StatusIndicator` with "Try Again" button. Retry preserves entered data (FR-012, FR-013).
- [x] T027 [US3] Add 10-second cooldown throttle in `web/src/components/SupportForm.tsx` — after each successful submission, call `startCooldown()`. Submit button disabled during cooldown with visual countdown or "Please wait" label (FR-016).

### Tests

- [x] T028 [US3] Write validation tests in `web/src/__tests__/components/test-validation.test.tsx` — empty fields show errors, invalid email format shows error, 2001-char message shows error, valid data passes. Write error recovery tests in `web/src/__tests__/integration/test-error-recovery.test.tsx` — network error shows banner with retry, timeout after 5 min shows message, retry preserves data, cooldown disables button for 10 seconds.

**Checkpoint**: All validation and error paths covered. `npm test` passes US3 tests.

---

## Phase 6: User Story 4 — Responsive and Accessible Experience (Priority: P2)

**Goal**: Form works on all viewports (320px–1920px). Full keyboard navigation. Screen reader compatibility with ARIA live regions.

**Independent Test**: Resize to 320px → single-column layout. Tab through all fields → visible focus. Screen reader announces status changes.

### Implementation

- [x] T029 [US4] Add responsive Tailwind classes to all components — mobile-first single-column layout (< 640px) with touch-friendly sizing (`min-h-[44px]` for inputs), tablet/desktop breakpoints (`sm:`, `md:`, `lg:`). Ensure no horizontal scroll at 320px. Update: `InitialForm`, `ChatThread`, `ChatMessage`, `MessageInput`, `CustomerHeader`, `SupportForm`, `StatusIndicator`.
- [x] T030 [US4] Add WCAG 2.1 AA accessibility to all components — proper `<label>` elements linked to inputs via `htmlFor`, `aria-describedby` for error messages, `aria-live="polite"` on ChatThread and StatusIndicator for screen readers, `aria-busy` during processing, visible focus rings (`focus-visible:ring-2`), sufficient color contrast (4.5:1 for text), keyboard navigation (Tab order, Enter to submit) (FR-008).

### Tests

- [x] T031 [US4] Write accessibility tests in `web/src/__tests__/accessibility/test-a11y.test.tsx` — run axe-core audit on rendered `SupportForm` (initial state, follow-up mode, error state). Verify zero WCAG 2.1 AA violations. Test keyboard navigation: Tab through fields, Enter to submit, focus moves to response after completion.

**Checkpoint**: Responsive on all viewports. Keyboard navigable. Screen reader friendly. Axe audit passes. `npm test` passes US4 tests.

---

## Phase 7: User Story 5 — Embeddable Widget (Priority: P3)

**Goal**: Dedicated `/embed` route renders form without page chrome. Can be loaded in an iframe from any external website.

**Independent Test**: Open localhost:3000/embed → form renders without header/footer. Create test HTML with iframe → form loads and works.

### Implementation

- [x] T032 [US5] Create embed page in `web/src/app/embed/page.tsx` — server component that renders `<SupportForm />` without the main page layout (no header, title, or surrounding chrome). Minimal padding for iframe context.
- [x] T033 [US5] Create embed example in `web/public/embed-example.html` — standalone HTML page with `<iframe src="http://localhost:3000/embed" width="400" height="600" style="border:none" />` demonstrating the embed integration.

### Tests

- [x] T034 [US5] Write embed test in `web/src/__tests__/integration/test-embed.test.tsx` — render the embed page component, verify `SupportForm` is present, verify no page header/footer/nav elements rendered.

**Checkpoint**: Embed page works at localhost:3000/embed. Example HTML loads form in iframe. `npm test` passes US5 tests.

---

## Phase 8: Polish and Cross-Cutting Concerns

**Purpose**: Final validation, cleanup, and documentation

- [x] T035 Run full test suite (`npm test`) — all component, hook, integration, and accessibility tests pass
- [x] T036 Run quickstart.md validation — execute all 7 manual testing scenarios from quickstart.md against running backend + frontend
- [x] T037 Final code review and cleanup — remove any unused imports, ensure consistent code style, verify all components have proper TypeScript types, no `any` types

---

## Dependencies and Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on T001–T005 (project + types + API client)
- **Phase 3 (US1)**: Depends on Phase 2 (hooks) — this is the MVP
- **Phase 4 (US2)**: Depends on Phase 3 (US1 must work first)
- **Phase 5 (US3)**: Depends on Phase 3 (US1 components exist to enhance)
- **Phase 6 (US4)**: Depends on Phase 3 (US1 components exist to style)
- **Phase 7 (US5)**: Depends on Phase 3 (SupportForm exists to embed)
- **Phase 8 (Polish)**: Depends on all desired phases complete

### User Story Dependencies

```
Phase 1 (Setup) → Phase 2 (Hooks)
                        ↓
                  Phase 3 (US1 - MVP)
                  ↙    ↓     ↘
          Phase 4   Phase 5   Phase 7
          (US2)     (US3)     (US5)
                  ↘    ↓     ↙
                  Phase 6 (US4)
                        ↓
                  Phase 8 (Polish)
```

- US2, US3, US5 can run in parallel after US1 is complete
- US4 (responsive/accessibility) should run after US2+US3 so it applies to the final component set

### Parallel Opportunities Per Phase

```bash
# Phase 1: T004, T005, T006 in parallel
# Phase 2: T007, T008, T009, T010 in parallel
# Phase 3: T012, T013, T014, T015 in parallel (leaf components)
# After US1: US2, US3, US5 in parallel
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1: Setup (T001–T006)
2. Phase 2: Foundational hooks (T007–T011)
3. Phase 3: US1 — form + submit + poll + display (T012–T021)
4. **STOP and VALIDATE**: Form works end-to-end with backend
5. Demo-ready after Phase 3

### Incremental Delivery

1. Setup + Foundational → tooling ready
2. US1 → core form works (MVP, worth majority of 10 hackathon points)
3. US2 → multi-turn conversation
4. US3 → validation + error recovery (production quality)
5. US4 → responsive + accessible (WCAG compliance)
6. US5 → embeddable widget
7. Polish → final validation

---

## Notes

- All frontend code lives in `web/` directory at repo root
- `'use client'` directive on all interactive components
- `NEXT_PUBLIC_API_URL` env var for backend URL — no hardcoded URLs
- No backend changes required — CORS already configured
- Tests mock `fetch` with `vi.fn()` — no real backend calls in tests
- Commit after each phase checkpoint
