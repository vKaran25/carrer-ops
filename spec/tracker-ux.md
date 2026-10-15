# Search chat and tracker `[P1–P3 foundations / P4 target]`

## Core UI

Light blue workspace with Search chat, Job tracker and Settings. One continuous saved chat with inline DOCX controls, optional query and collapsible JD/fit cards. Show effective context/preferences with reset/edit controls. Only Interested creates a tracker application; search never adds tracker counts automatically.

The P4 target removes preparation, research, curation, learning, MCP and unfinished-feature controls. Ordinary users see account/privacy/preferences and understandable source status, not operator credentials/global configuration. Retain the confirmed Kanban/list toggle and responsive layout. Discuss further structural UI decisions before implementation.

## Tracker

- FR-TRACK-1: Interested → Applied → Interviewing → Resolved. Statuses/outcomes are explicit user actions; Applied uses its dedicated audited gate and never submits externally.
- FR-TRACK-2: Clear stages, source-backed JD details, empty/error/loading states, accessible mobile/desktop behavior.
- Interested has a small × with Cancel/Remove confirmation. Preserve chat/audit history and allow re-selection; duplicate selection never resets later progress.
- Migrate legacy Tailored entries to Interested with an audit entry; retain preparation artifacts, and preserve Applied/later progress. Earlier Found → Interested migration remains historical evidence.
- A failed/dormant draft is not a prerequisite or blocker for the core Applied action. Preparation may return as an independently accepted P6 upgrade.
- Current filename/remove × then Add resume (.docx); accept DOCX only and preserve the prior resume on failed replacement.

## Current prototype versus target

The existing runtime still exposes preparation and manual LinkedIn controls. These documentation changes do not remove them. In the target core, hide manual LinkedIn search/import initially; if live Tavily/employer coverage proves inadequate, discuss a refined LinkedIn feature or source remedy before choosing one. Preserve existing imported snapshots and their explicitly unverified availability; do not delete history or add scraping.

## Acceptance

Verify zero tracker intake from search, audited/idempotent Interested, status/history persistence, confirmation cancel/remove/restore, legacy migration without progress/artifact loss, Applied bypass rejection and four-stage views. Verify effective context/reset/preferences, stale-score clearing and absence of deferred UI/API actions. Test real account isolation and desktop/mobile behavior; prototype fixtures alone do not certify deployment.

## Introduction/demo `[P4 / P5A]`

Show the released pipeline search → Interested → Applied → Interviewing → Resolved, with sign-in/invitation/privacy states. P5A includes the demo video and write-up; bots/monetization/P6 tools must not appear as released core capabilities.
