<script lang="ts">
  import Icon from './Icon.svelte';
  import { api, message, refreshWorkspace, titleCase } from './api';
  import type { Job } from './types';
  export let job: Job;
  export let turnId: number;
  export let oninterested: () => Promise<void>;
  let saving = false;
  let error = '';
  $: tracked = job.status !== 'discovered' && job.status !== 'dismissed';
  async function interested() {
    if (saving || tracked) return;
    saving=true; error='';
    try { await api(`/jobs/${job.id}/interest`, {method:'POST',body:JSON.stringify({turn_id:turnId})}); await oninterested(); refreshWorkspace(); }
    catch(e) {error=message(e);} finally {saving=false;}
  }
</script>

<details class="chat-job">
  <summary><div class="job-summary"><span class="company">{job.company}</span><h3>{job.title}</h3><div class="meta"><span><Icon name="pin" size={12}/>{job.location}</span>{#if job.posted_at}<span>Posted {new Date(job.posted_at).toLocaleDateString(undefined,{month:'short',day:'numeric'})}</span>{/if}{#if tracked}<span class="badge blue">{titleCase(job.status)}</span>{:else if job.status==='dismissed'}<span class="badge">Removed from Interested</span>{/if}</div></div><div class="summary-end">{#if job.fit_score !== null}<span class="score" class:low={job.fit_score<50}>{job.fit_score}<small>resume fit</small></span>{/if}<span class="chevron"><Icon name="arrow" size={15}/></span></div></summary>
  <div class="job-content"><h4>Job description</h4><p class="jd">{job.description || job.description_snippet || job.snippet || 'The source did not provide a full description. Open the original posting for details.'}</p><details class="fit-details"><summary>Why this job matches</summary><p>{job.explanation || 'Fit information is unavailable for this search.'}</p><small>Content similarity, not a probability of being hired.</small></details>
    {#if error}<div class="error" role="alert">{error}</div>{/if}
    <div class="job-actions"><a class="text-link" href={job.url} target="_blank" rel="noopener noreferrer">Original posting <Icon name="external" size={12}/></a>{#if tracked}<a class="button-link" href="/tracker">In {titleCase(job.status)} · Open tracker <Icon name="arrow" size={12}/></a>{:else}<button class="primary" disabled={saving} onclick={interested}>{#if saving}<span class="spinner"></span>Adding…{:else}<Icon name="plus" size={14}/>{job.status==='dismissed'?'Interested again':'Interested'}{/if}</button>{/if}</div>
  </div>
</details>

<style>
  .chat-job{background:white;border:1px solid var(--line);border-radius:12px;overflow:hidden}.chat-job>summary{display:flex;justify-content:space-between;align-items:center;gap:15px;padding:17px 18px;list-style:none;color:var(--ink)}.chat-job>summary::-webkit-details-marker{display:none}.chat-job>summary:hover{background:#fafcff}.chat-job>summary:focus-visible{outline:3px solid #93b7ff;outline-offset:-3px}.job-summary{min-width:0}.company{font-size:11px;color:#6d7d93}.job-summary h3{font-size:13px;margin:5px 0 9px;overflow-wrap:anywhere}.summary-end{display:flex;align-items:center;gap:13px;flex-shrink:0}.chevron{display:flex;color:#8396b2;transform:rotate(90deg);transition:transform .15s}.chat-job[open] .chevron{transform:rotate(-90deg)}.job-content{border-top:1px solid var(--line);padding:18px}.job-content h4{font-size:12px;margin:0 0 10px}.jd{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;line-height:1.85;max-height:350px;overflow:auto;color:#526178}.fit-details{margin:18px 0}.fit-details p{font-size:11px;margin:10px 0;color:#64758c;line-height:1.8}.fit-details small{font-size:10px;color:#7b8ba0}.job-actions{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;padding-top:15px;border-top:1px solid var(--line);margin-top:16px}.job-actions button,.job-actions .button-link{font-size:11px}.job-content .error{margin-bottom:12px}@media(max-width:700px){.chat-job>summary{padding:14px 12px;gap:8px}.job-content{padding:14px}.summary-end{gap:8px}.score{font-size:11px}.job-summary h3{font-size:12px}.meta{font-size:10px;gap:6px}.job-actions .button-link{font-size:10px}}
</style>
