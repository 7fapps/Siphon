import { useCallback } from 'react';

export function useHaptic() {
  const trigger = useCallback((type: 'light' | 'medium' | 'heavy' | 'success' | 'warning' | 'error' = 'light') => {
    if (!('vibrate' in navigator)) return;
    const patterns: Record<string, number | number[]> = {
      light: 10,
      medium: 20,
      heavy: 30,
      success: [10, 50, 10],
      warning: [20, 50, 20],
      error: [50, 100, 50],
    };
    navigator.vibrate(patterns[type] || 10);
  }, []);

  return { trigger };
}
