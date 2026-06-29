import { useState, useCallback } from 'react';

interface SiphonSettings {
  autoDownload: boolean;
  defaultHeight: number;
  enableWebSocket: boolean;
  enableHaptic: boolean;
  darkMode: boolean;
  serverUrl: string;
  dismissedInstall: boolean;
}

const defaults: SiphonSettings = {
  autoDownload: false,
  defaultHeight: 720,
  enableWebSocket: true,
  enableHaptic: true,
  darkMode: true,
  serverUrl: '',
  dismissedInstall: false,
};

function loadSettings(): SiphonSettings {
  try {
    const raw = localStorage.getItem('siphon-settings');
    return raw ? { ...defaults, ...JSON.parse(raw) } : defaults;
  } catch {
    return defaults;
  }
}

export function useSettings() {
  const [settings, setSettings] = useState<SiphonSettings>(loadSettings);

  const update = useCallback((patch: Partial<SiphonSettings>) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      localStorage.setItem('siphon-settings', JSON.stringify(next));
      return next;
    });
  }, []);

  const reset = useCallback(() => {
    localStorage.setItem('siphon-settings', JSON.stringify(defaults));
    setSettings(defaults);
  }, []);

  return { settings, update, reset };
}
