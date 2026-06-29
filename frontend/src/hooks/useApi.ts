export interface FormatInfo {
  format_id: string;
  height: number;
  width: number;
  ext: string;
  vcodec: string;
  acodec: string;
  abr?: number;
  vbr?: number;
  filesize?: number;
  filesize_approx?: number;
  video_ext?: string;
  audio_ext?: string;
  quality?: string;
}

export interface ProbeResponse {
  url: string;
  title?: string;
  thumbnail?: string;
  duration?: number;
  formats: FormatInfo[];
  heights: number[];
  message: string;
}

export interface DownloadResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface BatchDownloadResponse {
  batch_id: string;
  job_ids: string[];
  total: number;
  status: string;
  message: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: string;
  progress?: number;
  message?: string;
  file_path?: string;
  error?: string;
}

export interface HistoryEntry {
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

function getBase(): string {
  try {
    const saved = localStorage.getItem('siphon-settings');
    if (saved) {
      const s = JSON.parse(saved);
      if (s.serverUrl) return s.serverUrl.replace(/\/$/, '');
    }
  } catch {}
  return '';
}

export async function probeUrl(url: string): Promise<ProbeResponse> {
  const res = await fetch(`${getBase()}/api/probe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `Probe failed (${res.status})`);
  }
  return res.json();
}

export async function probeAudio(url: string): Promise<ProbeResponse> {
  const res = await fetch(`${getBase()}/api/probe/audio`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `Audio probe failed (${res.status})`);
  }
  return res.json();
}

export async function startDownload(url: string, height: number): Promise<DownloadResponse> {
  const res = await fetch(`${getBase()}/api/download`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, height }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `Download failed (${res.status})`);
  }
  return res.json();
}

export async function startAudioDownload(url: string, format = 'mp3', quality = '192'): Promise<DownloadResponse> {
  const res = await fetch(`${getBase()}/api/download/audio`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, format, quality }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `Audio download failed (${res.status})`);
  }
  return res.json();
}

export async function startBatchDownload(urls: string[], height: number): Promise<BatchDownloadResponse> {
  const res = await fetch(`${getBase()}/api/download/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ urls, height }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `Batch download failed (${res.status})`);
  }
  return res.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(`${getBase()}/api/download/${jobId}/status`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `Status check failed (${res.status})`);
  }
  return res.json();
}

export async function fetchHistory(): Promise<HistoryEntry[]> {
  const res = await fetch(`${getBase()}/api/history`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.entries || [];
}

export function triggerDownload(jobId: string, filename = 'siphon_video.mp4') {
  const link = document.createElement('a');
  link.href = `${getBase()}/api/download/${jobId}/file`;
  link.setAttribute('download', filename);
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

export async function shareDownload(jobId: string, title?: string) {
  const url = `${window.location.origin}/api/download/${jobId}/file`;
  if ((navigator as any).share) {
    try {
      await (navigator as any).share({
        title: title || 'Siphon Download',
        text: 'Download from Siphon',
        url,
      });
      return true;
    } catch {
      return false;
    }
  }
  return false;
}

export function copyToClipboard(text: string) {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text);
  }
}
