import React, { useState } from 'react';

interface BatchInputProps {
  onSubmit: (urls: string[]) => void;
  isLoading: boolean;
  onBack: () => void;
}

const BatchInput: React.FC<BatchInputProps> = ({ onSubmit, isLoading, onBack }) => {
  const [text, setText] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = () => {
    setError('');
    const lines = text
      .split(/\n/)
      .map((l) => l.trim())
      .filter((l) => l.length > 0 && l.startsWith(('http://', 'https://')));
    if (lines.length === 0) {
      setError('No valid URLs found. Each line must start with http:// or https://');
      return;
    }
    if (lines.length > 10) {
      setError('Maximum 10 URLs per batch');
      return;
    }
    onSubmit(lines);
  };

  return (
    <div className="animate-slide-up w-full">
      <div className="mb-4 text-center">
        <div className="flex justify-center mb-3">
          <img src="/logo-sm.png" alt="" className="h-10 w-10 object-contain opacity-80" draggable={false} />
        </div>
        <h2 className="text-xl font-semibold text-white mb-1">Batch Download</h2>
        <p className="text-sm text-slate-400">Paste one URL per line (max 10)</p>
      </div>

      <textarea
        value={text}
        onChange={(e) => { setText(e.target.value); setError(''); }}
        placeholder="https://site1.com/video1&#10;https://site2.com/video2"
        disabled={isLoading}
        rows={5}
        className="w-full rounded-2xl bg-dark-surface border border-dark-border px-4 py-3 text-sm text-white placeholder:text-slate-600 focus:border-siphon-500 focus:outline-none focus:ring-1 focus:ring-siphon-500 resize-none transition-colors disabled:opacity-50"
      />

      {error && <p className="text-xs text-red-400 mt-2 pl-1">{error}</p>}

      <div className="mt-3 space-y-3">
        <button
          onClick={handleSubmit}
          disabled={isLoading || !text.trim()}
          className="w-full rounded-2xl bg-siphon-600 hover:bg-siphon-500 active:bg-siphon-700 disabled:bg-slate-700 disabled:text-slate-400 text-white font-medium py-4 text-sm transition-colors flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Queuing…
            </>
          ) : (
            <>Queue Batch Download</>
          )}
        </button>
        <button
          onClick={onBack}
          disabled={isLoading}
          className="w-full rounded-2xl border border-dark-border bg-transparent hover:bg-dark-surface text-slate-300 font-medium py-3.5 text-sm transition-colors"
        >
          Back
        </button>
      </div>
    </div>
  );
};

export default BatchInput;
