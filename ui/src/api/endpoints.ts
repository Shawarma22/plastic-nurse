import { api, API_BASE_URL } from './client';
import type {
  TokenResponse,
  UserMeResponse,
  MotorState,
  DoorStatus,
  SessionResponse,
  VitalResponse,
  EventResponse,
  JobResponse,
} from '../types/api';

// auth.py's /login uses OAuth2PasswordRequestForm, which expects
// application/x-www-form-urlencoded, not JSON — handled separately here.
export async function login(username: string, password: string): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username, password }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail ?? 'Login failed');
  }
  return res.json();
}

export const getMe = () => api.get<UserMeResponse>('/api/v1/auth/me');

// --- motors ---
export const motors = {
  forward: (speed = 1.0) => api.post<MotorState>('/api/v1/motors/forward', { speed }),
  backward: (speed = 1.0) => api.post<MotorState>('/api/v1/motors/backward', { speed }),
  turnLeft: (speed = 1.0) => api.post<MotorState>('/api/v1/motors/turn_left', { speed }),
  turnRight: (speed = 1.0) => api.post<MotorState>('/api/v1/motors/turn_right', { speed }),
  command: (leftSpeed: number, rightSpeed: number) =>
    api.post<MotorState>('/api/v1/motors/command', { left_speed: leftSpeed, right_speed: rightSpeed }),
  stop: () => api.post<MotorState>('/api/v1/motors/stop'),
  status: () => api.get<MotorState>('/api/v1/motors/status'),
};

// --- door ---
export const door = {
  open: () => api.post<DoorStatus>('/api/v1/door/open'),
  close: () => api.post<DoorStatus>('/api/v1/door/close'),
  stop: () => api.post<DoorStatus>('/api/v1/door/stop'),
  status: () => api.get<DoorStatus>('/api/v1/door/status'),
};

// --- vitals ---
export const vitals = {
  createSession: (patientRef: string, notes?: string) =>
    api.post<SessionResponse>('/api/v1/vitals/sessions', { patient_ref: patientRef, notes }),
  listSessions: () => api.get<SessionResponse[]>('/api/v1/vitals/sessions'),
  recordVitals: (sessionUid: string, data: Partial<VitalResponse>) =>
    api.post<VitalResponse>('/api/v1/vitals/records', { session_uid: sessionUid, ...data }),
  getVitals: (sessionUid: string) => api.get<VitalResponse[]>(`/api/v1/vitals/records/${sessionUid}`),
  recordEvent: (eventType: string, sessionUid?: string, payload?: string) =>
    api.post<EventResponse>('/api/v1/vitals/events', { event_type: eventType, session_uid: sessionUid, payload }),
  getEvents: (sessionUid: string) => api.get<EventResponse[]>(`/api/v1/vitals/events/${sessionUid}`),
};

// --- jobs ---
export const jobs = {
  submit: (jobType: string, payload?: Record<string, unknown>) =>
    api.post<JobResponse>('/api/v1/jobs/submit', { job_type: jobType, payload }),
  status: (jobId: string) => api.get<JobResponse>(`/api/v1/jobs/${jobId}`),
};

// --- camera ---
// The stream/snapshot endpoints accept the token as a query param as a
// fallback for <img>/<video> tags, which can't set an Authorization header.
export function cameraStreamUrl(token: string | null): string {
  return `${API_BASE_URL}/api/v1/camera/stream${token ? `?token=${encodeURIComponent(token)}` : ''}`;
}
export function cameraSnapshotUrl(token: string | null): string {
  return `${API_BASE_URL}/api/v1/camera/snapshot${token ? `?token=${encodeURIComponent(token)}` : ''}`;
}
