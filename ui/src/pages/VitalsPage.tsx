import { useEffect, useState } from 'react';
import { useWebSocketChannel } from '../hooks/useWebSocketChannel';
import { wsUrl } from '../api/ws';
import { vitals } from '../api/endpoints';
import type { SessionResponse, TelemetryMessage } from '../types/api';

// Core Rule 1 (README): hobby sensors aren't calibrated clinical instruments.
// Show raw readings + ranges only — never a diagnostic classification.
export function VitalsPage() {
  const { lastMessage, connected } = useWebSocketChannel<TelemetryMessage>(wsUrl('/ws/telemetry'));
  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    vitals
      .listSessions()
      .then(setSessions)
      .catch(() => setLoadError('Could not load session history.'));
  }, []);

  const heartRate = readNumber(lastMessage, 'heart_rate');
  const spo2 = readNumber(lastMessage, 'spo2');
  const isCalibrated = Boolean(lastMessage?.is_calibrated);

  return (
    <div className="page">
      <header className="page-header">
        <h2>Vitals Telemetry</h2>
        <span className={`ws-badge ${connected ? 'ws-badge-live' : 'ws-badge-offline'}`}>
          {connected ? 'Live' : 'Reconnecting…'}
        </span>
      </header>

      <p className="disclaimer">
        Readings are indicative records from uncalibrated hobby sensors, not a medical diagnosis.
        Consult a healthcare professional for clinical decisions.
      </p>

      <div className="vitals-grid">
        <div className="vital-tile">
          <span className="vital-label">Heart Rate</span>
          <span className="vital-value">{heartRate !== null ? `${heartRate} bpm` : '—'}</span>
          <span className="vital-sub">{isCalibrated ? 'calibrated' : 'uncalibrated'}</span>
        </div>
        <div className="vital-tile">
          <span className="vital-label">SpO2</span>
          <span className="vital-value">{spo2 !== null ? `${spo2}%` : '—'}</span>
          <span className="vital-sub">{isCalibrated ? 'calibrated' : 'uncalibrated'}</span>
        </div>
      </div>

      <h3>Recent Sessions</h3>
      {loadError && <div className="error-banner">{loadError}</div>}
      <table className="data-table">
        <thead>
          <tr>
            <th>Patient Ref</th>
            <th>Status</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((s) => (
            <tr key={s.session_uid}>
              <td>{s.patient_ref}</td>
              <td>{s.status}</td>
              <td>{s.notes ?? '—'}</td>
            </tr>
          ))}
          {sessions.length === 0 && !loadError && (
            <tr>
              <td colSpan={3}>No sessions recorded yet.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function readNumber(msg: TelemetryMessage | null, key: string): number | null {
  const v = msg?.[key];
  return typeof v === 'number' ? v : null;
}
