# Resume Curator `[P2]`

Not needed for P1.

## Constraint, restated precisely
This is *curation*, not regeneration. Minor, targeted edits only — never disturb the resume's existing formatting or structure; layer in JD-relevant content without rewriting wholesale.

## Chosen approach: statement-level, provenance-tracked splicing
1. Parse the resume's LaTeX source into addressable statements (bullets, summary, skills lines), each with a stable ID and exact character span in the original source
2. Compare against the JD; identify which specific statements are worth tailoring
3. Rewrite *only* those statements, grounded strictly in facts already present in the user's stored profile — never inventing skills, employers, metrics, or experience not already there (critic agent verifies this)
4. Splice the edited statements back into the *original* source at their exact spans — nothing else touched
5. Recompile to PDF for preview and download

## The PDF-only fork
True PDF→LaTeX visual reconstruction is unsolved industry-wide, not a gap unique to this project (even funded competitors require `.tex` input or list PDF support as "planned"). Two paths for non-`.tex` uploads:
- **(a)** Ask the user for a `.tex`/Overleaf source if they have one
- **(b)** For PDF/Word-only uploads, fall back to a clean pre-built, ATS-friendly LaTeX template — honestly presented as a new layout, not a promise to preserve their original design

## Requirements
- FR-CURATOR-1: `.tex`-sourced resumes use statement-level splice editing — formatting untouched outside edited spans
- FR-CURATOR-2: PDF/Word-only resumes fall back to the clean template, honestly labeled
- FR-CURATOR-3: Output is a downloadable rendered PDF plus the underlying `.tex`

## Acceptance
A `.tex` upload tailored against two different JDs produces two outputs with identical formatting/macros outside the edited bullets.

## Known risk (flagged, not yet resolved — see /docs/competitive-analysis.md)
Preserving a user's *original* layout can mean preserving an already ATS-risky layout (e.g. two-column templates are documented to misparse on Workday-style ATS). Open question: should the curator warn the user about this even while still preserving the layout as instructed? Not decided yet — raise it when this module is actually built.
