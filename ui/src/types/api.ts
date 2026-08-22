// Types mirror the Pydantic response models in core/app/routers/*.py

export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: string;
  username: string;
}

export interface UserMeResponse {
  username: string;
  role: string;
}

export interface MotorState {
  left_speed: number;
  right_speed: number;
  [key: string]: unknown;
}

export interface DoorStatus {
  state: 'closed' | 'opening' | 'open' | 'closing' | 'error';
  [key: string]: unknown;
}

export interface SessionResponse {
  id: number;
  session_uid: string;
  patient_ref: string;
  status: string;
  notes: string | null;
}

export interface VitalResponse {
  id: number;
  session_uid: string;
  heart_rate: number | null;
  spo2: number | null;
  confidence: number | null;
  is_calibrated: boolean;
}

export interface EventResponse {
  id: number;
  session_uid: string | null;
  event_type: string;
  payload: string | null;
}

export interface JobResponse {
  job_id: string;
  status: string;
  [key: string]: unknown;
}

// Live payloads pushed over /ws/telemetry and /ws/state.
// Shapes aren't pinned down server-side (broadcast_* takes a raw dict),
// so keep these loose and let consumers narrow by field.
export type TelemetryMessage = Record<string, unknown>;
export type StateMessage = Record<string, unknown>;
