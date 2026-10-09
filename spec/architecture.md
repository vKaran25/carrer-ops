# Architecture Overview

```mermaid
flowchart TD
    O[Orchestrator agent<br/>LangGraph supervisor]
    QP[Query Parser<br/>NL to query spec]
    S[Scout agent<br/>ATS API + BS4 + Playwright fallback]
    RANK[Ranking & Confidence<br/>Scoring engine]
    T[Tailor agent]
    RC[Resume Curator<br/>LaTeX splice engine]
    C[Critic agent]
    IR[Interview Research agent]
    TR[Tracker agent]
    M[(Memory layer +<br/>personalized scoring weights)]
    E[(Eval harness)]
    MCP[(Custom MCP server)]
    H{Human approval gate}
    D[Deployed public app]
    BOT[Telegram / Discord clients]

    O --> QP --> S --> RANK
    O --> T --> RC
    O --> C
    O --> IR
    O --> TR
    RANK -.-> M
    T -.-> M
    RC -.-> M
    C -.-> E
    S -.-> MCP
    IR -.-> MCP
    T --> H
    H --> D
    BOT --> O
```

Solid arrows: orchestration/data flow. Dashed arrows: shared services each module draws on.
`BOT` clients (`[P4]`) call the *same* orchestrator as the web app — never a separately reimplemented scoring or agent path (see `/docs/competitive-analysis.md` — this is directly why Jobright's extension and web app showed different scores for the same job).

## Phase tags used throughout /spec
`[P1]` foundation/core loop · `[P2]` query engine + ATS scraping + interview research + resume curator · `[P3]` memory + eval harness + self-improving scoring · `[P4]` MCP server, multi-platform, monetization, public-readiness · `[P5]` harden/deploy/document.

## Module → spec file map
- Orchestrator + human approval gate + getting-started → `orchestrator-and-gate.md`
- Scout agent (job discovery) → `scout-agent.md`
- Query parsing + confidence scoring + self-improving personalization → `query-and-scoring.md`
- Tailor + Critic agents → `tailor-and-critic.md`
- Resume curator (LaTeX) → `resume-curator.md`
- Interview research → `interview-research.md`
- Tracker/dashboard UX → `tracker-ux.md`
- Data models (all entities) → `data-models.md`
- Everything P3/P4 (memory, eval, MCP, multi-platform, monetization, auth, privacy, remaining NFRs) → `later-phases.md`
