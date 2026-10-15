# Phase 5 — Deploy First, Then Clients and Commercial Features

P5A/B/C are milestones in one phase. P5B and P5C do not block P5A or require one another. These are planned tasks; production account/service configuration and publishing require their corresponding implementation/release authorization.

## P5A — Core beta deployment and original P5 deliverables

Prerequisite: P4 acceptance and user-reviewed hosting/session/execution/backup decisions in `phase-4-tasks.md`.

- [ ] Complete final release hardening and reproducible frontend/backend build/runtime configuration; separate operator secrets from application output.
- [ ] Provision the agreed services with versioned PostgreSQL migrations, configured Google/email authentication and actual invite enforcement. Start clean beta workspaces.
- [ ] Deploy staging and verify the complete upload/search/follow-up/Interested/manual-tracker journey, source evidence and privacy/deletion behavior.
- [ ] Validate actual cold/warm behavior and agreed 15-account workload on the selected host, including provider budgets, limits, interrupted work and failure reporting.
- [ ] Verify monitoring/alerts, PostgreSQL/artifact backup restore as applicable, rollback and incident/recovery instructions. Free-tier pauses and email/provider limits must be documented.
- [ ] Present the deployment configuration, acceptance evidence and known limitations for release approval, then publish the invited beta.
- [ ] Finish setup/user/operator documentation, demo video and write-up showing only released features.
- [ ] Before public registration, review capacity, budget, abuse controls and admission configuration using the same account model. Do not silently open signups.

## P5B — Telegram and Discord

- [ ] Discuss account linking, supported commands, bot credentials and interaction/privacy design with the user.
- [ ] Implement thin clients through the same authenticated orchestrator, search/ranking and audited tracker actions.
- [ ] Test equal scores/results for equal context, ownership/admission, source/operational limits and explicit Applied actions across surfaces.
- [ ] Validate each client live and document its supported actions before release. Do not promise paid access conditions before P5C decides them.

## P5C — Pricing, commercial usage and feature gates

- [ ] Present cost/usage evidence and recommend plans; decide pricing, free/paid boundaries, product allowances and payment approach with the user.
- [ ] Design and implement the agreed entitlements/payment flows after review; enforce them server-side, independent of hidden UI.
- [ ] Test allowance reset/idempotency, entitlement changes and payment-related state transitions as applicable, while preserving P4 operational caps and manual action gates.
- [ ] Publish accurate pricing and limits only after acceptance. Paid user plans do not permit paid LLM models without a separate change to the confirmed model policy.

Owning requirements: `../spec/core-release.md` and `../spec/later-phases.md`.
