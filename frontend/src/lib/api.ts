export class ApiError extends Error {
  constructor(message:string,public status:number){super(message);this.name='ApiError';}
}
export async function api<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const response = await fetch('/api' + path, { ...options, headers });
  const value = response.headers.get('content-type')?.includes('application/json') ? await response.json() : null;
  if (!response.ok) {
    if ([401,403].includes(response.status) && typeof window!=='undefined' && window.location.pathname!=='/login') window.location.assign('/login?access=1');
    const detail = typeof value?.detail === 'string' ? value.detail : 'This request could not be completed. The service may be unavailable; try again shortly.';
    throw new ApiError(detail,response.status);
  }
  return value as T;
}
export function message(error: unknown): string { return error instanceof Error ? error.message : 'Something went wrong. Please try again.'; }
export function refreshWorkspace() { window.dispatchEvent(new Event('workspace-update')); }
export const statuses = ['interested', 'applied', 'interviewing', 'resolved'] as const;
export function titleCase(value: string) { return value.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase()); }
