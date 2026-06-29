import React, { useEffect, useState } from 'react';

interface ProgressTrackerProps {
  status: string;
  progress: number | null;
  message: string | null;
  error: string | null;
  onDownload: () => void;
  onReset: () => void;
}

const ProgressTracker: React.FC<ProgressTrackerProps> = ({
  status,
  progress,
  message,
  error,
  onDownload,
  onReset,
}) => {
  const [dots, setDots] = useState('');

  useEffect(() => {
    if (status !== 'completed' && status !== 'failed') {
      const interval = setInterval(() => {
        setDots((prev) => (prev.length >= 3 ? '' : prev + '.'));
      }, 500);
      return () => clearInterval(interval);
    }
  }, [status]);

  const steps = [
    { key: 'queued', label: 'In Queue', icon: '📥' },
    { key: 'extracting', label: 'Extracting', icon: '🔍' },
    { key: 'assembling', label: 'Assembling', icon: '⚙️' },
    { key: 'completed', label: 'Ready', icon: '✅' },
  ];

  const getStepIndex = (s: string) => {
    const idx = steps.findIndex((step) => step.key === s);
    return idx === -1 ? 0 : idx;
  };

  const currentStep = getStepIndex(status);
  const isFailed = status === 'failed';

  return (
    <div className="animate-slide-up w-full">
      <div className="mb-6 text-center">
        <div className="flex justify-center mb-3">
          <img
            src="/logo-sm.png"
            alt="Siphon"
            className="h-10 w-10 object-contain opacity-80"
            draggable={false}
          />
        </div>
        <h2 className="text-xl font-semibold text-white mb-1">
          {isFailed ? 'Download Failed' : 'Downloading'}
        </h2>
        <p className="text-sm text-slate-400">
          {isFailed
            ? 'Something went wrong. You can try again.'
            : `Sit tight — we're working on it${dots}`}
        </p>
      </div>

      {/* Progress Steps */}
      <div className="mb-8">
        <div className="relative flex justify-between">
          {/* Progress bar */}
          <div className="absolute top-3 left-0 right-0 h-0.5 bg-dark-border -z-10">
            <div
              className="h-full bg-siphon-500 transition-all duration-700 ease-out"
              style={{
                width: isFailed
                  ? '0%'
                  : `${Math.min((currentStep / (steps.length - 1)) * 100, 100)}%`,
              }}
            />
          </div>

          {steps.map((step, idx) => {
            const isActive = idx <= currentStep && !isFailed;
            const isCurrent = idx === currentStep && !isFailed;
            return (
              <div key={step.key} className="flex flex-col items-center gap-2">
                <div
                  className={`flex h-6 w-6 items-center justify-center rounded-full text-xs transition-colors ${
                    isActive
                      ? isCurrent
                        ? 'bg-siphon-500 text-white ring-4 ring-siphon-500/20 animate-pulse'
                        : 'bg-siphon-600 text-white'
                      : 'bg-dark-border text-slate-500'
                  }`}
                >
                  {isActive && !isCurrent ? (
                    <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="3" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  ) : (
                    <span className="text-[10px]">{idx + 1}</span>
                  )}
                </div>
                <span
                  className={`text-[10px] font-medium ${
                    isActive ? 'text-siphon-300' : 'text-slate-500'
                  }`}
                >
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Status Detail */}
      {!isFailed && status !== 'completed' && (
        <div className="mb-6 rounded-2xl bg-dark-surface border border-dark-border p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              {message || status}
            </span>
            <span className="text-xs font-bold text-siphon-400">
              {progress !== null ? `${Math.round(progress)}%` : '…'}
            </span>
          </div>
          <div className="h-2 w-full rounded-full bg-dark-border overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-siphon-600 to-siphon-400 transition-all duration-500 ease-out"
              style={{ width: `${progress ?? 0}%` }}
            />
          </div>
        </div>
      )}

      {/* Error */}
      {isFailed && error && (
        <div className="mb-6 rounded-2xl bg-red-950/40 border border-red-900/50 p-4">
          <p className="text-xs text-red-300 leading-relaxed">{error}</p>
        </div>
      )}

      {/* Actions */}
      <div className="space-y-3">
        {status === 'completed' && (
          <button
            onClick={onDownload}
            className="w-full rounded-2xl bg-siphon-600 hover:bg-siphon-500 active:bg-siphon-700 text-white font-medium py-4 text-sm transition-colors flex items-center justify-center gap-2"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M7.5 12l4.5 4.5m0 0l4.5-4.5m-4.5 4.5V3" />
            </svg>
            Save to Device
          </button>
        )}

        <button
          onClick={onReset}
          className="w-full rounded-2xl border border-dark-border bg-transparent hover:bg-dark-surface text-slate-300 font-medium py-3.5 text-sm transition-colors"
        >
          {status === 'completed' ? 'Download Another' : 'Cancel & Start Over'}
        </button>
      </div>
    </div>
  );
};

export default ProgressTracker;
