import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { RequireAuth } from './auth/RequireAuth';
import { Shell } from './components/Shell';
import { LoginPage } from './pages/LoginPage';
import { VitalsPage } from './pages/VitalsPage';
import { TeleopPage } from './pages/TeleopPage';
import { DoorPage } from './pages/DoorPage';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <RequireAuth>
                <Shell />
              </RequireAuth>
            }
          >
            <Route path="/" element={<VitalsPage />} />
            <Route path="/teleop" element={<TeleopPage />} />
            <Route path="/door" element={<DoorPage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
