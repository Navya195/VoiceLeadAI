import React, { useState, useEffect } from 'react';
import { Sparkles, Key, CheckCircle2, AlertCircle, ExternalLink, X, ShieldCheck } from 'lucide-react';
import { getSettingsStatus, saveGeminiKey } from '../api';

export default function ApiKeyModal({ isOpen, onClose, onKeyUpdated }) {
  const [apiKey, setApiKey] = useState('');
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    if (isOpen) {
      checkStatus();
      setError(null);
      setSuccess(null);
    }
  }, [isOpen]);

  const checkStatus = async () => {
    try {
      const data = await getSettingsStatus();
      setStatus(data);
    } catch (e) {
      console.error(e);
    }
  };

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!apiKey.trim()) return;
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const res = await saveGeminiKey(apiKey.trim());
      setSuccess(res.message);
      setStatus(prev => ({
        ...prev,
        gemini_active: true,
        has_key: true,
        key_preview: `${apiKey.trim().slice(0, 6)}...${apiKey.trim().slice(-4)}`,
        model_name: 'gemini-2.5-flash'
      }));
      setApiKey('');
      if (onKeyUpdated) onKeyUpdated();
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err) {
      setError(err.message || 'Failed to activate Gemini API key');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-purple-100">
        <div className="flex items-center justify-between pb-4 border-b border-purple-50 mb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-purple-100 text-purple-700 flex items-center justify-center">
              <Key className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-base text-slate-900">Configure Gemini API Key</h3>
              <p className="text-[11px] text-slate-400">Google Gemini LLM Integration</p>
            </div>
          </div>
          <button 
            onClick={onClose} 
            className="w-8 h-8 rounded-full hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-600 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Current Status Banner */}
        <div className="mb-4 p-3.5 rounded-2xl bg-purple-50/70 border border-purple-100 text-xs space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-slate-500 font-medium">Model Status:</span>
            <span className={`font-bold px-2 py-0.5 rounded-full text-[10px] ${
              status?.gemini_active
                ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                : 'bg-amber-100 text-amber-800 border border-amber-200'
            }`}>
              {status?.gemini_active ? 'Gemini 2.5 Flash Live' : 'Built-in Educational Engine Active'}
            </span>
          </div>
          {status?.key_preview && (
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-slate-500">Configured Key:</span>
              <span className="font-mono text-purple-800 font-semibold">{status.key_preview}</span>
            </div>
          )}
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div className="mb-4 p-3 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2 font-semibold">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{success}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="font-semibold text-slate-700 block mb-1">
              Enter your Gemini API Key
            </label>
            <input
              type="password"
              required
              placeholder="AIzaSy..."
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:border-purple-500 outline-none text-slate-900 font-mono text-xs"
            />
            <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">
              You can get a free API key at{' '}
              <a 
                href="https://aistudio.google.com/app/apikey" 
                target="_blank" 
                rel="noreferrer" 
                className="text-purple-600 hover:text-purple-800 font-bold underline inline-flex items-center gap-0.5"
              >
                Google AI Studio <ExternalLink className="w-3 h-3" />
              </a>. It will be stored securely in <code className="bg-slate-100 px-1 py-0.5 rounded font-mono">backend/.env</code>.
            </p>
          </div>

          <div className="pt-2 flex justify-end gap-2.5">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 font-semibold text-slate-700 cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !apiKey.trim()}
              className="px-5 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 font-semibold text-white shadow-md shadow-purple-600/20 cursor-pointer disabled:opacity-50 flex items-center gap-1.5"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{loading ? 'Saving & Testing...' : 'Activate Gemini API'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
