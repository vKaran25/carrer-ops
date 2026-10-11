<script lang="ts">
  import Icon from './Icon.svelte';
  import { titleCase } from './api';
  import type { Profile } from './types';
  export let profile: Profile;
</script>

<div class="row between resume-heading">
  <div class="row"><Icon name="file" size={23}/><div class="filename"><strong>{profile.filename}</strong><small>{profile.structured_facts.facts.length} resume statements · Used for every search</small></div></div>
</div>
<details class="resume-details">
  <summary>Review resume details</summary>
  <p class="fine-print">These statements are copied from your uploaded resume and used to match jobs.</p>
  {#if profile.layout_advisory}<div class="notice">{profile.layout_advisory}</div>{/if}
  <p class="fine-print">{profile.latex_source ? 'Your existing .tex layout is preserved outside curated statements.' : 'Resume curation creates a new clean layout from your stored facts.'}</p>
  <div class="facts">{#each profile.structured_facts.facts as fact}<div class="fact"><span class="badge blue">{titleCase(fact.category)}</span><p>{fact.text}</p></div>{/each}</div>
  <details><summary>View extracted source text</summary><pre>{profile.raw_resume_text}</pre></details>
</details>

<style>
  .resume-heading{gap:12px;flex-wrap:wrap}.resume-heading>.row{min-width:0;flex:1}.resume-heading :global(svg){flex-shrink:0;color:var(--blue)}.filename{min-width:0}.filename strong{display:block;font-size:12px;overflow-wrap:anywhere}.filename small{display:block;font-size:10px;color:#8190a8;margin-top:5px}.resume-details{margin-top:14px}.resume-details summary{font-size:11px}.resume-details .fine-print{margin:12px 0}.facts{display:grid;gap:10px;margin:15px 0;max-height:320px;overflow:auto}.fact p{white-space:pre-wrap}.resume-details pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:250px;overflow:auto;font-size:11px;line-height:1.7}
</style>
