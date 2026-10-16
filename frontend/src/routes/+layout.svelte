<script lang="ts">
  import { onMount, type Snippet } from 'svelte';
  import { page } from '$app/state';
  import { replaceState } from '$app/navigation';
  import '../app.css';
  import Icon from '#lib/Icon.svelte';
  import { api, ApiError } from '#lib/api';
  import type { Bootstrap } from '#lib/types';
  let { children }: { children: Snippet } = $props();
  let bootstrap = $state<Bootstrap | null>(null);
  let offline = $state(false);
  let accessRequired = $state(false);
  const nav = [{href:'/', label:'Search chat', icon:'search'}, {href:'/tracker', label:'Job tracker', icon:'board'}, {href:'/settings', label:'Settings', icon:'settings'}];
  async function reload() {
    if(page.url.pathname==='/login')return;
    try {
      const next=await api<Bootstrap>('/bootstrap');
      if(bootstrap&&bootstrap.account_subject!==next.account_subject){window.location.reload();return;}
      bootstrap=next;offline=false;accessRequired=false;
    }catch(e){accessRequired=e instanceof ApiError&&[401,403].includes(e.status);offline=!accessRequired;}
  }
  onMount(()=>{
    const params=new URLSearchParams(window.location.search);
    if(params.has('signed_in')){sessionStorage.removeItem('career-ops-search-key');localStorage.setItem('career-ops-auth-event',String(Date.now()));const url=new URL(window.location.href);url.searchParams.delete('signed_in');replaceState(url,page.state);}
    const accountEvent=(event:StorageEvent)=>{if(event.key==='career-ops-auth-event'){sessionStorage.removeItem('career-ops-search-key');window.location.reload();}};
    reload();window.addEventListener('workspace-update',reload);window.addEventListener('focus',reload);window.addEventListener('storage',accountEvent);
    return()=>{window.removeEventListener('workspace-update',reload);window.removeEventListener('focus',reload);window.removeEventListener('storage',accountEvent);};
  });
</script>
<svelte:head><title>Career Ops — Your job search workspace</title><meta name="description" content="Find technology roles matching your resume and track your job search."/></svelte:head>
{#if page.url.pathname==='/login'}<main class="login-main">{@render children()}</main>{:else}
<div class="workspace">
  <aside class="sidebar">
    <a class="brand" href="/" aria-label="Career Ops home"><span class="brand-mark"><Icon name="briefcase" size={21}/></span><span>Career<span class="brand-light">Ops</span><small>YOUR NEXT CHAPTER</small></span></a>
    <p class="nav-caption">WORKSPACE</p>
    <nav aria-label="Main navigation">{#each nav as item}<a class:active={page.url.pathname === item.href} href={item.href}><Icon name={item.icon}/><span>{item.label}</span>{#if item.href === '/tracker' && bootstrap}<span class="nav-count">{Object.values(bootstrap.counts).reduce((a,b) => a+b,0)}</span>{/if}</a>{/each}</nav>
    <div class="sidebar-bottom">
      <div class="workspace-note"><span class="tiny-dot"></span><strong>{bootstrap?.auth_mode==='supabase'?'Your private workspace':'Local development'}</strong><p>Thoughtful applications.<br/>Every submission is your decision.</p></div>
      <a class="profile-link" href="/settings"><span class="avatar">Y</span><span><strong>Your workspace</strong><small>Free models only</small></span><Icon name="settings" size={16}/></a>
    </div>
  </aside>
  <div class="main-wrap">
    <header class="topbar"><span>Career workspace <span class="topbar-separator">/</span> <strong>{nav.find(n => n.href === page.url.pathname)?.label || 'Workspace'}</strong></span><span class="connection"><span class:offline class="tiny-dot"></span>{offline ? 'Service unavailable' : accessRequired ? 'Access required' : bootstrap ? bootstrap.auth_mode==='supabase'?'Account connected':'Local development' : 'Connecting…'}</span></header>
    {#if offline}<div class="offline-banner" role="alert">The service is unavailable. Please try again shortly.</div>{/if}
    {#if accessRequired}<div class="offline-banner" role="alert">Sign-in or an active beta invitation is required. <a href="/login">Sign in or switch account</a>.</div>{/if}
    <main>{@render children()}</main>
  </div>
</div>

{/if}
