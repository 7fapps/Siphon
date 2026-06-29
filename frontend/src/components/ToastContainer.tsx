import React from 'react';
import type { Toast } from '../hooks/useToast';

interface ToastContainerProps {
  toasts: Toast[];
  onRemove: (id: string) => void;
}

const ToastIcon = ({ type }: { type: Toast['type'] }) => {
  switch (type) {
    case 'success':
      return <span className="text-emerald-400 text-lg">✓</span>;
    case 'error':
      return <span className="text-red-400 text-lg">✕</span>;
    case 'warning':
      return <span className="text-amber-400 text-lg">⚠</span>;
    default:
      return <span className="text-siphon-400 text-lg">ℹ</span>;
  }
};

const ToastItem: React.FC<{ toast: Toast; onRemove: (id: string) => void }> = ({ toast, onRemove }) => {
  const bgMap = {
    success: 'bg-emerald-950/90 border-emerald-800',
    error: 'bg-red-950/90 border-red-800',
    warning: 'bg-amber-950/90 border-amber-800',
    info: 'bg-siphon-950/90 border-siphon-800',
  };

  return (
    <div
      className={`flex items-center gap-3 rounded-xl border px-4 py-3 shadow-lg backdrop-blur-sm animate-slide-up ${bgMap[toast.type]}`}
      role="alert"
    >
      <ToastIcon type={toast.type} />
      <p className="text-sm text-white flex-1">{toast.message}</p>
      <button
        onClick={() => onRemove(toast.id)}
        className="text-slate-400 hover:text-white text-xs"
        aria-label="Dismiss"
      >
        ✕
      </button>
    </div>
  );
};

const ToastContainer: React.FC<ToastContainerProps> = ({ toasts, onRemove }) => {
  if (toasts.length === 0) return null;
  return (
    <div className="fixed top-4 left-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map((t) => (
        <div key={t.id} className="pointer-events-auto max-w-sm mx-auto w-full">
          <ToastItem toast={t} onRemove={onRemove} />
        </div>
      ))}
    </div>
  );
};

export default ToastContainer;
