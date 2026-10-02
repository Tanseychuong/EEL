import React, { createContext, useContext, useEffect, useState } from 'react';

const STORAGE_KEY = 'eel-theme'; // stores an explicit 'light'/'dark' override; absent = follow system

const ThemeContext = createContext(null);

const getSystemTheme = () =>
  window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';

const getInitialTheme = () => {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === 'light' || stored === 'dark' ? stored : getSystemTheme();
};

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(getInitialTheme);
  const [followSystem, setFollowSystem] = useState(() => !localStorage.getItem(STORAGE_KEY));

  // Apply to <html data-theme="..."> so CSS variables switch instantly.
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // While no manual override is set, stay in sync if the OS theme changes
  // (e.g. the system switches to dark mode at sunset).
  useEffect(() => {
    if (!followSystem) return undefined;
    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (e) => setTheme(e.matches ? 'dark' : 'light');
    mql.addEventListener('change', handleChange);
    return () => mql.removeEventListener('change', handleChange);
  }, [followSystem]);

  const toggleTheme = () => {
    setTheme((prev) => {
      const next = prev === 'dark' ? 'light' : 'dark';
      localStorage.setItem(STORAGE_KEY, next);
      setFollowSystem(false);
      return next;
    });
  };

  const resetToSystem = () => {
    localStorage.removeItem(STORAGE_KEY);
    setFollowSystem(true);
    setTheme(getSystemTheme());
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, followSystem, resetToSystem }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within a ThemeProvider');
  return ctx;
};
