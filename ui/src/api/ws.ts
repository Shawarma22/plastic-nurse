import { API_BASE_URL } from './client';

export function wsUrl(path: '/ws/state' | '/ws/telemetry'): string {
  const httpUrl = new URL(path, API_BASE_URL);
  httpUrl.protocol = httpUrl.protocol === 'https:' ? 'wss:' : 'ws:';
  return httpUrl.toString();
}
