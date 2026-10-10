<script lang="ts">
  import { onMount, type Snippet } from 'svelte';
  import { page } from '$app/state';
  import '../app.css';
  import Icon from '#lib/Icon.svelte';
  import { api } from '#lib/api';
  import type { Bootstrap } from '#lib/types';
  let { children }: { children: Snippet } = $props();
  let bootstrap = $state<Bootstrap | null>(null);
  let offline = $state(false);
  const nav = [{href:'/', label:'Search jobs', icon:'search'}, {href:'/tracker', label:'Job tracker', icon:'board'}, {href:'/resume', label:'Resume & facts', icon:'file'}, {href:'/settings', label:'Settings', icon:'settings'}];
  async function reload() { try { bootstrap = await api<Bootstrap>('/bootstrap'); offline = false; } catch { offline = true; } }
  onMount(() => { reload(); window.addEventListener('workspace-update', reload); return () => window.removeEventListener('workspace-update', reload); });
</script>
<svelte:head><title>Career Ops — Your job search workspace</title><meta name="description" content="Find technology roles, tailor grounded application materials, and track your job search."/></svelte:head>
<div class="workspace">
  <aside class="sidebar">
    <a class="brand" href="/" aria-label="Career Ops home"><span class="brand-mark"><Icon name="briefcase" size={21}/></span><span>Career<span class="brand-light">Ops</span><small>YOUR NEXT CHAPTER</small></span></a>
    <p class="nav-caption">WORKSPACE</p>
    <nav aria-label="Main navigation">{#each nav as item}<a class:active={page.url.pathname === item.href} href={item.href}><Icon name={item.icon}/><span>{item.label}</span>{#if item.href === '/tracker' && bootstrap}<span class="nav-count">{Object.values(bootstrap.counts).reduce((a,b) => a+b,0)}</span>{/if}</a>{/each}</nav>
    <div class="sidebar-bottom">
      <div class="workspace-note"><span class="tiny-dot"></span><strong>Your local workspace</strong><p>Thoughtful applications.<br/>Every submission is your decision.</p></div>
      <a class="profile-link" href="/settings"><span class="avatar">Y</span><span><strong>Your workspace</strong><small>Free models only</small></span><Icon name="settings" size={16}/></a>
    </div>
  </aside>
  <div class="main-wrap">
    <header class="topbar"><span>Career workspace <span class="topbar-separator">/</span> <strong>{nav.find(n => n.href === page.url.pathname)?.label || 'Workspace'}</strong></span><span class="connection"><span class:offline class="tiny-dot"></span>{offline ? 'Backend offline' : bootstrap ? 'Local workspace' : 'Connecting…'}</span></header>
    {#if offline}<div class="offline-banner" role="alert">The backend is offline. Start FastAPI on port 8000 to connect your workspace.</div>{/if}
    <main>{@render children()}</main>
  </div>
</div>
