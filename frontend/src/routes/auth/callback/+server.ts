import { redirect, type RequestHandler } from '@sveltejs/kit';
export const GET: RequestHandler = async ({url,locals}) => {
  const code=url.searchParams.get('code');
  if (code&&locals.supabase) {
    const {error}=await locals.supabase.auth.exchangeCodeForSession(code);
    if (!error) redirect(303,'/?signed_in=1');
  }
  redirect(303,'/login?error=callback');
};
