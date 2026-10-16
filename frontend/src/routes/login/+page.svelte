<script lang="ts">
  import { onMount } from 'svelte';
  import { api, message } from '#lib/api';
  import { browserAuth, type AuthConfiguration } from '#lib/auth';
  let config: AuthConfiguration | null = null;
  let email = ''; let busy = false; let error = ''; let sent = false;
  onMount(async()=>{try{
    const params=new URLSearchParams(window.location.search);
    if(params.has('signed_out')||params.has('deleted'))localStorage.setItem('career-ops-auth-event',String(Date.now()));
    config=await api<AuthConfiguration>('/auth/config');
    if(params.has('error'))error='Sign-in could not finish. Open a new sign-in link in this browser or try Google again.';
    if(params.has('access'))error='An active beta invitation and verified sign-in are required. You can switch accounts below.';
  }catch(e){error=message(e);}});
  async function signIn(provider: 'google' | 'email') {
    if (!config?.enabled || busy) return;
    busy=true;error='';sent=false;
    try {
      const supabase=browserAuth(config);
      const callback=window.location.origin+'/auth/callback';
      const result=provider==='google'
        ? await supabase.auth.signInWithOAuth({provider:'google',options:{redirectTo:callback}})
        : await supabase.auth.signInWithOtp({email:email.trim(),options:{emailRedirectTo:callback,shouldCreateUser:true}});
      if (result.error) throw result.error;
      if (provider==='email') sent=true;
    } catch(e){error=message(e);} finally{busy=false;}
  }
</script>
<svelte:head><title>Sign in — Career Ops</title></svelte:head>
<section class="login panel"><p class="eyebrow">CAREER OPS · INVITED BETA</p><h1>Your job search workspace</h1><p>Sign in with the verified email invited by the operator.</p>
  {#if error}<div class="error" role="alert">{error}</div>{/if}
  {#if sent}<p class="notice" role="status">Check your email for a sign-in link. Open it in this browser so the login can finish.</p>{/if}
  {#if config&&!config.enabled}<p class="notice">This workspace is running in local development mode.</p><a href="/">Open local workspace</a>{:else}
    <button class="primary" disabled={busy||!config} onclick={()=>signIn('google')}>Continue with Google</button>
    <form onsubmit={(e)=>{e.preventDefault();signIn('email');}}><label class="field">Email<input class="input" type="email" autocomplete="email" required maxlength="320" bind:value={email}/></label><button disabled={busy||!config}>{busy?'Connecting…':'Email me a sign-in link'}</button></form>
    <form method="POST" action="/auth/signout"><button>Use a different account</button></form>
  {/if}
  <p class="privacy">Your workspace stores your resume statements, searches and selected jobs. OpenRouter processes resume/query text; Tavily receives search terms; embeddings run locally. We request model providers that deny training data collection. You can delete your account and active workspace data in Settings. No application backup is retained.</p>
</section>
<style>.login{max-width:480px;margin:40px auto;padding:30px;display:grid;gap:18px}.login h1{font-size:25px;line-height:1.4}.login p{font-size:12px;line-height:1.8;color:#657994}.login form{display:grid;gap:14px}.login .privacy{font-size:10px;border-top:1px solid var(--line);padding-top:18px}</style>
