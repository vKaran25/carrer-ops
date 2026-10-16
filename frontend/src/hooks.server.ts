import { createServerClient } from '@supabase/ssr';
import { redirect } from '@sveltejs/kit';
import type { Handle } from '@sveltejs/kit/hooks';
import type { AuthConfiguration } from '#lib/auth';

const backend = () => process.env.BACKEND_URL || 'http://127.0.0.1:8000';
export const handle: Handle = async ({ event, resolve }) => {
  if (event.url.pathname.startsWith('/_app/') || event.url.pathname === '/favicon.ico') return resolve(event);
  event.locals.supabase = null;
  event.locals.user = null;
  event.locals.accessToken = null;
  let config: AuthConfiguration;
  try {
    const response = await fetch(new URL('/api/auth/config', backend()), {signal:AbortSignal.timeout(5000)});
    if (!response.ok) throw new Error('Unavailable');
    config = await response.json();
  } catch {
    return new Response('Career Ops could not reach its backend. Please try again shortly.', {status:503});
  }
  event.locals.authEnabled = config.enabled;
  if (config.enabled) {
    event.locals.supabase = createServerClient(config.url, config.publishable_key, {
      cookies: {
        getAll: () => event.cookies.getAll(),
        setAll: (cookies) => { for (const {name,value,options} of cookies) event.cookies.set(name,value,{...options,path:'/',secure:event.url.protocol==='https:',sameSite:'lax'}); }
      }
    });
    const {data:{user},error} = await event.locals.supabase.auth.getUser();
    if (!error && user) {
      event.locals.user = user;
      // getSession is used only after Auth has independently verified this user.
      const {data:{session}} = await event.locals.supabase.auth.getSession();
      event.locals.accessToken = session?.access_token || null;
    }
  }
  if (event.url.pathname.startsWith('/api/') || event.url.pathname === '/health') {
    const unsafe = !['GET','HEAD','OPTIONS'].includes(event.request.method);
    if (unsafe && (event.request.headers.get('origin') && event.request.headers.get('origin') !== event.url.origin || event.request.headers.get('sec-fetch-site') === 'cross-site')) {
      return Response.json({detail:'Cross-site writes are not allowed.'},{status:403});
    }
    const headers = new Headers(event.request.headers);
    headers.delete('cookie'); headers.delete('authorization'); headers.delete('host');
    if (event.locals.accessToken) headers.set('authorization','Bearer '+event.locals.accessToken);
    const target = new URL(event.url.pathname + event.url.search,backend());
    try {
      const request = new Request(target,event.request);
      const response = await fetch(new Request(request,{headers,redirect:'manual'}));
      const result = new Response(response.body,response);
      result.headers.set('cache-control','private, no-store');
      return result;
    } catch {
      return Response.json({detail:'The backend is unavailable. Please try again shortly.'},{status:503});
    }
  }
  const publicPath = event.url.pathname === '/login' || event.url.pathname.startsWith('/auth/') || event.url.pathname.startsWith('/_app/');
  if (config.enabled && !event.locals.user && !publicPath) redirect(303,'/login');
  const response = await resolve(event,{filterSerializedResponseHeaders:(name)=>name==='content-range'||name==='x-supabase-api-version'});
  response.headers.set('cache-control','private, no-store');
  response.headers.set('x-content-type-options','nosniff');
  response.headers.set('referrer-policy','strict-origin-when-cross-origin');
  return response;
};
