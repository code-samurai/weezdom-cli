# Idea to production: the path every change follows (v4, 3 Nov 2026)

History: v4.2 (3 Nov 12:24am): house block line 7 (only tier 3 has a frozen click-through file), line 16 (replay recordings, not fakes) and line 17 (changed approved screenshot needs UX Expert approval), from UX Expert. v1 (2 Nov 2026) set gates S1–S5, C1–C4 and R1 after #518 (approval note below, kept as written). v4 (3 Nov 2026) adds Core contracts K1–K6 below; S5 and C1 now point to K2. Numbered v4 to match house rules block v4. Approved by Nik in All-Team, 3 Nov 2026 12:16am AEDT: "Then please fix it up so that going forward we don't run into this issue ever again. Add it to our core contracts requirements and underlying infrastructure and substrate where you're using across all of our app building and codebase going forward." Source: #518 took many rounds because tests used hand-written fakes of the Dream Insights findings store, real behaviour (one POST per source per run with up to 200 rows, a source stops at its first refused reply, 207 partial saves, 422s) only turned up mid-build, and wording was checked by reading sentences off screens. Separately, at 12:04am a production "read-only" check called GET /api/studio/search-plan, which started a paid Apify run.

#518 finishes on the current process (v1 gates). The next Studio piece is the first to run on v4.

Approved by Nik in All-Team, 2 Nov 2026 11:29pm AEDT: "Collate all updates and ensure every agent has fixed it in their substrate, process, pattern, capability and our entire design of how we are going from idea to production."
Source: #518 lessons (two check bugs, partial batches, internal names on screen, production range). Proposals from UX Expert, Hermes, CloudFlare-Pages and BossMan, merged here.

## Stages and their gates (a stage can't start until the gate before it passes)

1. **Idea → plan.** Code map and delete list (rg over html/js/css/tests). Plan-vs-spec conflicts settled with Nik in a decision box.
2. **Plan → data sheet.** For every element on screen:
   - S1 **Every answer listed.** Each backend or outside call lists every answer it can give (e.g. 200 / 207 / 422, empty, timeout). Each answer gets a row on the state sheet, a screen, and a check.
   - S2 **Count rule.** Every number on screen says how many calls make it up (e.g. one POST per source per run, up to 200 rows each; several sources can land on the same feed) and what is added up.
   - S3 **Display rule.** Text from another bot's service is never shown as-is. It's mapped to our plain words, with a fallback line.
   - S4 **Storage and key rows.** Any storage or key the change needs is listed for staging and production: a real sample, the path layout matches what the code writes, access confirmed by the owning bot.
   - S5 **Real sample.** Replaced by K2 (record before build) and K1 (contract per route). See Core contracts.
3. **Data sheet → frozen checks.**
   - C1 **Fakes copy reality.** Replaced by K2 (recorded real staging runs as fixtures) and K1 (no hand-written fakes of another service). See Core contracts.
   - C2 **Proven both ways.** Every new check fails on a deliberately wrong build (e.g. last-batch-only count, old build) and passes on the reference build, for the right reason, before it is frozen. A check that can't tell them apart doesn't ship.
   - C3 **Labelled reads.** Checks read counts and states from labelled elements (data-testid), never a card's loose text. The brief tells the builder to add those labels.
   - C4 Staging checks read the current state first; background hand-offs get one check that the job really starts.
4. **Checks → brief.** House rules block included, stop after two failures, size cap, scope lines matched to test IDs.
   - R1 **Path to production section.** Before work starts: the commits between production and the target, what each needs on production (volumes, keys, settings), whether the production check is read-only or costs money, and that the first paid production action needs Nik's separate yes.
5. **Build → staging.** Builder's own real-browser walk, then the reviewer's confirm walk. One change on staging at a time.
6. **Staging → production.** Nik's yes, MR by MR (or batch per the promote rule), production check as declared in R1. Delete branch, close milestone.

## Core contracts (K1–K6, from v4)

These apply to every app and repo: Hermes, Dream Insights (DI), Weezdom.ai, weezdom-cli, scrape-gateway, CloudFlare-Pages repos, Backoffice and Partners.

