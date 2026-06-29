import { useState, useCallback } from 'react';

export interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
  duration?: number;
}

let toastId = 0;

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const add = useCallback((message: string, type: Toast['type'] = 'info', duration = 4000) => {
    const id = `toast-${++toastId}`;
    const t = { id, message, type, duration };
    setToasts((prev) => [...prev, t]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((x) => x.id !== id));
    }, duration);
  }, []);

  const remove = useCallback((id: string) => {
    setToasts((prev) => prev.filter((x) => x.id !== id));
  }, []);

  const success = useCallback((msg: string, duration?: number) => add(msg, 'success', duration), [add]);
  const error = useCallback((msg: string, duration?: number) => add(msg, 'error', duration), [add]);
  const info = useCallback((msg: string, duration?: number) => add(msg, 'info', duration), [add]);
  const warning = useCallback((msg: string, duration?: number) => add(msg, 'warning', duration), [add]);

  return { toasts, add, remove, success, error, info, warning };
}
