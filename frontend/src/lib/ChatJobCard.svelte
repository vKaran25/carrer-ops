<script lang="ts">
  import { tick } from 'svelte';
  import Icon from './Icon.svelte';
  import { api, message, refreshWorkspace, titleCase } from './api';
  import type { Job } from './types';
  export let job: Job;
  export let turnId: number;
  export let oninterested: (id: number, status: string) => Promise<void>;
  let saving = false;
  let error = '';
  let expanded = false;
  let fitExpanded = false;
  let fitSummary: HTMLElement;
  $: evidence=job.metadata||job.source_metadata;
  async function showScore(event: MouseEvent) {
    event.preventDefault(); event.stopPropagation();
    expanded=true; fitExpanded=true;
    await tick(); fitSummary?.focus(); fitSummary?.scrollIntoView({block:'start',behavior:'instant'});
  }
  $: tracked = job.status !== 'discovered' && job.status !== 'dismissed';
  async function interested() {
    if (saving || tracked) return;
    saving=true; error='';
    try { const application=await api<{status:string}>(`/jobs/${job.id}/interest`, {method:'POST',body:JSON.stringify({turn_id:turnId})}); await oninterested(job.id,application.status); refreshWorkspace(); }
    catch(e) {error=message(e);} finally {saving=false;}
  }
</script>

