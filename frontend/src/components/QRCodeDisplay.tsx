import React, { useState } from 'react';

interface QRCodeDisplayProps {
  jobId: string;
}

const QRCodeDisplay: React.FC<QRCodeDisplayProps> = ({ jobId }) => {
  const [show, setShow] = useState(false);

  if (!show) {
    return (
      <button
        onClick={() => setShow(true)}
        className="w-full rounded-2xl border border-dark-border bg-transparent hover:bg-dark-surface text-slate-300 font-medium py-3.5 text-sm transition-colors flex items-center justify-center gap-2"
      >
        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 4.875a2.625 2.625 0 115.25 0 2.625 2.625 0 01-5.25 0zM12.75 4.875a2.625 2.625 0 115.25 0 2.625 2.625 0 01-5.25 0zM3.75 13.5a2.625 2.625 0 115.25 0 2.625 2.625 0 01-5.25 0zM12.75 13.5a2.625 2.625 0 115.25 0 2.625 2.625 0 01-5.25 0zM21 4.875a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0zM21 13.5a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
        </svg>
        Show QR Code
      </button>
    );
  }

  const downloadUrl = `${window.location.origin}/api/download/${jobId}/file`;
  const qrApiUrl = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(downloadUrl)}`;

  return (
    <div className="rounded-2xl bg-dark-surface border border-dark-border p-4 animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-medium text-white">Scan to Download</p>
        <button onClick={() => setShow(false)} className="text-slate-400 hover:text-white text-sm">✕</button>
      </div>
      <div className="flex justify-center">
        <img
          src={qrApiUrl}
          alt="Download QR Code"
          className="h-40 w-40 rounded-xl"
          draggable={false}
        />
      </div>
      <p className="mt-3 text-xs text-center text-slate-500 break-all">{downloadUrl}</p>
    </div>
  );
};

export default QRCodeDisplay;
