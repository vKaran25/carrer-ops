import type { Handle } from '@sveltejs/kit/hooks';
export const handle: Handle = async ({ event, resolve }) => {
  if (event.url.pathname.startsWith('/api/') || event.url.pathname === '/health') {
    const target = new URL(event.url.pathname + event.url.search, process.env.BACKEND_URL || 'http://127.0.0.1:8000');
    try { return await fetch(new Request(target, event.request)); }
    catch { return Response.json({ detail: 'Backend is offline. Start the FastAPI server on port 8000.' }, { status: 503 }); }
  }
  return resolve(event);
};
