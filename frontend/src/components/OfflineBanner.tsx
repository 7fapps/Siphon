import React from 'react';

const OfflineBanner: React.FC = () => {
  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-amber-900/90 backdrop-blur-sm border-b border-amber-700 px-4 py-2 text-center animate-fade-in">
      <p className="text-xs font-medium text-amber-200 flex items-center justify-center gap-2">
        <span className="inline-block h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
        You're offline. Some features may not work until you reconnect.
      </p>
    </div>
  );
};

export default OfflineBanner;
