import React, { useState, useCallback, useRef, useEffect } from 'react';
import UrlInput from './components/UrlInput';
import ResolutionSelector from './components/ResolutionSelector';
import ProgressTracker from './components/ProgressTracker';
import BatchInput from './components/BatchInput';
import AudioToggle from './components/AudioToggle';
import ToastContainer from './components/ToastContainer';
import OfflineBanner from './components/OfflineBanner';
import SettingsPanel from './components/SettingsPanel';
import DownloadHistory from './components/DownloadHistory';
import QRCodeDisplay from './components/QRCodeDisplay';
import ErrorBoundary from './components/ErrorBoundary';
import { useWebSocket } from './hooks/useWebSocket';
import { useToast } from './hooks/useToast';
import { useOffline } from './hooks/useOffline';
import { useKeyboard } from './hooks/useKeyboard';
import { useHaptic } from './hooks/useHaptic';
import { useSettings } from './hooks/useSettings';
import {
  probeUrl, probeAudio, startDownload, startAudioDownload, startBatchDownload,
  getJobStatus, triggerDownload, fetchHistory, shareDownload, copyToClipboard,
  type ProbeResponse, type JobStatusResponse, type HistoryEntry,
} from './hooks/useApi';

type Step = 'input' | 'select' | 'progress' | 'batch';

// ── PWA Install Prompt Hook ──
interface InstallState {
  canInstall: boolean;
  isIos: boolean;
  isStandalone: boolean;
  promptInstall: () => void;
  dismiss: () => void;
}

function useInstallPrompt(): InstallState {
  const [deferred, setDeferred] = useState<any>(null);
  const [dismissed, setDismissed] = useState(() => {
    try { return localStorage.getItem('siphon-install-dismissed') === '1'; } catch { return false; }
  });
  const [isStandalone, setIsStandalone] = useState(false);
  const [isIos, setIsIos] = useState(false);

  useEffect(() => {
    const s = window.matchMedia('(display-mode: standalone)').matches || !!(window.navigator as any).standalone;
    setIsStandalone(s);
    setIsIos(/iPad|iPhone|iPod/.test(navigator.userAgent));
    const h = (e: Event) => { e.preventDefault(); setDeferred(e); };
    window.addEventListener('beforeinstallprompt', h);
    return () => window.removeEventListener('beforeinstallprompt', h);
  }, []);

  const promptInstall = useCallback(() => {
    if (deferred) { deferred.prompt(); deferred.userChoice.then(() => setDeferred(null)); }
  }, [deferred]);

  const dismiss = useCallback(() => {
    setDismissed(true);
    try { localStorage.setItem('siphon-install-dismissed', '1'); } catch {}
  }, []);

  return { canInstall: !!deferred && !isStandalone && !dismissed, isIos: isIos && !isStandalone && !dismissed, isStandalone, promptInstall, dismiss };
}

