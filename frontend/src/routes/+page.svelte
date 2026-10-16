<script lang="ts">
  import { onMount, tick } from 'svelte';
  import Icon from '#lib/Icon.svelte';
  import ChatJobCard from '#lib/ChatJobCard.svelte';
  import SearchMemory from '#lib/SearchMemory.svelte';
  import ResumeSummary from '#lib/ResumeSummary.svelte';
  import { api, message, refreshWorkspace } from '#lib/api';
  import type { Bootstrap, ChatTurn, Profile, SearchTicket } from '#lib/types';
  let bootstrap: Bootstrap | null=null;
  let profile: Profile | null=null;
  let turns: ChatTurn[]=[];
  let resumeInput: HTMLInputElement;
  let chatScroll: HTMLDivElement;
  let query=''; let ready=false; let loading=false; let uploading=false; let removing=false; let showResume=false; let pendingQuery=''; let error='';
  let activeRun: SearchTicket | null=null; let pollTimer: ReturnType<typeof setTimeout> | undefined; let disposed=false; let pendingKey='';
  const examples=['Java backend jobs in fintech','Jobs matching my resume posted this week','Internships at mid-size companies'];
  async function loadResume(){[bootstrap,profile]=await Promise.all([api<Bootstrap>('/bootstrap'),api<Profile|null>('/resume')]);}
  let hasOlder=false;let loadingOlder=false;let historyEpoch=0;
  async function loadChat(reset=false){
    if(reset)historyEpoch++;const epoch=historyEpoch;
    const latest=await api<ChatTurn[]>('/chat?limit=25');
    if(epoch!==historyEpoch)return;
    if(reset||!turns.length){turns=latest;hasOlder=latest.length===25;return;}
    const messages=new Map(turns.map(t=>[t.id,t]));for(const turn of latest)messages.set(turn.id,turn);
    turns=[...messages.values()].sort((a,b)=>a.id-b.id);
  }
  async function older(){
    if(loadingOlder||!turns.length)return;loadingOlder=true;
    const height=chatScroll.scrollHeight,top=chatScroll.scrollTop,epoch=historyEpoch;
    try{const page=await api<ChatTurn[]>(`/chat?limit=25&before_id=${turns[0].id}`);if(epoch!==historyEpoch)return;turns=[...page,...turns];hasOlder=page.length===25;await tick();chatScroll.scrollTop=top+chatScroll.scrollHeight-height;}
    catch(e){error=message(e);}finally{loadingOlder=false;}
  }
  async function interested(id:number,status:string){turns=turns.map(t=>({...t,result:{...t.result,jobs:t.result.jobs.map(j=>j.id===id?{...j,status}:j)}}));}
  async function scrollToLatest(){await tick();if(chatScroll)chatScroll.scrollTop=chatScroll.scrollHeight;}
  async function observe(run: SearchTicket) {
    if(disposed)return;
    activeRun=run;loading=['queued','running','cancelling'].includes(run.status);pendingQuery=run.query;
    if(loading){pollTimer=setTimeout(poll,1500);return;}
    if(run.status==='succeeded'){sessionStorage.removeItem('career-ops-search-key');pendingKey='';await loadChat();query='';error='';refreshWorkspace();await scrollToLatest();}
    else if(run.status==='failed'||run.status==='interrupted'||run.status==='needs_input')error=run.error||'Search interrupted. Retry when ready.';
  }
  async function poll(){
    if(!activeRun||disposed)return;
    try{await observe(await api<SearchTicket>(`/search/runs/${activeRun.id}`));}
    catch(e){if(!disposed){error=message(e);pollTimer=setTimeout(poll,4000);}}
  }
  async function recoverSearch(){
    const runs=await api<SearchTicket[]>('/search/runs');
    const active=runs.find(r=>['queued','running','cancelling'].includes(r.status));
    if(active)await observe(active);
    else if(pendingKey&&runs[0]?.request_key===pendingKey)await observe(runs[0]);
    else if(runs[0]&&['failed','interrupted','needs_input'].includes(runs[0].status))activeRun=runs[0];
  }
  onMount(()=>{
    disposed=false;pendingKey=sessionStorage.getItem('career-ops-search-key')||'';
    (async()=>{try{await Promise.all([loadResume(),loadChat()]);await recoverSearch();if(window.location.hash==='#resume')showResume=true;}catch(e){error=message(e);}finally{ready=true;await scrollToLatest();}})();
    return()=>{disposed=true;if(pollTimer)clearTimeout(pollTimer);};
  });
  async function cancelSearch(){if(!activeRun)return;try{if(pollTimer)clearTimeout(pollTimer);await observe(await api<SearchTicket>(`/search/runs/${activeRun.id}/cancel`,{method:'POST'}));}catch(e){error=message(e);pollTimer=setTimeout(poll,1500);}}
  async function retrySearch(){if(!activeRun||loading)return;error='';try{await observe(await api<SearchTicket>(`/search/runs/${activeRun.id}/retry`,{method:'POST'}));}catch(e){error=message(e);}}
  async function upload(file:File|undefined){
    if(!file||loading||uploading||removing)return;
    if(!file.name.toLowerCase().endsWith('.docx')){error='Upload a .docx file. Only DOCX resumes are supported for now.';if(resumeInput)resumeInput.value='';return;}
    uploading=true;error='';
    try{const body=new FormData();body.append('file',file);await api('/resume',{method:'POST',body});await Promise.all([loadResume(),loadChat(true)]);refreshWorkspace();showResume=true;}
    catch(e){error=message(e);}finally{uploading=false;if(resumeInput)resumeInput.value='';}
  }
  async function removeResume(){if(loading||uploading||removing)return;removing=true;error='';try{await api('/resume',{method:'DELETE'});await Promise.all([loadResume(),loadChat(true)]);refreshWorkspace();showResume=false;}catch(e){error=message(e);}finally{removing=false;}}
  async function search(){
    if(!profile||uploading||removing||loading)return;
    loading=true;error='';pendingQuery=query.trim();pendingKey=crypto.randomUUID();sessionStorage.setItem('career-ops-search-key',pendingKey);await scrollToLatest();
    try{await observe(await api<SearchTicket>('/search',{method:'POST',body:JSON.stringify({query:pendingQuery,mode:'resume',limit:15,request_key:pendingKey})}));}
    catch(e){error=message(e);loading=false;try{await recoverSearch();}catch{/* Keep the original error visible. */}}
    finally{await scrollToLatest();}
  }
  function submitOnEnter(event:KeyboardEvent){if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();search();}}
