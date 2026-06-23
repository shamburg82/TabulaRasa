import { createContext, useContext, useState, useEffect } from 'react';
import { getCurrentUser } from '../api/user.js';

const UserContext = createContext({ username: 'unknown', initials: '?', loading: true });

function initialsOf(name) {
  if (!name) return '?';
  const parts = String(name).trim().split(/[\s._-]+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function UserProvider({ children }) {
  const [state, setState] = useState({ username: 'unknown', initials: '?', loading: true });
  useEffect(() => {
    getCurrentUser().then((u) =>
      setState({
        username: u.username || 'unknown',
        initials: initialsOf(u.username),
        source: u.source,
        loading: false,
      })
    );
  }, []);
  return <UserContext.Provider value={state}>{children}</UserContext.Provider>;
}

export function useCurrentUser() {
  return useContext(UserContext);
}
