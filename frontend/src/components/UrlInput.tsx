import React, { useState, useCallback } from 'react';

interface UrlInputProps {
  onScan: (url: string) => void;
  isLoading: boolean;
}

const UrlInput: React.FC<UrlInputProps> = ({ onScan, isLoading }) => {
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const trimmed = url.trim();
    if (!trimmed) {
      setError('Please enter a URL');
      return;
    }
    if (!/^https?:\/\//i.test(trimmed)) {
      setError('URL must start with http:// or https://');
      return;
    }
    onScan(trimmed);
  }, [url, onScan]);

  return (
    <div className="animate-slide-up w-full">
      <div className="mb-6 text-center">
        {/* Logo */}
        <div className="flex justify-center mb-4">
          <div className="relative">
            <img
              src="/logo.png"
              alt="Siphon"
              className="h-20 w-20 object-contain drop-shadow-[0_0_16px_rgba(14,165,233,0.35)]"
              draggable={false}
            />
          </div>
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2">
          Siphon
        </h1>
        <p className="text-sm text-slate-400">
          Paste a video URL to extract and download
        </p>
      </div>

      <form onSubmit={handleSubmit} className="w-full space-y-3">
        <div className="relative">
          <input
            type="url"
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              if (error) setError('');
            }}
            placeholder="https://example.com/video"
            disabled={isLoading}
            autoFocus
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
            spellCheck={false}
            enterKeyHint="go"
            className="w-full rounded-2xl bg-dark-surface border border-dark-border px-4 py-4 text-sm text-white placeholder:text-slate-500 focus:border-siphon-500 focus:outline-none focus:ring-1 focus:ring-siphon-500 transition-colors disabled:opacity-50"
          />
          {url && !isLoading && (
            <button
              type="button"
              onClick={() => { setUrl(''); setError(''); }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white p-1"
              aria-label="Clear URL"
            >
              ✕
            </button>
          )}
        </div>

        {error && (
          <p className="text-xs text-red-400 pl-1">{error}</p>
        )}

        <button
          type="submit"
          disabled={isLoading || !url.trim()}
          className="w-full rounded-2xl bg-siphon-600 hover:bg-siphon-500 active:bg-siphon-700 disabled:bg-slate-700 disabled:text-slate-400 text-white font-medium py-4 text-sm transition-colors flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Scanning…
            </>
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
              </svg>
              Scan
            </>
          )}
        </button>
      </form>

      <div className="mt-8 flex items-center justify-center gap-2 text-xs text-slate-500">
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" />
        Server ready
      </div>
    </div>
  );
};

export default UrlInput;
