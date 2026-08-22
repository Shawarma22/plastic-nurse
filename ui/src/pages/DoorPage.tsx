import { useEffect, useState } from 'react';
import { useWebSocketChannel } from '../hooks/useWebSocketChannel';
import { wsUrl } from '../api/ws';
import { door } from '../api/endpoints';
import type { DoorStatus, StateMessage } from '../types/api';

export function DoorPage() {
  const [status, setStatus] = useState<DoorStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { lastMessage } = useWebSocketChannel<StateMessage>(wsUrl('/ws/state'));

  useEffect(() => {
    door.status().then(setStatus).catch(() => setError('Could not load door status.'));
  }, []);

  // Prefer live state pushes over the door state machine when available.
  const liveState = typeof lastMessage?.door_state === 'string' ? (lastMessage.door_state as string) : null;
  const state = liveState ?? status?.state ?? 'unknown';

  const run = async (action: () => Promise<DoorStatus>) => {
    setError(null);
    try {
      setStatus(await action());
    } catch {
      setError('Door command failed.');
    }
  };

  return (
    <div className="page">
      <header className="page-header">
        <h2>Door Control</h2>
      </header>

      <div className="door-status">
        Current state: <span className={`state-pill state-${state}`}>{state}</span>
      </div>

      <div className="door-controls">
        <button className="btn btn-primary" onClick={() => run(door.open)}>Open</button>
        <button className="btn btn-primary" onClick={() => run(door.close)}>Close</button>
        <button className="btn btn-danger" onClick={() => run(door.stop)}>Stop</button>
      </div>

      {error && <div className="error-banner">{error}</div>}
    </div>
  );
}
