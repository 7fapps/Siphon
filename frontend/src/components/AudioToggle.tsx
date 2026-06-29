import React from 'react';

interface AudioToggleProps {
  enabled: boolean;
  onToggle: () => void;
}

const AudioToggle: React.FC<AudioToggleProps> = ({ enabled, onToggle }) => {
  return (
    <button
      onClick={onToggle}
      className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium transition-colors ${
        enabled
          ? 'bg-siphon-950 border-siphon-600 text-siphon-300'
          : 'bg-dark-surface border-dark-border text-slate-400 hover:text-white'
      }`}
    >
      <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
        {enabled ? (
          <>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.208A2.25 2.25 0 013 15V9c0-.621.504-1.125 1.125-1.125h2.25z" />
          </>
        ) : (
          <>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
          </>
        )}
      </svg>
      {enabled ? 'Audio Only' : 'Video + Audio'}
    </button>
  );
};

export default AudioToggle;