<details class="chat-job" bind:open={expanded}>
  <summary><div class="job-summary"><span class="company">{job.company}</span><h3>{job.title}</h3><div class="meta"><span><Icon name="pin" size={12}/>{job.location}</span>{#if job.posted_at}<span>Posted {new Date(job.posted_at).toLocaleDateString(undefined,{month:'short',day:'numeric'})}</span>{/if}{#if tracked}<span class="badge blue">{titleCase(job.status)}</span>{:else if job.status==='dismissed'}<span class="badge">Removed from Interested</span>{/if}</div>{#if job.score_breakdown?.location}<small class="location-label">{job.score_breakdown.location.distance_km===null?'Distance unknown':job.score_breakdown.location.within_radius?'Inside radius':'Outside radius'} · {job.score_breakdown.location.distance_km===null?job.score_breakdown.location.country:`≈ ${job.score_breakdown.location.distance_km} km`}</small>{/if}</div><div class="summary-end">{#if job.fit_score !== null}<button type="button" class="score" class:low={job.fit_score<50} onclick={showScore} aria-label={`Explain fit score ${job.fit_score} for ${job.title}`} aria-expanded={expanded&&fitExpanded}>{job.fit_score}<small>fit · details</small></button>{/if}<span class="chevron"><Icon name="arrow" size={15}/></span></div></summary>
  <div class="job-content"><h4>Job description</h4><p class="jd">{job.description || job.description_snippet || job.snippet || 'The source did not provide a full description. Open the original posting for details.'}</p><details class="fit-details" bind:open={fitExpanded}><summary bind:this={fitSummary}>Why this job matches</summary>
    {#if job.score_breakdown}
      <h4 class="breakdown-heading">Score breakdown</h4>
      <div class="score-table"><table><thead><tr><th>Factor</th><th>Value</th><th>Weight</th><th>Points</th></tr></thead><tbody>{#each job.score_breakdown.components as component}<tr><th scope="row">{component.factor.replaceAll('_',' ')}</th><td>{(component.value*100).toFixed(1)}%</td><td>{(component.weight*100).toFixed(1)}%</td><td>{component.points.toFixed(2)}</td></tr>{/each}<tr class="total"><th scope="row" colspan="3">Overall fit</th><td>{job.score_breakdown.total.toFixed(1)} / 100</td></tr></tbody></table></div>
      <small>Points = value × weight × 100. Displayed values are rounded; final rounding/cap: {job.score_breakdown.rounding_and_cap.toFixed(3)} points.</small>
      {#each job.score_breakdown.components as component}<p><strong>{component.factor.replaceAll('_',' ')}:</strong> {component.evidence}{#if component.query_evidence}<br/>Your preference: “{component.query_evidence}”{/if}</p>{/each}
      {#if job.score_breakdown.location&&job.score_breakdown.location.mode==='required'}<p>{job.score_breakdown.location.evidence}</p>{/if}
      <details><summary>Stored resume statements used for comparison</summary><ul>{#each job.score_breakdown.resume_evidence as statement}<li>{statement}</li>{/each}</ul></details>
      <p>{job.score_breakdown.notice}</p><small>Geography: <a href="https://www.geonames.org/" target="_blank" rel="noopener noreferrer">GeoNames</a>, <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener noreferrer">CC BY 4.0</a>; indexed city data.</small>
    {:else}<p>{job.explanation || 'Fit information is unavailable for this search.'}</p><small>Content similarity, not a probability of being hired. Detailed points are available for new searches.</small>{/if}</details>
    <details class="fit-details"><summary>Source and availability</summary><p>Retrieved: {evidence?.retrieved_at?new Date(evidence.retrieved_at).toLocaleString():'Not recorded for this older result'}. Published: {job.posted_at?new Date(job.posted_at).toLocaleDateString():'Not provided by the source'}.</p>{#if evidence?.expires_at}<p>Source expiry: {new Date(evidence.expires_at).toLocaleDateString()}.</p>{/if}<p>Confirm the opening on the original posting before applying. A retrieved page does not guarantee the vacancy is still open.</p>{#if evidence?.source_url}<a class="text-link" href={evidence.source_url} target="_blank" rel="noopener noreferrer">Publisher page <Icon name="external" size={12}/></a>{/if}</details>
    {#if error}<div class="error" role="alert">{error}</div>{/if}
    <div class="job-actions"><a class="text-link" href={job.url} target="_blank" rel="noopener noreferrer">Original posting <Icon name="external" size={12}/></a>{#if tracked}<a class="button-link" href="/tracker">In {titleCase(job.status)} · Open tracker <Icon name="arrow" size={12}/></a>{:else}<button class="primary" disabled={saving} onclick={interested}>{#if saving}<span class="spinner"></span>Adding…{:else}<Icon name="plus" size={14}/>{job.status==='dismissed'?'Interested again':'Interested'}{/if}</button>{/if}</div>
  </div>
</details>

<style>
  .fit-details>summary:focus-visible{outline:2px solid #93b7ff;outline-offset:3px}
  button.score{cursor:pointer;border:1px solid #c4d8fa;font:inherit;font-weight:650;display:flex;flex-direction:column;align-items:center;min-width:68px;padding:7px 9px}button.score:focus-visible{outline:3px solid #93b7ff;outline-offset:2px}.location-label{display:block;color:#65758b;font-size:10px;margin-top:8px}.breakdown-heading{margin-top:16px!important}.score-table{overflow-x:auto;margin-bottom:10px}table{border-collapse:collapse;width:100%;font-size:11px}th,td{text-align:left;padding:9px 7px;border-bottom:1px solid var(--line)}thead th{color:#64758c;font-weight:500}.total{background:#eff5ff}.fit-details li{font-size:11px;line-height:1.7;overflow-wrap:anywhere}.fit-details ul{padding-left:20px}
  .chat-job{background:white;border:1px solid var(--line);border-radius:12px;overflow:hidden}.chat-job>summary{display:flex;justify-content:space-between;align-items:center;gap:15px;padding:17px 18px;list-style:none;color:var(--ink)}.chat-job>summary::-webkit-details-marker{display:none}.chat-job>summary:hover{background:#fafcff}.chat-job>summary:focus-visible{outline:3px solid #93b7ff;outline-offset:-3px}.job-summary{min-width:0}.company{font-size:11px;color:#6d7d93}.job-summary h3{font-size:13px;margin:5px 0 9px;overflow-wrap:anywhere}.summary-end{display:flex;align-items:center;gap:13px;flex-shrink:0}.chevron{display:flex;color:#8396b2;transform:rotate(90deg);transition:transform .15s}.chat-job[open] .chevron{transform:rotate(-90deg)}.job-content{border-top:1px solid var(--line);padding:18px}.job-content h4{font-size:12px;margin:0 0 10px}.jd{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;line-height:1.85;max-height:350px;overflow:auto;color:#526178}.fit-details{margin:18px 0}.fit-details p{font-size:11px;margin:10px 0;color:#64758c;line-height:1.8}.fit-details small{font-size:10px;color:#7b8ba0}.job-actions{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;padding-top:15px;border-top:1px solid var(--line);margin-top:16px}.job-actions button,.job-actions .button-link{font-size:11px}.job-content .error{margin-bottom:12px}@media(max-width:700px){.chat-job>summary{padding:14px 12px;gap:8px}.job-content{padding:14px}.summary-end{gap:8px}.score{font-size:11px}.job-summary h3{font-size:12px}.meta{font-size:10px;gap:6px}.job-actions .button-link{font-size:10px}}
</style>
