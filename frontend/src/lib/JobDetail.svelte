<script lang="ts">
  import Icon from './Icon.svelte';
  import { api, message, refreshWorkspace, titleCase } from './api';
  import type { Bootstrap, Job, Research } from './types';
  export let job: Job;
  export let onclose: () => void;
  export let onupdated: () => void = () => {};
  let detail: Job | null = null;
  let bootstrap: Bootstrap | null = null;
  let loadedId = -1;
  let tab = 'overview';
  let busy = '';
  let error = '';
  let research: Research | null = null;
  let nextStatus = '';
  let outcome = '';
  $: fitScore = detail ? detail.fit_score : job.fit_score;
  $: if (job.id !== loadedId) { loadedId = job.id; detail = null; research = null; tab = 'overview'; error = ''; load(); }
  async function load() {
    try { [detail, bootstrap] = await Promise.all([api<Job>(`/jobs/${job.id}`), api<Bootstrap>('/bootstrap')]); nextStatus = detail.status; outcome = detail.application?.outcome || ''; }
    catch (e) { error = message(e); }
  }
  async function action(name: string) {
    busy = name; error = '';
    try {
      const result = await api<Research>(`/jobs/${job.id}/${name}`, {method:'POST', body: name === 'mark-applied' ? JSON.stringify({explicit_action:true}) : undefined});
      if (name === 'research') { research = result; tab = 'research'; }
      if (name === 'tailor' || name === 'curate') tab = 'application';
      await load(); refreshWorkspace(); onupdated();
    } catch(e) { error = message(e); } finally { busy = ''; }
  }
  async function changeStatus() {
    busy = 'status'; error = '';
    try { await api(`/jobs/${job.id}/status`, {method:'PATCH', body:JSON.stringify({status:nextStatus, outcome: ['resolved','interviewing'].includes(nextStatus) ? outcome || null : null})}); await load(); refreshWorkspace(); onupdated(); }
    catch(e) { error = message(e); } finally { busy = ''; }
  }
  async function discard() {
    busy = 'discard'; error = '';
    try { await api(`/jobs/${job.id}/draft`, {method:'DELETE'}); await load(); refreshWorkspace(); onupdated(); }
    catch(e) { error = message(e); } finally { busy = ''; }
  }
  function downloadDraft() {
    const content = (detail?.application?.draft?.bullets.map(c => '- '+c.text).join('\n') || '') + '\n\n' + (detail?.application?.tailored_cover_letter || '');
    const url = URL.createObjectURL(new Blob([content], {type:'text/plain'}));
    const link = document.createElement('a'); link.href=url; link.download='application-draft.txt'; link.click(); URL.revokeObjectURL(url);
  }
