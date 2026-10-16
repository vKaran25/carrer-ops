<script lang="ts">
  import Icon from './Icon.svelte';
  import { api, message, refreshWorkspace, titleCase } from './api';
  import type { Job } from './types';
  export let job: Job;
  export let onclose: () => void;
  export let onupdated: () => void = () => {};
  let detail: Job | null = null;
  let loadedId = -1;
  let busy = false;
  let error = '';
  let nextStatus = '';
  let outcome = '';
  $: if (job.id !== loadedId) { loadedId = job.id; detail = null; error = ''; load(job.id); }
  async function load(id: number) {
    try {
      const value = await api<Job>(`/jobs/${id}`);
      if (loadedId !== id) return;
      detail = value; nextStatus = value.status; outcome = value.application?.outcome || '';
    } catch (e) { if (loadedId === id) error = message(e); }
  }
  async function update(applied = false) {
    if (busy) return;
    busy = true; error = ''; const id = job.id;
    try {
      await api(`/jobs/${id}/${applied ? 'mark-applied' : 'status'}`, {
        method: applied ? 'POST' : 'PATCH',
        body: JSON.stringify(applied ? {explicit_action:true} : {status:nextStatus, outcome:['interviewing','resolved'].includes(nextStatus) ? outcome || null : null})
      });
      await load(id); refreshWorkspace(); onupdated();
    } catch (e) { error = message(e); } finally { busy = false; }
  }
</script>
<section class="detail panel" aria-label="Job details">
  <div class="row between"><span class="eyebrow">JOB DETAILS</span><button class="icon-button" aria-label="Close job details" onclick={onclose}><Icon name="close" size={18}/></button></div>
  <p class="company">{job.company}</p><h2>{job.title}</h2>
  <div class="meta"><span><Icon name="pin" size={13}/>{job.location}</span><span class="badge">{titleCase(detail?.status || job.status)}</span></div>
  <a class="text-link" href={job.url} target="_blank" rel="noopener noreferrer">Open original posting <Icon name="external" size={12}/></a>
  {#if error}<div class="error" role="alert">{error}</div>{/if}
  {#if !detail&&!error}<p class="loading-line"><span class="spinner"></span>Loading job details…</p>{/if}
  {#if detail?.explanation}<details class="fit"><summary>Match explanation{detail.fit_score !== null ? ` · ${detail.fit_score} points` : ''}</summary><p>{detail.explanation}</p><small>Content match, not a hiring probability.</small></details>{/if}
  <details open class="jd"><summary>Job description</summary><p>{detail?.description || job.description || job.snippet || 'Description unavailable. Check the original posting.'}</p></details>
  {#if detail}
    <div class="tracking"><h3>Update your tracker</h3>
      {#if !detail.application?.applied_at}<p>Submitted on the employer’s site? Record your application here.</p><button class="primary" disabled={busy} onclick={() => update(true)}>{busy?'Updating…':'Mark as applied'}</button><small>This records your action and does not submit an application.</small>{:else}<span class="badge green">Applied by your action</span>{/if}
      <form onsubmit={(e)=>{e.preventDefault();update();}}>
        <label class="field">Stage<select class="input" bind:value={nextStatus} disabled={busy}>
          {#if !detail.application?.applied_at}<option value="interested">Interested</option>{/if}
          {#if detail.application?.applied_at}<option value="applied" disabled>Applied</option><option value="interviewing">Interviewing</option>{/if}
          <option value="resolved">Resolved</option>
        </select></label>
        {#if detail.application?.applied_at&&['interviewing','resolved'].includes(nextStatus)}<label class="field">Outcome<select class="input" bind:value={outcome} disabled={busy}><option value="">Choose an outcome</option>{#each ['interview','offer','rejected','no_response','withdrawn'] as value}<option value={value}>{titleCase(value)}</option>{/each}</select></label>{/if}
        <button type="submit" disabled={busy||nextStatus===detail.status||nextStatus==='applied'}>{busy?'Updating…':'Update stage'}</button>
      </form>
    </div>
  {/if}
</section>
<style>
  .detail{min-width:0;align-self:start;padding:22px;position:sticky;top:20px}.company{font-size:12px;color:#73839a;margin:18px 0 7px}h2{font-size:19px;line-height:1.5}.meta{margin:14px 0;flex-wrap:wrap}.text-link{margin-bottom:18px}.error{margin:14px 0}details{margin:18px 0;font-size:12px}summary{cursor:pointer;color:#49658c;font-weight:600}details p{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.8;color:#60748f;margin:12px 0;max-height:420px;overflow:auto}small{display:block;color:#73839a;font-size:10px;line-height:1.7}.fit{padding:12px;background:#f4f7ff;border-radius:8px}.tracking{border-top:1px solid var(--line);margin-top:20px;padding-top:20px}.tracking h3{font-size:14px}.tracking p{font-size:12px;color:#73839a;line-height:1.7;margin:10px 0}.tracking>button{margin:8px 0}.tracking form{display:grid;gap:12px;margin-top:16px}@media(max-width:900px){.detail{position:static}}
</style>
