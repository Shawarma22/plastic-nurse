import { useState } from 'react';
import { motors, cameraStreamUrl } from '../api/endpoints';
import { getStoredToken } from '../api/client';
import type { MotorState } from '../types/api';

// Touch targets below are >=64px (README/UI-rule minimum is 48x48px on the
// kiosk touchscreen) since directional controls benefit from extra margin.
export function TeleopPage() {
  const [status, setStatus] = useState<MotorState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const streamUrl = cameraStreamUrl(getStoredToken());

  const send = async (action: () => Promise<MotorState>) => {
    setError(null);
    try {
      const res = await action();
      setStatus(res);
    } catch {
      setError('Motor command failed.');
    }
  };

  return (
    <div className="page">
      <header className="page-header">
        <h2>Camera &amp; Teleoperation</h2>
      </header>

      <div className="teleop-layout">
        <div className="camera-frame">
          {/* MJPEG stream served via multipart/x-mixed-replace; a plain <img> renders it. */}
          <img src={streamUrl} alt="Live camera feed" className="camera-feed" />
        </div>

        <div className="dpad">
          <button className="btn dpad-btn dpad-up" onTouchStart={() => send(() => motors.forward())} onClick={() => send(() => motors.forward())}>▲</button>
          <button className="btn dpad-btn dpad-left" onTouchStart={() => send(() => motors.turnLeft())} onClick={() => send(() => motors.turnLeft())}>◀</button>
          <button className="btn dpad-btn dpad-stop" onTouchStart={() => send(() => motors.stop())} onClick={() => send(() => motors.stop())}>■</button>
          <button className="btn dpad-btn dpad-right" onTouchStart={() => send(() => motors.turnRight())} onClick={() => send(() => motors.turnRight())}>▶</button>
          <button className="btn dpad-btn dpad-down" onTouchStart={() => send(() => motors.backward())} onClick={() => send(() => motors.backward())}>▼</button>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}
      {status && (
        <p className="status-line">
          left: {status.left_speed ?? '—'} · right: {status.right_speed ?? '—'}
        </p>
      )}
      <p className="disclaimer">
        A watchdog auto-stops the motors if no command is received; buttons re-issue on every press.
      </p>
    </div>
  );
}
