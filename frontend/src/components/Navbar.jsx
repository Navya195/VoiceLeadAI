import React, { useState, useEffect } from 'react';
import { Mic, Calendar, Key, ShieldCheck, Sparkles } from 'lucide-react';
import { getSettingsStatus } from '../api';

export default function Navbar({ activeTab, onStartCall, onBookSlot, onOpenApiKeyModal }) {
  const [geminiActive, setGeminiActive] = useState(false);

  useEffect(() => {
    checkKey();
    const interval = setInterval(checkKey, 10000);
    return () => clearInterval(interval);
  }, []);

  const checkKey = async () => {
    try {
      const data = await getSettingsStatus();
      setGeminiActive(data.gemini_active);
    } catch (e) {
      // ignore
    }
  };

  const titles = {
    dashboard: { title: 'Executive Overview', desc: 'Real-time sales metrics, lead conversions & pipeline health' },
    agent: { title: 'AI Voice Sales Agent', desc: 'Interactive autonomous counselor with speech STT, RAG & Gemini' },
    leads: { title: 'Lead Management System', desc: 'Lead qualification, scoring rubric & prospective student pipeline' },
    appointments: { title: 'Counseling Appointments', desc: 'Available time slots, conflict prevention & booking confirmation' },
    knowledge: { title: 'Course Knowledge Base', desc: 'Sentence Transformers + FAISS vector search & syllabus explorer' },
    history: { title: 'Call History & Transcripts', desc: 'Recorded voice sessions, AI summaries & sentiment logs' },
    analytics: { title: 'Sales & Funnel Analytics', desc: 'Conversion rates, lead velocity & course demand insights' },
    architecture: { title: 'System Architecture', desc: 'End-to-end VoiceLeadAI pipeline, RAG & database topology' },
    settings: { title: 'Platform Settings', desc: 'API keys, voice preferences & workspace configuration' }
  };

  const current = titles[activeTab] || titles.dashboard;

  return (
    <header className="h-18 bg-white/90 backdrop-blur-md border-b border-slate-200/80 px-8 flex items-center justify-between shadow-xs sticky top-0 z-30">
      <div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">{current.title}</h2>
        <p className="text-xs text-slate-500 font-medium">{current.desc}</p>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={onOpenApiKeyModal}
          className={`hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-bold transition cursor-pointer ${
            geminiActive
              ? 'bg-cyan-50 border-cyan-300 text-cyan-900 hover:bg-cyan-100'
              : 'bg-slate-100 border-slate-300 text-slate-800 hover:bg-slate-200'
          }`}
          title="Click to configure or change Gemini API Key"
        >
          <Sparkles className={`w-3.5 h-3.5 ${geminiActive ? 'text-cyan-600' : 'text-blue-600 animate-pulse'}`} />
          <span>{geminiActive ? 'Gemini 2.5 Flash' : 'Configure Gemini API'}</span>
        </button>

        <button
          onClick={onBookSlot}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-100 text-slate-800 border border-slate-200 hover:bg-slate-200 text-xs font-semibold transition cursor-pointer"
        >
          <Calendar className="w-3.5 h-3.5 text-cyan-600" />
          <span>Book Slot</span>
        </button>

        <button
          onClick={onStartCall}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-700 hover:to-cyan-600 text-white text-xs font-semibold shadow-md shadow-cyan-500/20 transition cursor-pointer"
        >
          <Mic className="w-3.5 h-3.5" />
          <span>Launch Voice Call</span>
        </button>
      </div>
    </header>
  );
}
