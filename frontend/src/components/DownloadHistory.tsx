import React from 'react';

interface HistoryEntry {
  id: number;
  url: string;
  title?: string;
  height?: number;
  audio_only: boolean;
  file_size?: number;
  thumbnail?: string;
  duration?: number;
  downloaded_at?: string;
}

interface DownloadHistoryProps {
  entries: HistoryEntry[];
  onClose: () => void;
}

const formatSize = (bytes?: number) => {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const DownloadHistory: React.FC<DownloadHistoryProps> = ({ entries, onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 backdrop-blur-sm animate-fade-in sm:items-center px-4">
      <div className="w-full max-w-sm rounded-2xl bg-dark-surface border border-dark-border p-5 animate-slide-up max-h-[70vh] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Download History</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-lg">✕</button>
        </div>

        {entries.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-8">No downloads yet</p>
        ) : (
          <div className="overflow-y-auto space-y-3 pr-1">
            {entries.map((entry) => (
              <div key={entry.id} className="rounded-xl bg-dark-bg border border-dark-border p-3">
                <div className="flex items-start gap-3">
                  {entry.thumbnail ? (
                    <img src={entry.thumbnail} alt="" className="h-12 w-12 rounded-lg object-cover shrink-0" />
                  ) : (
                    <div className="h-12 w-12 rounded-lg bg-dark-border flex items-center justify-center shrink-0">
                      <span className="text-xs text-slate-500">{entry.audio_only ? '♪' : '▶'}</span>
                    </div>
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-white truncate">{entry.title || 'Untitled'}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {entry.audio_only ? 'Audio' : `${entry.height || '?'}p`} · {formatSize(entry.file_size)}
                    </p>
                    <p className="text-[10px] text-slate-600 mt-0.5">
                      {entry.downloaded_at ? new Date(entry.downloaded_at).toLocaleDateString() : ''}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        <button
          onClick={onClose}
          className="mt-4 w-full rounded-xl bg-siphon-600 py-2.5 text-sm text-white font-medium hover:bg-siphon-500 transition-colors"
        >
          Close
        </button>
      </div>
    </div>
  );
};

export default DownloadHistory;
