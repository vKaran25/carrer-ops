export async function api<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const response = await fetch('/api' + path, { ...options, headers });
  const value = await response.json();
  if (!response.ok) {
    const detail = typeof value.detail === 'string' ? value.detail : 'This request could not be completed. Check the fields and try again.';
    throw new Error(detail);
  }
  return value as T;
}
export function message(error: unknown): string { return error instanceof Error ? error.message : 'Something went wrong. Please try again.'; }
export function refreshWorkspace() { window.dispatchEvent(new Event('workspace-update')); }
export const statuses = ['found', 'tailored', 'applied', 'interviewing', 'resolved'] as const;
export function titleCase(value: string) { return value.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase()); }