- **K1 Contract per cross-service route.** The service that owns a route publishes every reply it can give: success, partial (such as 207), validation (such as 422), auth errors and empty. Each reply has a real staging recording in the owner's repo, and the owner's own CI fails if the route stops matching them. Consumers replay those recordings in their tests. Hand-written fakes of another service's replies are not allowed. Until a contract exists, the consumer's brief uses a recorded real staging run and marks the route "no contract yet". Storage buckets (R2 and similar) count as services: their contract is the per-bucket key layout, a real staging sample, writer and reader checks, and a live key check before production (skill `storage-and-key-setup-rows`).
  - How it's checked: the brief lists each cross-service route with its contract file path (or "no contract yet" plus the recording path). The reviewer rejects any test that builds another service's reply by hand. The owner's pipeline has a job that runs the route against its recordings.
- **K2 Record before build.** Before the brief goes out, one real staging run of every outside call the change touches is captured (record/replay cassettes) and committed as test fixtures. This replaces S5 and C1.
  - How it's checked: the brief lists each outside call with its cassette path and the commit that added it. No cassette, no brief.
- **K3 Logic below the screen.** Counting, choosing a state and choosing the wording live in plain functions, with table-driven unit tests that cover every reply for every source. Browser walks cover only the main flows (about five), plus one approved screenshot per state.
  - How it's checked: the brief names the functions and their test tables. The reviewer checks that the table has a row for every reply in the K1/K2 recordings, for every source, and that the walk list stays at about five main flows.
- **K4 One message catalogue per app.** All user-facing text lives in one reviewed file, with ICU-style plural and list rules. Screens never build sentences inline. Where practical, CI fails on inline user-facing strings in new code.
  - How it's checked: wording changes are reviewed as diffs of the catalogue file. Tests check message keys and catalogue output, not sentences read off a screen. The CI lint (where present) blocks new inline strings.
