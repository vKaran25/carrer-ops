# Interview Research `[P2]`

Not needed for P1. (Previously called "Prep Agent" — scope is research only, not full interview coaching. No DSA-practice tie-in.)

## Requirements
- FR-IR-1: Tool contract: `research_interview_structure(company: str) -> InterviewStructure` where `InterviewStructure = {rounds: [{name, type, focus_areas}], difficulty_note, prep_tips}`
- FR-IR-2: Output includes round structure **and** example question types/difficulty per round (e.g. "medium-to-hard array/DP questions typical in round 1") — not just bare structure
- FR-IR-3: Fixed query templates only (general + community-source-targeted, e.g. `site:reddit.com`, `site:leetcode.com/discuss`) — no LLM-generated queries. Single synthesis call. Shared cache across all users, keyed by company, valid ~60 days. Triggered on-demand only, never automatically per scouted job.
- FR-IR-4: When public data is insufficient, return "not enough public information found" — never fabricate a structure.

## Acceptance
A well-documented company returns a plausible structure. An obscure company returns the explicit "insufficient information" response, not an invented one.
