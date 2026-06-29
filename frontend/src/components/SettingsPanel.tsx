import React from 'react';
import { useSettings } from '../hooks/useSettings';

interface SettingsPanelProps {
  open: boolean;
  onClose: () => void;
}

const SettingsPanel: React.FC<SettingsPanelProps> = ({ open, onClose }) => {
  const { settings, update, reset } = useSettings();

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in px-4">
      <div className="w-full max-w-sm rounded-2xl bg-dark-surface border border-dark-border p-6 animate-slide-up">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-white">Settings</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-lg">✕</button>
        </div>

        <div className="space-y-5">
          {/* WebSocket */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-white">Real-time Progress</p>
              <p className="text-xs text-slate-400">Use WebSocket for live updates</p>
            </div>
            <button
              onClick={() => update({ enableWebSocket: !settings.enableWebSocket })}
              className={`relative h-6 w-11 rounded-full transition-colors ${settings.enableWebSocket ? 'bg-siphon-600' : 'bg-slate-700'}`}
            >
              <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${settings.enableWebSocket ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </button>
          </div>

          {/* Haptic */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-white">Haptic Feedback</p>
              <p className="text-xs text-slate-400">Vibrate on mobile actions</p>
            </div>
            <button
              onClick={() => update({ enableHaptic: !settings.enableHaptic })}
              className={`relative h-6 w-11 rounded-full transition-colors ${settings.enableHaptic ? 'bg-siphon-600' : 'bg-slate-700'}`}
            >
              <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${settings.enableHaptic ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </button>
          </div>

          {/* Auto-download */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-white">Auto-Download</p>
              <p className="text-xs text-slate-400">Start download immediately when ready</p>
            </div>
            <button
              onClick={() => update({ autoDownload: !settings.autoDownload })}
              className={`relative h-6 w-11 rounded-full transition-colors ${settings.autoDownload ? 'bg-siphon-600' : 'bg-slate-700'}`}
            >
              <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${settings.autoDownload ? 'translate-x-5' : 'translate-x-0.5'}`} />
            </button>
          </div>

          {/* Default resolution */}
          <div>
            <p className="text-sm font-medium text-white mb-2">Default Resolution</p>
            <div className="grid grid-cols-4 gap-2">
              {[360, 480, 720, 1080].map((h) => (
                <button
                  key={h}
                  onClick={() => update({ defaultHeight: h })}
                  className={`rounded-lg py-2 text-xs font-medium transition-colors ${
                    settings.defaultHeight === h
                      ? 'bg-siphon-600 text-white'
                      : 'bg-dark-border text-slate-400 hover:text-white'
                  }`}
                >
                  {h}p
                </button>
              ))}
            </div>
          </div>

          {/* Server URL */}
          <div>
            <p className="text-sm font-medium text-white mb-2">Custom Server</p>
            <input
              type="text"
              value={settings.serverUrl}
              onChange={(e) => update({ serverUrl: e.target.value })}
              placeholder="https://your-server.com"
              className="w-full rounded-xl bg-dark-bg border border-dark-border px-3 py-2 text-sm text-white placeholder:text-slate-600 focus:border-siphon-500 focus:outline-none"
            />
          </div>
        </div>

        <div className="mt-6 flex gap-3">
          <button
            onClick={reset}
            className="flex-1 rounded-xl border border-dark-border py-2.5 text-sm text-slate-400 hover:text-white transition-colors"
          >
            Reset Defaults
          </button>
          <button
            onClick={onClose}
            className="flex-1 rounded-xl bg-siphon-600 py-2.5 text-sm text-white font-medium hover:bg-siphon-500 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;