- **K5 Risk tiers.** Tier 1: copy or a small fix with no logic change (green pipeline, the builder's walk, one confirm walk). Tier 2: a logic change (adds K3 table tests and the K1 contract replay). Tier 3: a new screen, a new integration, or a data or storage change (the full data sheet, state sheet, frozen checks and joint walk). The brief states its tier. The reviewer can raise the tier but never lower it.
  - How it's checked: a brief without a tier doesn't go out. The reviewer records the tier they accepted, and any raise, in the review.
- **K6 Safe reads.** A GET or a page load never starts outside, paid or writing work (scrape-gateway, LLMs, Dream Insights writes, Apify). Every app has a guard test that calls every GET on an empty data dir with recording fakes and fails on any outside call. Production checks use only endpoints proven safe at that commit (R1).
  - How it's checked: the guard test runs in CI on every pipeline. The R1 section of the brief lists each endpoint the production check calls, with the commit at which the guard test passed.

- **K2 add-ons (v4.1, 3 Nov, from Hermes's review).** Recordings are scrubbed of keys, tokens, auth headers and personal data before commit, and a CI check fails on anything secret-shaped in the fixtures folder. Recordings come from staging only, with a spend cap, and any paid staging recording is named in the brief. Recording on production needs Nik's yes.
- **K1 add-on (v4.1).** When an owner changes a reply, it re-records in the same MR, bumps the contract version and posts the change in All-Team. Every consumer that replays that route updates before the owner promotes to production.
- **K5 add-on (v4.1).** A Tier 1 diff touches only the message catalogue (K4). Anything else makes it Tier 2 or above.
- **K1/K6 add-ons (v4.1).** Replay fails on any outside call that isn't in the recording. The K6 guard test finds GET routes from the router itself and also fails on queued jobs or writes. Until each known bad GET is fixed, it sits on a "never call in a production check" list kept in that repo.
- **Tier 1 proof (v4.1).** A Tier 1 brief includes the catalogue diff (its proof that it's copy only). The side-effect proof is the K6 guard test passing in CI, so it needs no extra step.

## Where each fix lives (owner makes it, BossMan verifies)

| Fix | Owner | Where it goes | Status |
|---|---|---|---|
| S1, S2, S5, C1–C4 (S3 pointer only) | UX Expert | ui-change-acceptance (data sheet, state sheet, check rules); product-qa | done, verified by BossMan 2 Nov 11:34pm (sha d36b82fc) |
| S1, S3, R1, C1 test helper | Hermes | hermes-brief-template.md, hermes repo AGENTS.md / .cursor/rules, test helper fakes | template v2 verified 2 Nov 11:33pm; repo rules !420 (5a34b725) checked by BossMan: block word for word, pipeline green; merges between #518 steps; fakes sample to UX Expert |
| S4 | CloudFlare-Pages | skill `storage-and-key-setup-rows` (/home/box/agent-data/workflows/storage-and-key-setup-rows/SKILL.md: rows template + checks); R2 sample doc /workspace/litmus/brief-518/r2-staging-signoff.md | done, verified by BossMan 2 Nov 11:32pm (checksum 5118dab3b6b0, 2 lessons logged) |
| S1/S5 publish side: list every answer its endpoints give, keep a real staging sample | Dream-Insights | DI repo AGENTS.md, DI contract docs, dream-insights-github-gitlab-land skill | pending |
| S1–S5, C2, R1 in briefs | Weezdom.ai | Weezdom repo AGENTS.md, weezdom-tip-ship skill | skill done 2 Nov 11:32pm; repo PRs building (bc-d68d4378 Weezdom.ai, bc-654fa437 weezdom-cli), unmerged until Nik names them |
| House rules block v3 (spec gates line) | BossMan | cursor-rules-house-block.md, then every repo via each owner | drafted |
| This file, failure lessons, code-changes routing, Backoffice and Partners notified | BossMan | /workspace/shared | done |
| v3 line in repo rules + brief steps | Backoffice | finance/backoffice !9 (e1b9031a), brief steps in its memory | merged b9964a10 on Nik's yes, branch deleted |
| v3 line in repo rules + brief steps | Partners@LH | marketing/partners !3, brief steps in its memory | merged aa3c1eed on Nik's yes, branch deleted |
| K1–K6 docs (this file, house rules block v4) and rollout to every repo's AGENTS.md / .cursor/rules (Hermes, DI, Weezdom.ai, weezdom-cli, scrape-gateway, CloudFlare-Pages repos, Backoffice, Partners) | BossMan | /workspace/shared, then every repo via each owner | pending |
| K1 publish side: contracts and per-run reply records for its cross-bot routes | Dream-Insights | DI issue https://gitlab.leadshook.com/leadshook-3.0/dream-insights/-/work_items/635: recordings of every answer, a CI check against them, a per-reply run record and a one-command replay export; dream-insights-github-gitlab-land skill makes recordings a standing step | pending |
| K1 for routes it owns, K2 recordings | Weezdom.ai | Weezdom issue https://github.com/code-samurai/Weezdom.ai/issues/1537: the match check, competitor writes, search and the opportunity finder, plus recorded replies for the AI and R2 services it calls | pending |
| K1 storage contract (owns no routes; buckets count as services) | CloudFlare-Pages | shared skill `storage-and-key-setup-rows` (sha256 10a0f679d890): per-bucket key layout, a real staging sample, writer and reader checks, a live key check before production | done |
| K1 for routes it owns, brief template onto v4, K6 GET guard test | Hermes | hermes-brief-template.md; Hermes repo guard test; issue https://gitlab.leadshook.com/marketing/hermes-marketing-agent/-/work_items/522 (recorded answers + CI check for its routes, Studio replays DI/Weezdom/scrape-gateway/storage recordings, table tests, one message list); product fix (GETs never start outside work) in progress via cloud agent bc-e5123a89 | pending (product fix in progress) |
| K5 tiers and shorter walks (about 5 main flows, one screenshot per state) | UX Expert | ui-change-acceptance rewrite | pending (in progress) |
| K6 guard test and K4 catalogue in each app (existing apps: new and changed screens first) | Each app owner (Hermes, DI, Weezdom.ai, weezdom-cli, scrape-gateway, CloudFlare-Pages, Backoffice, Partners) | each repo's tests and its message catalogue file | pending |

Verification: each owner posts the file path or MR link in All-Team. BossMan checks it and marks the row done. Friday's rules review re-reads this table.
