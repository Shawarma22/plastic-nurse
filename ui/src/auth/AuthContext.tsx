import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { getStoredToken, setStoredToken } from '../api/client';
import { getMe, login as loginRequest } from '../api/endpoints';
import type { UserMeResponse } from '../types/api';

interface AuthContextValue {
  token: string | null;
  user: UserMeResponse | null;
  status: 'loading' | 'authenticated' | 'unauthenticated';
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(getStoredToken());
  const [user, setUser] = useState<UserMeResponse | null>(null);
  const [status, setStatus] = useState<'loading' | 'authenticated' | 'unauthenticated'>('loading');

  useEffect(() => {
    if (!token) {
      setStatus('unauthenticated');
      return;
    }
    let cancelled = false;
    getMe()
      .then((me) => {
        if (!cancelled) {
          setUser(me);
          setStatus('authenticated');
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStoredToken(null);
          setToken(null);
          setStatus('unauthenticated');
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  const login = useCallback(async (username: string, password: string) => {
    const res = await loginRequest(username, password);
    setStoredToken(res.access_token);
    setToken(res.access_token);
    setUser({ username: res.username, role: res.role });
    setStatus('authenticated');
  }, []);

  const logout = useCallback(() => {
    setStoredToken(null);
    setToken(null);
    setUser(null);
    setStatus('unauthenticated');
  }, []);

  return (
    <AuthContext.Provider value={{ token, user, status, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