</script>

<svelte:head><title>Search chat — Career Ops</title></svelte:head>
<div class="chat-workspace">
  <div class="chat-heading"><div><p class="eyebrow">YOUR JOB SEARCH CONVERSATION</p><h1>Find your next role.</h1><p>Explore matches here. Save the jobs you want with Interested.</p></div><span class="badge">{bootstrap?.auth_mode==='supabase'?'Saved to your account':'Local development'}</span></div>
  <SearchMemory disabled={loading||uploading||removing} modelConfigured={!!bootstrap?.model_configured}/>
  <div class="chat-shell">
    <!-- svelte-ignore a11y_no_noninteractive_tabindex (Scrollable history needs keyboard focus.) -->
    <div class="chat-scroll" bind:this={chatScroll} role="region" aria-label="Job search conversation" tabindex="0">
      {#if !ready}<div class="loading-line" role="status"><span class="spinner"></span>Loading your conversation…</div>
      {:else if !turns.length}<div class="chat-welcome"><span class="welcome-icon"><Icon name="search" size={28}/></span><h2>{profile?'Your resume is ready.':'Start with your resume.'}</h2><p>{profile?'Click Find jobs to search using your resume. Leave the message empty or ask for a specific role.':'Add a .docx resume below, then search for matches. Leave the message empty or ask for a specific role.'}</p><div class="welcome-steps"><span>1. {profile?'Find jobs':'Add resume'}</span><span>2. Explore job details</span><span>3. Choose Interested</span></div><p class="source-note">Searches combine web discovery with supported public employer sources. Coverage varies by role and location.</p></div>{/if}
      {#if hasOlder}<button class="older-messages" disabled={loadingOlder} onclick={older}>{loadingOlder?'Loading…':'Load older messages'}</button>{/if}
      {#each turns as turn (turn.id)}
        <article class="chat-turn" aria-label="Search conversation turn">
          <div class="user-message"><span>You</span><p>{turn.query||'Find jobs matching my resume'}</p></div>
          <div class="assistant-message"><div class="assistant-label"><Icon name="sparkle" size={15}/><strong>Career Ops</strong><time datetime={turn.created_at}>{new Date(turn.created_at).toLocaleDateString(undefined,{month:'short',day:'numeric'})}</time></div>
            {#if turn.result.jobs.length}<p class="answer">Found {turn.result.jobs.length} job{turn.result.jobs.length===1?'':'s'}. Expand a role to read its description, then choose Interested to save it to your tracker.</p>{:else}<p class="answer">{turn.result.empty_message||'No new roles met this search in the checked company sources.'}</p>{/if}
            {#if turn.result.search_stats}<p class="search-coverage">Checked {turn.result.search_stats.retrieved} postings across {turn.result.search_stats.sources_searched} company sources.{#if turn.result.search_stats.web_queries} Web discovery used {turn.result.search_stats.web_queries} queries and checked {turn.result.search_stats.web_pages_checked} pages.{/if}{#if turn.result.search_stats.already_tracked} Skipped {turn.result.search_stats.already_tracked} tech roles already in your tracker.{/if}</p>{/if}
            {#if turn.result.warnings.length}<details class="source-notices" open={!turn.result.jobs.length||turn.mode==='import'}><summary>Source notices ({turn.result.warnings.length})</summary>{#each turn.result.warnings as warning}<p>{warning}</p>{/each}</details>{/if}
            {#if turn.resume_changed}<div class="notice">Your resume changed since this search. These job descriptions remain available; search again for current fit scores.</div>{/if}
            {#if turn.result.context_info}<p class="search-coverage">{turn.result.context_info.kind==='follow_up'?'Follow-up search':'New search'}{turn.result.context_info.saved_preferences_applied?' · Saved defaults applied (explicit query fields override them)':''}. Effective filters: {turn.result.context_info.effective_filters.join('; ')}.</p>{#if turn.result.context_info.notice}<div class="notice">{turn.result.context_info.notice}</div>{/if}{/if}
            <div class="chat-jobs">{#each turn.result.jobs as job (job.id)}<ChatJobCard {job} turnId={turn.id} oninterested={interested}/>{/each}</div>
            {#if turn.result.external_links?.length}<details class="external-listings"><summary>Other discovered links ({turn.result.external_links.length}) · details unavailable</summary><p>These links have no fit score. Open the original listing to check its details and availability.</p>{#each turn.result.external_links as lead}<div><a href={lead.url} target="_blank" rel="noopener noreferrer">{lead.title}</a><small>{lead.detail}</small></div>{/each}</details>{/if}
            {#if turn.result.location_notice}<p class="search-notes">{turn.result.location_notice} Change the radius in your next query, for example “near Pune, India within 25 km only”.</p>{/if}
            <details class="search-notes"><summary>Search details</summary><p>{turn.result.relaxation_note}</p><p>Resume used: {turn.resume_filename||'No resume'}. Fit scores show content similarity.</p>{#if turn.result.search_stats}<p>{turn.result.search_stats.eligible} new tech roles met your filters before ranking.</p>{/if}<details><summary>Interpreted query</summary><pre>{JSON.stringify(turn.result.query_spec,null,2)}</pre></details></details>
          </div>
        </article>
      {/each}
      {#if loading}<article class="chat-turn"><div class="user-message"><span>You</span><p>{pendingQuery||'Find jobs matching my resume'}</p></div><div class="loading-line searching" role="status"><span class="spinner"></span>{activeRun?.phase==='queued'?'Search queued…':activeRun?.phase==='interpreting'?'Interpreting your search…':activeRun?.phase==='ranking'?'Ranking jobs against your resume…':'Checking public employer sources…'}</div></article>{/if}
    </div>
    <div class="composer-area" id="resume">
      {#if error}<div class="error" role="alert">{error}</div>{/if}
      {#if activeRun&&loading}<button class="cancel-search" disabled={activeRun.status==='cancelling'} onclick={cancelSearch}>{activeRun.status==='cancelling'?'Cancelling…':'Cancel search'}</button>{/if}
      {#if activeRun&&['failed','interrupted'].includes(activeRun.status)&&!loading}<div class="notice"><span>{activeRun.error||'The search did not complete. Your previous context is preserved.'}</span><button onclick={retrySearch}>Retry search</button></div>{/if}
      {#if activeRun?.status==='needs_input'}<p class="discovery-hint">{activeRun.error} Update your message below to clarify the search. Your previous context is preserved.</p>{/if}
      {#if activeRun?.status==='cancelled'}<p class="discovery-hint">Search cancelled. Your previous successful search context is preserved.</p>{/if}
      {#if bootstrap&&!bootstrap.model_configured}<div class="notice"><span><a href="/settings">Check service status</a> to see why resume uploads and specific queries are unavailable. An existing resume can still be searched with an empty message.</span></div>{/if}
      {#if showResume&&profile&&!uploading}<div class="resume-review"><ResumeSummary {profile}/></div>{/if}
      <div class="resume-toolbar">{#if profile}<div class="uploaded-resume"><button class="resume-chip" aria-expanded={showResume} disabled={uploading||removing} onclick={()=>showResume=!showResume}><Icon name="file" size={13}/><span>{profile.filename}</span><span class="fact-count">{profile.structured_facts.facts.length} statements</span></button><button class="remove-resume" aria-label="Remove resume" title="Remove resume" disabled={loading||uploading||removing} onclick={removeResume}>{#if removing}<span class="spinner"></span>{:else}×{/if}</button></div>{:else}<button class="attach-button" disabled={!ready||!bootstrap?.model_configured||uploading||removing||loading} onclick={()=>resumeInput.click()}><Icon name="upload" size={14}/>{uploading?'Reading resume…':'Add resume (.docx)'}</button><span class="resume-hint">DOCX only for now · Up to 5 MB</span>{/if}</div>
      <input class="sr-only" type="file" bind:this={resumeInput} accept=".docx" aria-label="Upload resume" disabled={!bootstrap?.model_configured||uploading||removing||loading} onchange={(e)=>upload(e.currentTarget.files?.[0])}/>
      {#if uploading}<div class="loading-line" role="status"><span class="spinner"></span>Reading your resume…</div>{/if}
      {#if bootstrap&&!bootstrap.web_search_configured}<p class="discovery-hint">Web discovery is unavailable. Configured employer boards are still searched.</p>{/if}
      <form class="composer" onsubmit={(e)=>{e.preventDefault();search();}}><label class="sr-only" for="job-query">Describe the jobs you want</label><textarea id="job-query" bind:value={query} onkeydown={submitOnEnter} disabled={!ready||loading||uploading||removing||!profile||!bootstrap?.model_configured} placeholder={profile?'Ask for a role, location or posting date — or leave empty for resume matches…':'Add your resume to start finding jobs…'} rows="2" maxlength="2000"></textarea><button class="primary" type="submit" disabled={!ready||!profile||loading||uploading||removing||(!!query.trim()&&!bootstrap?.model_configured)}>{#if loading}<span class="spinner"></span>Searching…{:else}<Icon name="arrow" size={15}/>Find jobs{/if}</button></form>
      <p class="privacy-note">Resume statements are processed through OpenRouter for extraction; embeddings run locally. Web discovery receives search terms, not your raw resume. Model calls request providers that deny training data collection.</p>
      <p class="composer-hints">{profile?'Every search ranks jobs against your resume. Enter to search · Shift+Enter for a new line.':'Add a resume, then click Find jobs. Nothing enters your tracker until you choose Interested.'}</p>
      {#if !turns.length&&bootstrap?.model_configured}<div class="examples">{#each examples as example}<button disabled={!profile||loading||uploading||removing} onclick={()=>query=example}>{example}</button>{/each}</div>{/if}
    </div>
  </div>
</div>

<style>
  .older-messages{display:block;margin:0 auto 20px;font-size:11px}
  .cancel-search{margin-bottom:12px;font-size:11px}
  .discovery-hint,.privacy-note{font-size:10px;color:#73839a;margin:8px 0;line-height:1.6}.external-listings{margin:15px 0;font-size:11px}.external-listings p{margin:10px 0;color:#73839a}.external-listings>div{padding:10px 0;border-bottom:1px solid var(--line)}.external-listings small{display:block;margin-top:5px;color:#73839a}
  .search-coverage{font-size:10px;color:#73839a;margin:0 0 13px;line-height:1.7}.source-notices{margin:12px 0;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:#f4f7ff}.source-notices summary{font-size:11px}.source-notices p{font-size:10px;margin-top:8px;color:#657994}
  .uploaded-resume{display:flex;align-items:center;gap:6px;min-width:0;max-width:min(100%,560px)}.uploaded-resume .resume-chip{flex:1;min-width:0;max-width:none}.remove-resume{flex-shrink:0;width:26px;height:26px;padding:0;border:1px solid var(--line);border-radius:50%;font-size:18px;line-height:1;color:#8090a8}.remove-resume:hover:not(:disabled){background:#fff4f4;color:#a7434a;border-color:#e8bfc3}
  .chat-workspace{height:calc(100dvh - 150px);min-height:580px;display:flex;flex-direction:column;max-width:1050px;margin:auto}.chat-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;margin-bottom:20px;flex-shrink:0}.chat-heading .eyebrow{font-size:10px;margin-bottom:8px}.chat-heading h1{font-size:26px;margin-bottom:6px}.chat-heading p{font-size:12px;color:#66778f}.chat-heading>.badge{margin-top:7px;white-space:nowrap}.chat-shell{display:flex;flex-direction:column;flex:1;min-height:0;border:1px solid var(--line);border-radius:16px;background:#fff;overflow:hidden;box-shadow:0 6px 24px #23375b04}.chat-scroll{flex:1;min-height:0;overflow-y:auto;overscroll-behavior:contain;padding:26px 28px;background:#fbfcff;scroll-behavior:smooth}.chat-scroll:focus-visible{outline:2px solid #93b7ff;outline-offset:-2px}.chat-welcome{text-align:center;max-width:490px;margin:38px auto}.welcome-icon{background:#edf3ff;color:var(--blue);width:58px;height:58px;border-radius:16px;display:grid;place-items:center;margin:0 auto 18px}.chat-welcome h2{font-size:20px;margin-bottom:12px}.chat-welcome p{font-size:12px;color:#687991;line-height:1.8}.welcome-steps{display:flex;justify-content:center;gap:14px;flex-wrap:wrap;margin:22px 0;color:#526c96;font-size:11px}.chat-welcome .source-note{font-size:10px}.chat-turn+.chat-turn{margin-top:28px;padding-top:24px;border-top:1px solid #edf0f6}.user-message{margin-left:auto;max-width:85%;width:fit-content;border-radius:13px 13px 3px 13px;background:#edf3ff;padding:12px 16px;overflow-wrap:anywhere}.user-message>span{display:block;font-size:9px;font-weight:700;color:#6e88af;margin-bottom:4px}.user-message p{font-size:12px;white-space:pre-wrap;color:#334f7d}.assistant-message{margin-top:20px}.assistant-label{display:flex;align-items:center;gap:7px;color:var(--blue);font-size:11px}.assistant-label time{font-size:9px;margin-left:auto;color:#8796ab}.answer{font-size:12px;color:#61738e;line-height:1.8;margin:12px 0 15px}.assistant-message>.notice{margin-bottom:14px;font-size:11px}.chat-jobs{display:grid;gap:10px}.search-notes{margin-top:13px}.search-notes>summary{font-size:10px;color:#7c8ea8}.search-notes p{font-size:10px;margin:9px 0;color:#73839a}.search-notes pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:10px;padding:12px;background:white;border:1px solid var(--line);border-radius:8px}.searching{padding:22px 0}.composer-area{flex-shrink:0;border-top:1px solid var(--line);padding:15px 22px 17px;background:white}.composer-area>.error,.composer-area>.notice{margin-bottom:12px}.resume-toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px}.attach-button{font-size:11px;padding:7px 10px}.resume-chip{font-size:10px;border-color:#dce7fa;background:#f5f8ff;padding:6px 9px;min-width:0;max-width:65%;color:#5c759b;font-weight:500}.resume-chip>span:first-of-type{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.fact-count{white-space:nowrap;color:#899ab1;font-size:9px}.resume-hint{font-size:9px;color:#7a8ba3}.resume-review{border:1px solid var(--line);border-radius:10px;background:#fafcff;padding:14px;margin-bottom:12px;max-height:250px;overflow:auto}.composer{border:1px solid #d8e2f2;border-radius:11px;padding:10px 11px;display:flex;gap:12px;align-items:flex-end}.composer:focus-within{border-color:#96b6f2;box-shadow:0 0 0 2px #edf3ff}.composer textarea{flex:1;min-width:0;width:100%;border:0;outline:0;resize:vertical;min-height:55px;max-height:140px;font-size:12px;line-height:1.8;padding:5px;background:white;color:var(--ink)}.composer textarea::placeholder{color:#8393aa}.composer button{font-size:11px;padding:10px 13px;white-space:nowrap}.composer-hints{margin-top:8px;font-size:9px;color:#7a8ba3;line-height:1.7}.examples{display:flex;gap:7px;flex-wrap:wrap;margin-top:12px}.examples button{font-size:9px;color:#6880a3;font-weight:400;padding:5px 8px;border-color:#e6edf9}@media(min-width:1600px){.chat-workspace{height:calc(100dvh - 165px)}}@media(max-width:700px){.chat-workspace{height:calc(100dvh - 220px);min-height:540px}.chat-heading{margin-bottom:16px;gap:10px}.chat-heading h1{font-size:23px}.chat-heading .eyebrow{font-size:8px}.chat-heading p{font-size:11px}.chat-heading>.badge{font-size:8px}.chat-scroll{padding:18px 14px}.chat-welcome{margin:20px auto}.chat-welcome h2{font-size:17px}.composer-area{padding:12px}.composer{gap:6px;padding:8px}.composer button{padding:9px;font-size:10px}.composer textarea{font-size:11px}.resume-chip{max-width:100%}.fact-count{display:none}.welcome-steps{font-size:10px;gap:8px}.examples{display:none}.user-message{max-width:95%}}
</style>
