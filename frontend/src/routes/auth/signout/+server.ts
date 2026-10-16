import { redirect, type RequestHandler } from '@sveltejs/kit';
export const POST: RequestHandler = async ({locals,request,url}) => {
  if (request.headers.get('origin')!==url.origin) return new Response('Invalid origin',{status:403});
  const result=await locals.supabase?.auth.signOut();
  if(result?.error)return new Response('Sign-out could not finish. Please try again shortly.',{status:503});
  redirect(303,'/login?signed_out=1');
};
