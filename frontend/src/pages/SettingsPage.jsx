import React, { useState, useEffect } from 'react';
import { 
  Settings, 
  Volume2, 
  Mic, 
  Key, 
  Sparkles, 
  CheckCircle2, 
  Save, 
  Play, 
  RotateCcw,
  ShieldCheck,
  Cpu
} from 'lucide-react';
import { getSettingsStatus, saveGeminiKey } from '../api';

export default function SettingsPage() {
  const [geminiKey, setGeminiKey] = useState('');
  const [hasServerKey, setHasServerKey] = useState(false);
  const [maskedKey, setMaskedKey] = useState('');
  const [voices, setVoices] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState('');
  const [speechRate, setSpeechRate] = useState(1.05);
  const [speechPitch, setSpeechPitch] = useState(1.0);
  const [silenceThreshold, setSilenceThreshold] = useState(0.9);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    // Load voices
    const loadVoices = () => {
      if ('speechSynthesis' in window) {
        const available = window.speechSynthesis.getVoices();
        setVoices(available);
        if (available.length > 0 && !selectedVoice) {
          const defaultV = available.find(v => v.lang.startsWith('en')) || available[0];
          setSelectedVoice(defaultV.name);
        }
      }
    };
    loadVoices();
    if ('speechSynthesis' in window) {
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }

    // Load API settings status
    const fetchStatus = async () => {
      try {
        const res = await getSettingsStatus();
        setHasServerKey(res.gemini_configured);
        setMaskedKey(res.masked_key || '');
      } catch (e) {
        console.error('Failed to get settings status:', e);
      }
    };
    fetchStatus();
  }, []);

  const handleSaveApiKey = async (e) => {
    e.preventDefault();
    if (!geminiKey.trim()) return;
    try {
      setSaving(true);
      const res = await saveGeminiKey(geminiKey.trim());
      setHasServerKey(res.gemini_configured);
      setMaskedKey(res.masked_key || '');
      setGeminiKey('');
      setMessage({ type: 'success', text: 'Gemini API Key saved and verified successfully!' });
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setSaving(false);
    }
  };

  const handleTestVoice = () => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance("Hello! Welcome to VoxSales Academy. This is your autonomous sales assistant voice.");
    u.rate = speechRate;
    u.pitch = speechPitch;
    const v = voices.find(vox => vox.name === selectedVoice);
    if (v) u.voice = v;
    window.speechSynthesis.speak(u);
  };

  return (
    <div className="flex-1 p-6 max-w-4xl mx-auto w-full space-y-6 overflow-y-auto">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
          <Settings className="w-6 h-6 text-indigo-600" />
          <span>System & Voice Settings</span>
        </h2>
        <p className="text-xs text-slate-500 font-medium">
          Configure speech synthesis voice, mic silence detection threshold, and Gemini AI credentials.
        </p>
      </div>

      {message && (
        <div className={`p-4 rounded-2xl text-xs font-semibold flex items-center justify-between ${
          message.type === 'success' 
            ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' 
            : 'bg-rose-50 text-rose-800 border border-rose-200'
        }`}>
          <span>{message.text}</span>
          <button onClick={() => setMessage(null)} className="cursor-pointer">&times;</button>
        </div>
      )}

      {/* Card 1: Voice & Speech Synthesis */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-5">
        <h3 className="font-bold text-sm text-slate-900 flex items-center gap-2">
          <Volume2 className="w-4 h-4 text-cyan-600" />
          <span>Speech Synthesis & Audio Output</span>
        </h3>

        <div className="space-y-4 text-xs">
          <div>
            <label className="font-semibold text-slate-700 block mb-1">Text-to-Speech Voice</label>
            <select
              value={selectedVoice}
              onChange={(e) => setSelectedVoice(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-800 font-medium outline-none cursor-pointer"
            >
              {voices.map((v, idx) => (
                <option key={idx} value={v.name}>
                  {v.name} ({v.lang})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <div className="flex justify-between font-semibold text-slate-700 mb-1">
                <span>Speech Speed (Rate)</span>
                <span className="text-cyan-700">{speechRate}x</span>
              </div>
              <input
                type="range"
                min="0.8"
                max="1.4"
                step="0.05"
                value={speechRate}
                onChange={(e) => setSpeechRate(parseFloat(e.target.value))}
                className="w-full accent-cyan-600 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between font-semibold text-slate-700 mb-1">
                <span>Voice Pitch</span>
                <span className="text-cyan-700">{speechPitch}x</span>
              </div>
              <input
                type="range"
                min="0.8"
                max="1.3"
                step="0.05"
                value={speechPitch}
                onChange={(e) => setSpeechPitch(parseFloat(e.target.value))}
                className="w-full accent-cyan-600 cursor-pointer"
              />
            </div>
          </div>

          <div className="pt-2">
            <button
              onClick={handleTestVoice}
              className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs flex items-center gap-2 cursor-pointer transition"
            >
              <Play className="w-3.5 h-3.5 text-cyan-700 fill-current" />
              <span>Test Audio Playback</span>
            </button>
          </div>
        </div>
      </div>

      {/* Card 2: Voice Recognition (STT) Settings */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
        <h3 className="font-bold text-sm text-slate-900 flex items-center gap-2">
          <Mic className="w-4 h-4 text-indigo-600" />
          <span>Speech Recognition & Silence Detection</span>
        </h3>

        <div className="space-y-3 text-xs">
          <div>
            <div className="flex justify-between font-semibold text-slate-700 mb-1">
              <span>Silence Auto-Submit Delay</span>
              <span className="text-indigo-600">{silenceThreshold} seconds</span>
            </div>
            <input
              type="range"
              min="0.6"
              max="2.0"
              step="0.1"
              value={silenceThreshold}
              onChange={(e) => setSilenceThreshold(parseFloat(e.target.value))}
              className="w-full accent-indigo-600 cursor-pointer"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Controls how long the system waits after you finish speaking before sending your inquiry to the AI agent. (Recommended: 0.8s–1.0s).
            </p>
          </div>
        </div>
      </div>

      {/* Card 3: Gemini Model & AI Configuration */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-5">
        <h3 className="font-bold text-sm text-slate-900 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-amber-600" />
          <span>Gemini AI Engine & Credentials</span>
        </h3>

        <div className="space-y-4 text-xs">
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
            <div>
              <p className="font-bold text-slate-800">Current AI Model</p>
              <p className="text-[11px] text-slate-500 font-mono mt-0.5">models/gemini-3.5-flash-lite (Sub-3s Latency)</p>
            </div>
            <span className="px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 font-bold text-[10px]">
              Active & Optimized
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
            <div>
              <p className="font-bold text-slate-800">API Key Status</p>
              <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                {hasServerKey ? (maskedKey || 'Configured in backend/.env') : 'Not Configured'}
              </p>
            </div>
            <span className={`px-2.5 py-1 rounded-full font-bold text-[10px] ${
              hasServerKey ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
            }`}>
              {hasServerKey ? 'Connected' : 'Missing Key'}
            </span>
          </div>

          <form onSubmit={handleSaveApiKey} className="space-y-2 pt-2">
            <label className="font-semibold text-slate-700 block">Update or Enter New Gemini API Key</label>
            <div className="flex items-center gap-2">
              <input
                type="password"
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                placeholder="AIzaSy... or AQ.Ab8..."
                className="flex-1 px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-800 font-mono text-xs outline-none focus:border-amber-500"
              />
              <button
                type="submit"
                disabled={saving || !geminiKey.trim()}
                className="px-4 py-2.5 rounded-xl bg-[#0c1427] hover:bg-[#15233e] text-white font-bold text-xs flex items-center gap-2 cursor-pointer disabled:opacity-40"
              >
                <Save className="w-3.5 h-3.5 text-cyan-400" />
                <span>Save Key</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