const App: React.FC = () => {
  const [step, setStep] = useState<Step>('input');
  const [url, setUrl] = useState('');
  const [probeResult, setProbeResult] = useState<ProbeResponse | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [audioOnly, setAudioOnly] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const toast = useToast();
  const isOffline = useOffline();
  const haptic = useHaptic();
  const { settings } = useSettings();
  const install = useInstallPrompt();
  const { lastMessage: wsMessage } = useWebSocket(jobStatus?.job_id || null);

  const clearPoll = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  }, []);

  useEffect(() => () => clearPoll(), [clearPoll]);

  // WebSocket fallback: update job status from WebSocket
  useEffect(() => {
    if (wsMessage && wsMessage.job_id === jobStatus?.job_id) {
      setJobStatus((prev) => prev ? { ...prev, status: wsMessage.status, progress: wsMessage.progress, message: wsMessage.message, error: wsMessage.error } : prev);
      if (wsMessage.status === 'completed') {
        clearPoll();
        toast.success('Download complete!');
        haptic.trigger('success');
        if (settings.autoDownload) {
          setTimeout(() => triggerDownload(wsMessage.job_id), 500);
        }
      }
      if (wsMessage.status === 'failed') {
        clearPoll();
        toast.error('Download failed. Try again.');
        haptic.trigger('error');
      }
    }
  }, [wsMessage, jobStatus?.job_id, clearPoll, toast, haptic, settings.autoDownload]);

  const handleScan = useCallback(async (targetUrl: string) => {
    setError('');
    setIsLoading(true);
    haptic.trigger('medium');
    try {
      const result = audioOnly ? await probeAudio(targetUrl) : await probeUrl(targetUrl);
      setUrl(targetUrl);
      setProbeResult(result);
      setStep('select');
      toast.success(`Found ${audioOnly ? 'audio' : 'video'} formats!`);
    } catch (err: any) {
      setError(err.message || 'Probe failed');
      toast.error(err.message || 'Probe failed');
      haptic.trigger('error');
    } finally {
      setIsLoading(false);
    }
  }, [audioOnly, toast, haptic]);

  const handleSelectResolution = useCallback(async (height: number) => {
    setError('');
    setIsLoading(true);
    haptic.trigger('medium');
    try {
      const download = audioOnly
        ? await startAudioDownload(url, 'mp3', '192')
        : await startDownload(url, height);
      setJobStatus({ job_id: download.job_id, status: 'queued', progress: 0, message: 'In queue' });
      setStep('progress');
      setIsLoading(false);
      toast.info('Download queued');

      pollRef.current = setInterval(async () => {
        try {
          const status = await getJobStatus(download.job_id);
          setJobStatus(status);
          if (status.status === 'completed' || status.status === 'failed') {
            clearPoll();
            if (status.status === 'completed') {
              toast.success('Download complete!');
              haptic.trigger('success');
              if (settings.autoDownload) {
                setTimeout(() => triggerDownload(download.job_id), 500);
              }
            } else {
              toast.error('Download failed');
              haptic.trigger('error');
            }
          }
        } catch (err: any) {
          console.error('Poll error:', err);
          clearPoll();
        }
      }, settings.enableWebSocket ? 3000 : 2000);
    } catch (err: any) {
      setError(err.message || 'Failed to queue download');
      toast.error(err.message || 'Failed to queue download');
      haptic.trigger('error');
      setIsLoading(false);
    }
  }, [url, audioOnly, clearPoll, toast, haptic, settings.enableWebSocket, settings.autoDownload]);

  const handleBatchSubmit = useCallback(async (urls: string[]) => {
    setError('');
    setIsLoading(true);
    haptic.trigger('medium');
    try {
      const batch = await startBatchDownload(urls, settings.defaultHeight);
      setJobStatus({ job_id: batch.batch_id, status: 'queued', progress: 0, message: `Batch: ${batch.total} jobs queued` });
      setStep('progress');
      setIsLoading(false);
      toast.info(`Batch queued: ${batch.total} URLs`);
    } catch (err: any) {
      setError(err.message || 'Batch failed');
      toast.error(err.message || 'Batch failed');
      haptic.trigger('error');
      setIsLoading(false);
    }
  }, [settings.defaultHeight, toast, haptic]);

  const handleDownload = useCallback(() => {
    if (jobStatus?.job_id) {
      triggerDownload(jobStatus.job_id);
      haptic.trigger('success');
      toast.success('Download started');
    }
  }, [jobStatus, haptic, toast]);

  const handleShare = useCallback(async () => {
    if (jobStatus?.job_id) {
      const ok = await shareDownload(jobStatus.job_id, probeResult?.title);
      if (ok) toast.success('Shared!');
      else {
        const url = `${window.location.origin}/api/download/${jobStatus.job_id}/file`;
        copyToClipboard(url);
        toast.info('Link copied to clipboard');
      }
    }
  }, [jobStatus, probeResult, toast]);

  const handleReset = useCallback(() => {
    clearPoll();
    setStep('input');
    setUrl('');
    setProbeResult(null);
    setJobStatus(null);
    setError('');
  }, [clearPoll]);

  const handleOpenHistory = useCallback(async () => {
    setShowHistory(true);
    try {
      const entries = await fetchHistory();
      setHistory(entries);
    } catch {}
  }, []);

  const handleOpenBatch = useCallback(() => {
    setStep('batch');
  }, []);

  // Keyboard shortcuts
  useKeyboard({
    'ctrl+enter': () => {
      if (step === 'input' && !isLoading) {
        const input = document.querySelector('input[type="url"]') as HTMLInputElement;
        if (input?.value) handleScan(input.value);
      }
    },
    'escape': () => {
      if (showSettings) setShowSettings(false);
      else if (showHistory) setShowHistory(false);
      else if (step !== 'input') handleReset();
    },
    'b': () => {
      if (step === 'input') handleOpenBatch();
    },
    's': () => {
      if (step === 'input') setShowSettings(true);
    },
  });

  // Deep linking: check URL params for shared URLs
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const sharedUrl = params.get('url');
    if (sharedUrl && step === 'input') {
      handleScan(decodeURIComponent(sharedUrl));
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, [step, handleScan]);

  return (
    <ErrorBoundary>
      <div className="min-h-[100dvh] flex flex-col items-center justify-center safe-top safe-bottom px-4 py-8">
        {/* Offline banner */}
        {isOffline && <OfflineBanner />}

        {/* Toast notifications */}
        <ToastContainer toasts={toast.toasts} onRemove={toast.remove} />

        {/* Settings */}
        {showSettings && <SettingsPanel open={showSettings} onClose={() => setShowSettings(false)} />}

        {/* History */}
        {showHistory && <DownloadHistory entries={history} onClose={() => setShowHistory(false)} />}

        <div className="w-full max-w-sm">
          {/* Header actions */}
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={() => setShowSettings(true)}
              className="p-2 rounded-xl text-slate-500 hover:text-white hover:bg-dark-surface transition-colors"
              aria-label="Settings"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.22 1.033.07l1.137-.513a1.125 1.125 0 011.45.397l1.296 2.247a1.125 1.125 0 01-.26 1.432l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.49l-1.003-.352c-.296-.104-.62-.05-.863.143-.29.23-.514.528-.642.864-.128.336-.166.698-.09 1.05l.213 1.281c.09.543-.29 1.032-1.11 1.032h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.063-.374-.313-.686-.645-.87a4.618 4.618 0 01-.22-.127c-.324-.196-.72-.22-1.033-.07l-1.137.513a1.125 1.125 0 01-1.45-.397l-1.296-2.247a1.125 1.125 0 01.26-1.432l1.003-.827c.293-.24.438-.613.431-.992a6.75 6.75 0 010-.255c.007-.378-.138-.75-.43-.99l-1.005-.828a1.125 1.125 0 01-.26-1.43l1.298-2.247a1.125 1.125 0 011.369-.49l1.003.352c.296.104.62.05.863-.143.29-.23.514-.528.642-.864.128-.336.166-.698.09-1.05L9.594 3.94z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
            <div className="flex items-center gap-2">
              <button
                onClick={handleOpenHistory}
                className="p-2 rounded-xl text-slate-500 hover:text-white hover:bg-dark-surface transition-colors"
                aria-label="History"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </button>
            </div>
          </div>

          {/* Global Error */}
          {error && step === 'input' && (
            <div className="mb-4 rounded-2xl bg-red-950/40 border border-red-900/50 p-4 animate-fade-in">
              <p className="text-xs text-red-300 leading-relaxed">{error}</p>
            </div>
          )}

          {/* Install Prompts */}
          {install.canInstall && step === 'input' && (
            <div className="mb-4 rounded-2xl bg-siphon-950 border border-siphon-700 p-4 animate-fade-in">
              <div className="flex items-start gap-3">
                <img src="/logo-sm.png" alt="" className="h-8 w-8 object-contain shrink-0 mt-0.5" draggable={false} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white">Install Siphon</p>
                  <p className="text-xs text-siphon-300 mt-1">Add to your home screen for quick access.</p>
                </div>
                <button onClick={install.dismiss} className="text-siphon-400 hover:text-white text-lg shrink-0">✕</button>
              </div>
              <button onClick={install.promptInstall} className="mt-3 w-full rounded-xl bg-siphon-600 hover:bg-siphon-500 text-white text-sm font-medium py-2.5 transition-colors">Install App</button>
            </div>
          )}
          {install.isIos && step === 'input' && (
            <div className="mb-4 rounded-2xl bg-siphon-950 border border-siphon-700 p-4 animate-fade-in">
              <div className="flex items-start gap-3">
                <img src="/logo-sm.png" alt="" className="h-8 w-8 object-contain shrink-0 mt-0.5" draggable={false} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white">Install on iOS</p>
                  <p className="text-xs text-siphon-300 mt-1">Tap <span className="inline-block align-middle mx-0.5"><svg className="h-3.5 w-3.5 inline" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M7.5 12l4.5 4.5m0 0l4.5-4.5m-4.5 4.5V3" /></svg></span> then <strong>Add to Home Screen</strong>.</p>
                </div>
                <button onClick={install.dismiss} className="text-siphon-400 hover:text-white text-lg shrink-0">✕</button>
              </div>
            </div>
          )}

          {/* Step 1: Input */}
          {step === 'input' && (
            <>
              <UrlInput onScan={handleScan} isLoading={isLoading} />
              <div className="mt-4 flex items-center justify-center gap-3">
                <AudioToggle enabled={audioOnly} onToggle={() => setAudioOnly(!audioOnly)} />
                <button
                  onClick={handleOpenBatch}
                  className="flex items-center gap-2 rounded-xl border border-dark-border bg-dark-surface px-3 py-2 text-sm font-medium text-slate-400 hover:text-white transition-colors"
                >
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z" />
                  </svg>
                  Batch
                </button>
              </div>
            </>
          )}

          {/* Step 2: Select */}
          {step === 'select' && probeResult && (
            <ResolutionSelector
              formats={probeResult.formats}
              heights={probeResult.heights}
              onSelect={handleSelectResolution}
              isLoading={isLoading}
              onBack={handleReset}
            />
          )}

          {/* Step 3: Progress */}
          {step === 'progress' && jobStatus && (
            <>
              <ProgressTracker
                status={jobStatus.status}
                progress={jobStatus.progress ?? null}
                message={jobStatus.message ?? null}
                error={jobStatus.error ?? null}
                onDownload={handleDownload}
                onReset={handleReset}
              />
              {jobStatus.status === 'completed' && (
                <div className="mt-3 space-y-3">
                  <button
                    onClick={handleShare}
                    className="w-full rounded-2xl border border-dark-border bg-transparent hover:bg-dark-surface text-slate-300 font-medium py-3.5 text-sm transition-colors flex items-center justify-center gap-2"
                  >
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c-.18.324-.283.696-.283 1.093s.103.77.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0-12.186l-9.566 5.314" />
                    </svg>
                    Share
                  </button>
                  <QRCodeDisplay jobId={jobStatus.job_id} />
                </div>
              )}
            </>
          )}

          {/* Batch Step */}
          {step === 'batch' && (
            <BatchInput onSubmit={handleBatchSubmit} isLoading={isLoading} onBack={handleReset} />
          )}
        </div>

        {/* Footer */}
        <div className="mt-auto pt-8 text-center space-y-2">
          <p className="text-[10px] text-slate-600 tracking-wider uppercase">Siphon — Private. Unindexed. Ephemeral.</p>
          {isOffline && <p className="text-[10px] text-amber-600">Offline mode</p>}
        </div>
      </div>
    </ErrorBoundary>
  );
};

export default App;
