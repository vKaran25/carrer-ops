import { createBrowserClient } from '@supabase/ssr';
import type { SupabaseClient } from '@supabase/supabase-js';
export interface AuthConfiguration { enabled: boolean; url: string; publishable_key: string; }
let client: SupabaseClient | null = null;
export function browserAuth(config: AuthConfiguration): SupabaseClient {
  if (!config.enabled) throw new Error('Authentication is not enabled in this workspace.');
  client ??= createBrowserClient(config.url, config.publishable_key);
  return client;
}
