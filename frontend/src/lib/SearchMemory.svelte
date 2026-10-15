<script lang="ts">
  import { onMount } from 'svelte';
  import { api, message } from './api';
  export let disabled=false;
  export let modelConfigured=false;
  type Memory={active:boolean;last_query:string;resume_changed:boolean;effective_filters:string[];preferences:{query:string}|null};
  let memory:Memory|null=null;
  let preference='';let busy=false;let error='';let notice='';let dirty=false;
  async function load(){try{memory=await api<Memory>('/search/context');if(!dirty)preference=memory.preferences?.query||'';}catch(e){error=message(e);}}
  onMount(()=>{load();const update=()=>{load();};window.addEventListener('workspace-update',update);return()=>window.removeEventListener('workspace-update',update);});
  async function change(path:string,method:string){
    busy=true;error='';notice='';
    try{memory=await api<Memory>(path,{method,...(method==='PUT'?{body:JSON.stringify({query:preference.trim()})}:{})});if(!path.endsWith('context')){preference=memory.preferences?.query||'';dirty=false;}notice=path.endsWith('context')?'New search started. History, resume and saved preferences are kept.':method==='PUT'?'Search preferences saved. Explicit query changes override these defaults.':'Saved preferences removed.';}
    catch(e){error=message(e);}finally{busy=false;}
  }
</script>

<details class="memory-panel"><summary>Search memory {#if memory?.active}<span>· Active search</span>{:else}<span>· New search</span>{/if}{#if memory?.preferences}<span>· Saved preferences</span>{/if}</summary>
  <div class="memory-content">
    {#if error}<p class="error" role="alert">{error}</p>{/if}{#if notice}<p role="status">{notice}</p>{/if}
    <div class="row between"><p>{memory?.active?`Continuing from: ${memory.last_query||'Resume-based search'}`:'No active intent. Enter a complete search to begin.'}</p><button type="button" disabled={disabled||busy||!memory?.active} onclick={()=>change('/search/context','DELETE')}>New search</button></div>
    <p>Follow-ups can reuse the last successful search. A new standalone query starts another intent; an empty query uses your resume and saved defaults.</p>
    {#if memory?.resume_changed}<p>Resume changed. Only explicit filters are retained; matches use your current resume.</p>{/if}
    <ul aria-label="Current effective search filters">{#each memory?.effective_filters||[] as filter}<li>{filter}</li>{/each}</ul>
    <form onsubmit={(e)=>{e.preventDefault();change('/search/preferences','PUT');}}><label for="saved-search-preferences">Saved search preferences</label><textarea id="saved-search-preferences" bind:value={preference} oninput={()=>dirty=true} maxlength="2000" rows="2" disabled={disabled||busy||!memory?.effective_filters} placeholder="For example: jobs in India, prefer junior roles"></textarea><p>Saved only when you click Save. Required filters remain strict. New queries override the same fields; New search keeps these defaults.</p><div class="row"><button type="submit" disabled={disabled||busy||!modelConfigured||!preference.trim()}>{busy?'Saving…':'Save search preferences'}</button><button type="button" disabled={disabled||busy||!memory?.preferences} onclick={()=>change('/search/preferences','DELETE')}>Remove saved preferences</button></div></form>
  </div>
</details>

<style>
  .memory-panel{flex-shrink:0;margin:0 0 12px;border:1px solid var(--line);background:white;border-radius:9px;font-size:11px;overflow:auto;max-height:260px}.memory-panel>summary{position:sticky;top:0;z-index:1;background:white;padding:10px 13px;color:#49658a}.memory-panel>summary span{font-size:10px;color:#7b8ba0}.memory-content{padding:0 13px 13px}.memory-content p{font-size:11px;color:#64758b;line-height:1.65;margin:9px 0;overflow-wrap:anywhere}.memory-content button{font-size:10px;flex-shrink:0}.memory-content ul{display:flex;flex-wrap:wrap;list-style:none;gap:6px;padding:0;margin:10px 0}.memory-content li{padding:5px 8px;background:#eff5ff;border-radius:6px;color:#49658a;font-size:10px;overflow-wrap:anywhere}.memory-content form{border-top:1px solid var(--line);margin-top:12px;padding-top:12px}.memory-content label{display:block;font-weight:600;margin-bottom:6px}.memory-content textarea{width:100%;box-sizing:border-box;resize:vertical;border:1px solid var(--line);border-radius:7px;padding:9px;font:inherit;min-height:50px}.memory-content .row{flex-wrap:wrap}
</style>
