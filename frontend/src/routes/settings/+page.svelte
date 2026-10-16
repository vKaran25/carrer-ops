<script lang="ts">
  import { onMount } from 'svelte';
  import SearchMemory from '#lib/SearchMemory.svelte';
  import { api, message } from '#lib/api';
  import type { Bootstrap } from '#lib/types';
  let bootstrap: Bootstrap | null = null;
  let error = '';
  let deleting = false;
  async function deleteAccount(){
    if(!window.confirm('Delete your account and all active workspace data? There is no application backup. This cannot be undone.'))return;
    deleting=true;error='';
    try{
      await api('/account',{method:'DELETE',body:JSON.stringify({confirm:true})});
      await fetch('/auth/signout',{method:'POST'});
      window.location.assign('/login?deleted=1');
    }catch(e){error=message(e);deleting=false;}
  }
  onMount(async()=>{try{bootstrap=await api<Bootstrap>('/bootstrap');}catch(e){error=message(e);}});
</script>
<svelte:head><title>Settings — Career Ops</title></svelte:head>
<div class="page-heading"><div><p class="eyebrow">YOUR WORKSPACE</p><h1>Settings</h1><p>Manage your search preferences and understand how your data is used.</p></div></div>
{#if error}<div class="error" role="alert">{error}</div>{/if}
<div class="settings-grid">
  {#if bootstrap?.auth_mode==='supabase'}<section class="panel"><h2>Account</h2><p class="muted">{bootstrap.account_email}</p><form method="POST" action="/auth/signout"><button type="submit">Sign out</button></form><p class="fine-print">Deleting your account removes active resumes, history, preferences, tracker records and owned artifacts immediately, revokes beta access, and queues Supabase Auth deletion. No application backup is retained. Infrastructure/provider retention remains subject to their policies.</p><button class="danger delete-account" disabled={deleting} onclick={deleteAccount}>{deleting?'Deleting…':'Delete account and workspace'}</button></section>{/if}
  <section class="panel"><h2>Search preferences</h2><p class="muted">Save defaults explicitly. A specific query can override them.</p><SearchMemory modelConfigured={!!bootstrap?.model_configured}/></section>
  <section class="panel"><h2>Service status</h2><dl><div><dt>Resume and query processing</dt><dd>{bootstrap?bootstrap.model_configured?'Available':'Unavailable':'Loading…'}</dd></div><div><dt>Web discovery</dt><dd>{bootstrap?bootstrap.web_search_configured?'Available':'Unavailable':'Loading…'}</dd></div><div><dt>Employer sources</dt><dd>{bootstrap?bootstrap.source_count+' enabled':'Loading…'}</dd></div></dl><p class="fine-print">Provider limits or unavailable sources may reduce results. Search messages show any failures.</p></section>
  <section class="panel privacy"><h2>Your data and control</h2><p>Resume statements are processed through OpenRouter to extract your recorded skills and experience. Queries use OpenRouter to interpret search instructions. Calls request providers that deny training data collection.</p><p>Resume embeddings run locally. Tavily receives job-search terms and requested locations, rather than your raw resume or identity statements.</p><p>Fit scores measure content match. They do not predict hiring outcomes. Jobs enter the tracker only when you choose Interested, and Applied requires your explicit action.</p><p>Remove your current resume beside the search composer. Your search history is retained so you can revisit job descriptions.</p></section>
</div>
<style>
  .settings-grid{display:grid;gap:20px;max-width:1000px}.panel{padding:24px;min-width:0}h2{font-size:16px;margin-bottom:12px}.muted,.privacy p{font-size:12px;line-height:1.8;margin-bottom:14px}dl{font-size:12px}dl div{display:flex;justify-content:space-between;gap:18px;padding:12px 0;border-bottom:1px solid var(--line)}dd{margin:0;color:#486b9b}.fine-print{margin-top:14px}.privacy{background:#f6f9ff}.privacy p{color:#657994}.delete-account{margin-top:16px}
</style>