</script>
<section class="detail panel" aria-label="Job details">
  <div class="detail-heading row between"><span class="eyebrow" style="margin:0">JOB DETAILS</span><button class="icon-button" aria-label="Close job details" onclick={onclose}><Icon name="close" size={18}/></button></div>
  <div class="row between" style="align-items:flex-start;margin-top:20px"><div><span class="company-name">{job.company}</span><h2 class="detail-title">{job.title}</h2></div>{#if fitScore !== null}<span class="score" class:low={fitScore < 50}>{fitScore}<small>fit score</small></span>{/if}</div>
  <div class="meta" style="margin-top:14px"><span><Icon name="pin" size={13}/>{job.location}</span><span class="badge status-pill">{detail?.status || job.status}</span></div>
  <a class="text-link" href={job.url} target="_blank" rel="noopener noreferrer" style="margin-top:18px">Open original posting <Icon name="external" size={12}/></a>
  <div class="detail-tabs" role="tablist" aria-label="Job detail sections">{#each ['overview','application','research'] as name}<button role="tab" aria-selected={tab===name} class:current={tab===name} onclick={() => tab=name}>{titleCase(name)}</button>{/each}</div>
  {#if error}<div class="error" role="alert" style="margin:16px 0">{error}</div>{/if}
  {#if busy}<div class="loading-line" role="status" style="margin:16px 0"><span class="spinner"></span>{busy === 'research' ? 'Checking public sources…' : busy === 'curate' ? 'Checking facts and compiling your resume…' : busy === 'tailor' ? 'Preparing and fact-checking a draft…' : 'Updating your tracker…'}</div>{/if}
  {#if !detail && !error}<div class="loading-line" style="padding:25px 0"><span class="spinner"></span>Loading job details…</div>{/if}
  {#if tab === 'overview'}
    {#if job.explanation || detail?.explanation}<div class="match-note"><div class="row"><Icon name="sparkle" size={15}/><strong>Why this role appears</strong></div><p>{detail?.explanation || job.explanation}</p><small>Content match, not your probability of being hired.</small></div>{/if}
    <h3 class="content-heading">About the role</h3><p class="description">{detail?.description || job.description || job.description_snippet || job.snippet || 'The source did not provide a full description. Read the original posting for details.'}</p>
    <div class="divider"></div><h3 class="content-heading">Next steps, on your terms</h3><p class="muted" style="font-size:11px;margin-bottom:14px">Create materials or research this company when you are ready.</p>
    <div class="action-grid"><button disabled={!!busy || !bootstrap?.model_configured || !bootstrap?.resume} onclick={() => action('tailor')}><Icon name="file" size={15}/>Tailor draft</button><button disabled={!!busy || !bootstrap?.model_configured || !bootstrap?.resume || !bootstrap?.pdf_compiler_available} onclick={() => action('curate')}><Icon name="sparkle" size={15}/>Curate resume</button><button disabled={!!busy || !bootstrap?.model_configured} onclick={() => action('research')}><Icon name="search" size={15}/>Research company</button></div>
    {#if !bootstrap?.model_configured}<p class="fine-print" style="margin-top:10px"><a href="/settings">Set up a free model</a> to use these actions.</p>{:else if !bootstrap?.resume}<p class="fine-print" style="margin-top:10px"><a href="/resume">Upload a resume</a> to tailor or curate grounded materials.</p>{/if}
  {:else if tab === 'application'}
    {#if detail?.application?.draft}
      <div class="row between" style="margin:18px 0"><h3>Your draft</h3><span class="badge" class:green={detail.application.critique?.passed} class:amber={!detail.application.critique?.passed}>{detail.application.critique?.passed ? 'Facts verified' : 'Needs review'}</span></div>
      {#each detail.application.draft.bullets as claim}<div class="draft-claim">{claim.text}<small>{claim.fact_ids.length} stored fact{claim.fact_ids.length===1?'':'s'} cited</small></div>{/each}
      {#if !detail.application.critique?.passed}<div class="error" style="margin-top:13px">{detail.application.critique?.reason || 'The critic blocked unverified claims. Create a fresh draft or discard this one before marking applied.'}</div>{/if}
      <details class="section-gap"><summary>Cover letter draft</summary><p class="description" style="margin-top:13px">{detail.application.tailored_cover_letter}</p></details>
      <div class="row" style="margin-top:18px"><button onclick={downloadDraft}><Icon name="download" size={14}/>Download draft</button><button class="subtle-button danger" disabled={!!busy} onclick={discard}>Discard draft</button></div>
    {:else}<div class="empty-state" style="padding:32px 12px"><div class="empty-icon"><Icon name="file" size={26}/></div><h3>A draft for this role</h3><p>Relevant experience from your stored resume, checked by the critic before you use it.</p><button class="primary" disabled={!!busy || !bootstrap?.model_configured || !bootstrap?.resume} onclick={() => action('tailor')}>Create a tailored draft</button></div>{/if}
    {#if detail?.application?.curated_resume}<div class="divider"></div><h3 class="content-heading">Curated resume</h3><div class="notice">{detail.application.curated_resume.layout_note}. {detail.application.curated_resume.edit_count} targeted edits.</div>{#if detail.application.curated_resume.layout_advisory}<div class="notice" style="margin-top:12px">{detail.application.curated_resume.layout_advisory}</div>{/if}<div class="row" style="margin-top:12px;flex-wrap:wrap"><a class="button-link" href={detail.application.curated_resume.pdf_url} target="_blank" rel="noopener noreferrer">Preview PDF <Icon name="external" size={12}/></a><a class="button-link" href={detail.application.curated_resume.pdf_url} download="resume.pdf">Download PDF</a><a class="button-link" href={detail.application.curated_resume.tex_url}>Download .tex</a></div>{/if}
    <p class="fine-print" style="margin-top:18px">All materials are drafts. Review them before submitting on the original career site.</p>
  {:else}
    {#if research}
      <div class="row between" style="margin-top:18px"><h3>Public interview research</h3>{#if research.cached}<span class="badge">Cached</span>{/if}</div><p class="muted" style="font-size:11px;margin-top:8px">Source accounts can vary by role, location, and date.</p>
      {#if !research.sufficient_information}<div class="notice" style="margin-top:18px"><Icon name="info" size={17}/><span>{research.difficulty_note}. We do not infer a process when evidence is insufficient.</span></div>{:else}{#each research.rounds as round}<div class="research-round"><h3>{round.name}</h3><span class="badge" style="margin:7px 0">{round.type}</span><p>{round.focus_areas.join(', ')}</p><p><strong>Question types:</strong> {round.example_question_types.join(', ') || 'Not documented'}</p><p><strong>Difficulty:</strong> {round.difficulty || 'Not documented'}</p>{#each round.evidence as source}<details><summary>Source evidence</summary><blockquote>{source.quote}</blockquote><a class="text-link" href={research.sources[source.source_index]?.url} target="_blank" rel="noopener noreferrer">Read source <Icon name="external" size={12}/></a></details>{/each}</div>{/each}{/if}
      {#if research.sufficient_information && research.difficulty_note!=='Not documented'}<p class="description" style="margin-top:16px">{research.difficulty_note}</p>{/if}{#if research.sufficient_information && research.prep_tips.length}<h3 class="content-heading">Preparation evidence</h3><ul class="description">{#each research.prep_tips as tip}<li>{tip}</li>{/each}</ul>{/if}{#if research.sources.length}<details class="section-gap"><summary>{research.sources.length} public sources checked</summary>{#each research.sources as source}<a class="source-link" href={source.url} target="_blank" rel="noopener noreferrer">{source.title || source.url}<Icon name="external" size={11}/></a>{/each}</details>{/if}
    {:else}<div class="empty-state" style="padding:32px 12px"><div class="empty-icon"><Icon name="search" size={26}/></div><h3>Know what to expect</h3><p>Research reported rounds and question types from public sources. If evidence is sparse, we will say so.</p><button class="primary" disabled={!!busy || !bootstrap?.model_configured} onclick={() => action('research')}>Research this company</button></div>{/if}
  {/if}
  {#if detail}<div class="approval-section"><h3>Keep your tracker current</h3>{#if !detail.application?.applied_at}<p>Already submitted on the career site? Record it here.</p><button class="primary" style="width:100%;margin-top:13px" disabled={!!busy || detail.application?.critique?.passed === false} onclick={() => action('mark-applied')}><Icon name="check" size={16}/>Mark as applied</button><small>This records your action. It does not submit an application.</small>{:else}<span class="badge green" style="margin:10px 0"><Icon name="check" size={12}/>Applied by your action</span><div class="stack" style="gap:10px"><label class="field">Pipeline status<select class="input" bind:value={nextStatus}><option value="applied" disabled>Applied</option><option value="interviewing">Interviewing</option><option value="resolved">Resolved</option></select></label>{#if nextStatus==='resolved' || nextStatus==='interviewing'}<label class="field">Outcome<select class="input" bind:value={outcome}><option value="">Choose outcome</option><option value="interview">Interview</option><option value="offer">Offer</option><option value="rejected">Rejected</option><option value="no_response">No response</option><option value="withdrawn">Withdrawn</option></select></label>{/if}<button disabled={!!busy || nextStatus==='applied'} onclick={changeStatus}>Update tracker</button></div>{/if}</div>{/if}
</section>
<style>
  .detail{min-width:0;align-self:start;padding:22px;position:sticky;top:20px}.company-name{font-size:11px;color:#8793a7}.detail-title{font-size:18px;line-height:1.5;margin-top:6px;padding-right:14px}.detail-tabs{display:flex;gap:20px;border-bottom:1px solid var(--line);margin-top:22px}.detail-tabs button{border:0;border-bottom:2px solid transparent;border-radius:0;padding:12px 0;color:#8793a7;background:transparent;font-size:11px}.detail-tabs button.current{border-color:var(--blue);color:var(--blue)}.match-note{background:#f4f7ff;border:1px solid #e6ecfb;border-radius:8px;padding:14px;margin:20px 0;color:#5f79a8;font-size:11px}.match-note strong{font-weight:600;color:#48679b}.match-note p{margin-top:10px;line-height:1.75}.match-note small{display:block;font-size:9px;color:#94a5c1;margin-top:10px}.content-heading{font-size:12px;margin:20px 0 10px}.description{font-size:12px;line-height:1.85;white-space:pre-wrap;color:#738097;max-height:340px;overflow:auto;overflow-wrap:anywhere}.action-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.action-grid button{font-size:10px;padding:10px 5px}.action-grid button:last-child{grid-column:1/-1}.approval-section{margin:25px -22px -22px;padding:21px 22px;background:#fafbfd;border-top:1px solid var(--line);border-radius:0 0 13px 13px}.approval-section h3{font-size:12px}.approval-section p{font-size:11px;color:#8c97a9;margin-top:7px}.approval-section small{display:block;text-align:center;color:#a0a9b8;font-size:9px;margin-top:10px}.draft-claim{border:1px solid var(--line);padding:12px;border-radius:7px;font-size:12px;line-height:1.7;margin-top:9px}.draft-claim small{display:block;font-size:9px;color:#91a0b3;margin-top:8px}.research-round{border:1px solid var(--line);border-radius:8px;padding:14px;margin-top:15px}.research-round h3{font-size:12px}.research-round p{font-size:11px;line-height:1.7;margin-bottom:8px;color:#7a879b}.research-round details{margin-top:10px}.source-link{display:flex;gap:8px;font-size:11px;margin-top:10px;line-height:1.6;overflow-wrap:anywhere}blockquote{font-size:11px;line-height:1.7;color:#8190a4;border-left:2px solid #d4dff2;margin:10px 0;padding-left:10px}@media(max-width:900px){.detail{position:static}.action-grid{grid-template-columns:1fr 1fr 1fr}.action-grid button:last-child{grid-column:auto}}
</style>
