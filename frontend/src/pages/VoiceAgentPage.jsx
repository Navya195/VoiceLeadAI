import React, { useState, useEffect, useRef } from 'react';
import { 
  Mic, 
  MicOff, 
  Send, 
  Volume2, 
  VolumeX, 
  Sparkles, 
  Bot, 
  User, 
  Calendar, 
  Clock, 
  ShieldCheck, 
  Database, 
  Flame, 
  AlertCircle,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Phone,
  Mail,
  Key,
  Check,
  Square,
  Play,
  RotateCcw
} from 'lucide-react';
import { interactWithAgent } from '../api';

export default function VoiceAgentPage({ onOpenBookingWithData, onOpenApiKeyModal }) {
  const [sessionId, setSessionId] = useState('');
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState('');
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(true);
  const [selectedLanguage, setSelectedLanguage] = useState('en-IN');
  const [consultationStatus, setConsultationStatus] = useState('Idle'); // 'Idle', 'In Consultation'
  const [micError, setMicError] = useState(null);
  
  // Real-time Lead Qualification State
  const [leadProfile, setLeadProfile] = useState({
    name: null,
    email: null,
    phone: null,
    interested_course: null,
    score: 10,
    category: 'Cold',
    sentiment: 'Neutral'
  });

  // Last RAG Sources
  const [ragSources, setRagSources] = useState([]);
  const [showRagSources, setShowRagSources] = useState(true);

  const recognitionRef = useRef(null);
  const messagesEndRef = useRef(null);
  const silenceTimerRef = useRef(null);
  const accumulatedSpeechRef = useRef('');

  // Initialize Session
  const initNewSession = () => {
    const newSession = 'sess_' + Math.random().toString(36).substring(2, 10);
    setSessionId(newSession);
    setConsultationStatus('Idle');
    setMessages([]);
    setLiveTranscript('');
    accumulatedSpeechRef.current = '';
    setLeadProfile({
      name: null,
      email: null,
      phone: null,
      interested_course: null,
      score: 10,
      category: 'Cold',
      sentiment: 'Neutral'
    });
  };

  useEffect(() => {
    initNewSession();

    // Setup Web Speech Recognition with Continuous & Interim support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = selectedLanguage;

      recognition.onstart = () => {
        setIsListening(true);
        setMicError(null);
        setLiveTranscript('');
        accumulatedSpeechRef.current = '';
      };

      recognition.onresult = (event) => {
        let finalChunk = '';
        let interimChunk = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalChunk += event.results[i][0].transcript;
          } else {
            interimChunk += event.results[i][0].transcript;
          }
        }

        if (finalChunk) {
          accumulatedSpeechRef.current += (accumulatedSpeechRef.current ? ' ' : '') + finalChunk.trim();
        }

        const fullSpokenText = (accumulatedSpeechRef.current + ' ' + interimChunk).trim();
        setLiveTranscript(fullSpokenText);

        // Reset silence detection timer (0.9 seconds of silence = fast auto-submit)
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current);
        }
        silenceTimerRef.current = setTimeout(() => {
          finishAndSubmitVoice();
        }, 900);
      };

      recognition.onerror = (event) => {
        if (event.error === 'not-allowed') {
          setMicError('Microphone permission denied. Please allow microphone access or use the text chat/interview demo below.');
          setIsListening(false);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    } else {
      setMicError('Web Speech API is not supported in this browser. Please use Google Chrome or Microsoft Edge for voice, or use the interactive demo buttons below.');
    }

    return () => {
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch (e) {}
      }
      window.speechSynthesis.cancel();
    };
  }, [selectedLanguage]);

  // Scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading, liveTranscript]);

  // Finish and Submit Spoken Voice
  const finishAndSubmitVoice = () => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
    }
    const textToSend = accumulatedSpeechRef.current.trim() || liveTranscript.trim();
    setLiveTranscript('');
    accumulatedSpeechRef.current = '';

    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) {}
    }
    setIsListening(false);

    if (textToSend && textToSend.length >= 2) {
      handleSendMessage(textToSend, 'voice');
    }
  };

  // Multilingual Greetings Dictionary (Spoken in clear, fluent English)
  const greetings = {
    'en-IN': "Hello! Welcome to VoiceLead AI Academy. I am VoiceLead AI, your AI sales advisor. We offer specialized career bootcamps in Python, Java Microservices, Full Stack MERN, AI/Machine Learning, and DSA for placements. How can I help boost your tech career today?",
    'en-US': "Hello! Welcome to VoiceLead AI Academy. I am VoiceLead AI, your AI sales advisor. How can I help boost your tech career today?",
    'hi-IN': "Hello and welcome to VoxSales Academy! You can speak to me in Hindi or English. I can help you with course fees, syllabus, and placement support for Python, Java, Full Stack, AI, and DSA. How can I assist you today?",
    'te-IN': "Hello and welcome to VoxSales Academy! You can speak to me in Telugu or English. I can assist you with our bootcamps in Python, Java, Full Stack Web Development, AI, and DSA for placements. How can I help you today?",
    'ta-IN': "Hello and welcome to VoxSales Academy! You can speak to me in Tamil or English. I can help you explore our technical bootcamps in Python, Java, Full Stack, AI, and DSA. How can I help you today?",
    'kn-IN': "Hello and welcome to VoxSales Academy! You can speak to me in Kannada or English. I can assist you with our course syllabus, fees, and placement programs in Python, Java, Full Stack, and AI. What would you like to know?",
    'ml-IN': "Hello and welcome to VoxSales Academy! You can speak to me in Malayalam or English. I am here to assist you with our programs in Python, Java, Full Stack, AI, and DSA. How can I help your career today?"
  };

  // Multilingual Demo Scenarios
  const localizedDemoScenarios = {
    'en-IN': [
      { title: "Cloud & DevOps Engineering", query: "What are the fees, duration, and AWS/Kubernetes topics in the Cloud & DevOps Engineering program?", badge: "Fees" },
      { title: "Cybersecurity & Ethical Hacking", query: "Tell me about the Cybersecurity & Ethical Hacking curriculum and placement assistance.", badge: "Placements" },
      { title: "Data Engineering & Analytics", query: "Does the Data Engineering & Analytics course cover Spark, Snowflake, and real-world projects?", badge: "Curriculum" },
      { title: "AI & ML Specialist Capstones", query: "Does the AI & Machine Learning course cover GenAI, LLMs, and real-world projects?", badge: "AI / ML" },
      { title: "Mobile App Dev (Flutter & React Native)", query: "I would like to know about the Mobile App Development program and book a 1-on-1 counseling slot.", badge: "Booking" }
    ],
    'hi-IN': [
      { title: "पायथन फीस और EMI", query: "पायथन प्रोग्रामिंग बूटकैंप की फीस और EMI विकल्प क्या हैं?", badge: "फीस" },
      { title: "फुल स्टैक प्लेसमेंट सपोर्ट", query: "फुल स्टैक वेब डेवलपमेंट का सिलेबस और 100% प्लेसमेंट सपोर्ट के बारे में बताएं।", badge: "प्लेसमेंट" },
      { title: "AI और मशीन लर्निंग प्रोजेक्ट्स", query: "क्या AI और मशीन लर्निंग स्पेशलिस्ट में GenAI और LLM कवर किया जाता है?", badge: "सिलेबस" },
      { title: "काउंसलिंग स्लॉट बुक करें", query: "मुझे कल के लिए एक फ्री 1-on-1 काउंसलिंग स्लॉट बुक करना है।", badge: "बुकिंग" }
    ],
    'te-IN': [
      { title: "పైథాన్ ఫీజు & EMI వివరాలు", query: "పైథాన్ ప్రోగ్రామింగ్ బూట్‌క్యాంప్ ఫీజు మరియు EMI ఎంపికలు ఏమిటి?", badge: "ఫీజు" },
      { title: "ఫుల్ స్టాక్ ప్లేస్‌మెంట్స్", query: "ఫుల్ స్టాక్ వెబ్ డెవలప్‌మెంట్ సిలబస్ మరియు ప్లేస్‌మెంట్ సహాయం గురించి చెప్పండి.", badge: "ప్లేస్‌మెంట్స్" },
      { title: "AI & మెషిన్ లెర్నింగ్ ప్రోగ్రామ్", query: "AI మరియు మెషిన్ లెర్నింగ్ కోర్సులో GenAI మరియు LLM నేర్పిస్తారా?", badge: "సిలబస్" },
      { title: "కౌన్సెలింగ్ స్లాట్ బుకింగ్", query: "నేను రేపటి కోసం 1-on-1 కెరీర్ కౌన్సెలింగ్ అపాయింట్‌మెంట్ బుక్ చేసుకోవాలనుకుంటున్నాను.", badge: "బుకింగ్" }
    ],
    'ta-IN': [
      { title: "பைதான் கட்டணம் & EMI", query: "பைதான் புரோகிராமிங் பாடநெறி கட்டணம் மற்றும் EMI விவரங்கள் என்ன?", badge: "கட்டணம்" },
      { title: "ஃபுல் ஸ்டாக் வேலைவாய்ப்பு", query: "ஃபுல் ஸ்டாக் வெப் டெவலப்மெண்ட் பாடத்திட்டம் மற்றும் வேலைவாய்ப்பு உதவி பற்றி சொல்லுங்கள்.", badge: "வேலைவாய்ப்பு" },
      { title: "AI மற்றும் மெஷின் லேர்னிங்", query: "AI மற்றும் மெஷின் லேர்னிங் படிப்பில் GenAI மற்றும் LLMs கற்றுக்கொடுக்கப்படுமா?", badge: "பாடத்திட்டம்" },
      { title: "ஆலோசனை முன்பதிவு", query: "நாளைய தினத்திற்கு இலவச 1-on-1 ஆலோசனை நேரம் முன்பதிவு செய்ய விரும்புகிறேன்.", badge: "முன்பதிவு" }
    ],
    'kn-IN': [
      { title: "ಪೈಥಾನ್ ಶುಲ್ಕ & EMI", query: "ಪೈಥಾನ್ ಪ್ರೋಗ್ರಾಮಿಂಗ್ ಬೂಟ್‌ಕ್ಯಾಂಪ್ ಶುಲ್ಕ ಮತ್ತು ಇಎಂಐ ಆಯ್ಕೆಗಳು ಯಾವುವು?", badge: "ಶುಲ್ಕ" },
      { title: "ಫುಲ್ ಸ್ಟ್ಯಾಕ್ ಉದ್ಯೋಗ ಬೆಂಬಲ", query: "ಫುಲ್ ಸ್ಟ್ಯಾಕ್ ವೆಬ್ ಡೆವಲಪ್‌ಮೆಂಟ್ ಪಠ್ಯಕ್ರಮ ಮತ್ತು ಪ್ಲೇಸ್‌ಮೆಂಟ್ ಬೆಂಬಲದ ಬಗ್ಗೆ ತಿಳಿಸಿ.", badge: "ಪ್ಲೇಸ್‌ಮೆಂಟ್" },
      { title: "AI ಮತ್ತು ಮೆಷಿನ್ ಲರ್ನಿಂಗ್", query: "AI ಮತ್ತು ಮೆಷಿನ್ ಲರ್ನಿಂಗ್ ಕೋರ್ಸ್‌ನಲ್ಲಿ GenAI ಮತ್ತು LLM ಕಲಿಸಲಾಗುತ್ತದೆಯೇ?", badge: "ಪಠ್ಯಕ್ರಮ" },
      { title: "ಕೌನ್ಸೆಲಿಂಗ್ ಸ್ಲಾಟ್ ಕಾಯ್ದಿರಿಸಿ", query: "ನಾನು ನಾಳೆಗೆ 1-on-1 ವೃತ್ತಿ ಕೌನ್ಸೆಲಿಂಗ್ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಕಾಯ್ದಿರಿಸಲು ಬಯಸುತ್ತೇನೆ.", badge: "ಬುಕಿಂಗ್" }
    ],
    'ml-IN': [
      { title: "പൈത്തൺ ഫീസും ഇഎംഐയും", query: "പൈത്തൺ പ്രോഗ്രാമിംഗ് കോഴ്സിന്റെ ഫീസും ഇഎംഐ ഓപ്ഷനുകളും എന്തൊക്കെയാണ്?", badge: "ഫീസ്" },
      { title: "ഫുൾ സ്റ്റാക്ക് പ്ലേസ്മെന്റ്", query: "ഫുൾ സ്റ്റാക്ക് വെബ് ഡെവലപ്‌മെന്റ് സിലബസും പ്ലേസ്‌മെന്റ് പിന്തുണയും അറിയിക്കൂ.", badge: "പ്ലേസ്മെന്റ്" },
      { title: "AI & മെഷീൻ ലേണിംഗ്", query: "AI, മെഷീൻ ലേണിംഗ് കോഴ്സിൽ GenAI-യും LLM-ഉം ഉൾപ്പെടുന്നുണ്ടോ?", badge: "സിലബസ്" },
      { title: "കൗൺസിലിംഗ് സ്ലോട്ട് ബുക്ക് ചെയ്യുക", query: "നാളത്തേക്ക് ഒരു കൗൺസിലിംഗ് അപ്പോയിന്റ്മെന്റ് ബുക്ക് ചെയ്യാൻ ആഗ്രഹിക്കുന്നു.", badge: "ബുക്കിംഗ്" }
    ]
  };

  // Text to Speech
  const speakResponse = (text) => {
    if (!autoSpeak || !('speechSynthesis' in window)) return;
    
    // Stop microphone immediately to prevent feedback loop
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) {}
      setIsListening(false);
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    // Always articulate voice in fluent, clear English so no words are skipped or truncated
    utterance.lang = 'en-IN';
    
    const voices = window.speechSynthesis.getVoices();
    const englishVoice = voices.find(v => {
      const vLang = (v.lang || '').toLowerCase().replace('_', '-');
      return vLang.includes('en-in') || vLang.includes('en-us') || vLang.includes('en-gb') || vLang.startsWith('en');
    });

    if (englishVoice) {
      utterance.voice = englishVoice;
    }

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
  };

  const stopAudio = () => {
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  };

  const [showNameModal, setShowNameModal] = useState(false);
  const [candidateNameInput, setCandidateNameInput] = useState(() => {
    try { return JSON.parse(localStorage.getItem('vl_customer_details') || '{}').name || ''; } catch { return ''; }
  });
  const [customerEmailInput, setCustomerEmailInput] = useState(() => {
    try { return JSON.parse(localStorage.getItem('vl_customer_details') || '{}').email || ''; } catch { return ''; }
  });
  const [detailsError, setDetailsError] = useState('');
  const [detailsSaved, setDetailsSaved] = useState(() => {
    try {
      const d = JSON.parse(localStorage.getItem('vl_customer_details') || '{}');
      return Boolean(d.name && d.email);
    } catch { return false; }
  });

  const handleSaveAndStart = async (e) => {
    if (e) e.preventDefault();
    const name = candidateNameInput.trim();
    const email = customerEmailInput.trim();
    if (!name) {
      setDetailsError('Please enter your Full Name.');
      return;
    }
    if (!/^[^\s@]+@gmail\.com$/i.test(email)) {
      setDetailsError('Please enter a valid Gmail address (e.g. name@gmail.com).');
      return;
    }
    setDetailsError('');
    setDetailsSaved(true);
    localStorage.setItem('vl_customer_details', JSON.stringify({ name, email }));
    setLeadProfile(prev => ({ ...prev, name, email }));
    setConsultationStatus('In Consultation');

    try {
      await handleSendMessage(`My name is ${name} and my email is ${email}. Please greet me personally by name and welcome me to VoiceLead AI.`, 'text', true);
    } catch (err) {
      const baseGreeting = greetings[selectedLanguage] || greetings['en-IN'];
      const greeting = `Hello ${name}! ${baseGreeting.replace(/^Hello!?\s*/i, '')}`;
      setMessages([{ role: 'assistant', content: greeting, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
      if (autoSpeak) speakResponse(greeting);
    }

    setTimeout(() => {
      if (!isListening && recognitionRef.current) {
        try {
          recognitionRef.current.start();
          setIsListening(true);
        } catch (err) {}
      }
    }, 800);
  };

  // Start Conversation (From top banner) - requires saved details first
  const handleStartConversation = () => {
    if (!detailsSaved) {
      setDetailsError('Please save your Full Name and Gmail Address on the right panel first.');
      return;
    }
    handleSaveAndStart();
  };

  const confirmStartWithName = async (e) => {
    if (e) e.preventDefault();
    const trimmedName = candidateNameInput.trim() || 'there';
    setShowNameModal(false);
    if (candidateNameInput.trim()) {
      setLeadProfile(prev => ({ ...prev, name: candidateNameInput.trim() }));
    }
    setConsultationStatus('In Consultation');

    try {
      await handleSendMessage(`My name is ${trimmedName}. Please greet me personally by name and welcome me to VoiceLead AI.`);
    } catch (err) {
      const baseGreeting = greetings[selectedLanguage] || greetings['en-IN'];
      const greeting = `Hello ${trimmedName}! ${baseGreeting.replace(/^Hello!?\s*/i, '')}`;
      setMessages([{ role: 'assistant', content: greeting, timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
      if (autoSpeak) speakResponse(greeting);
    }

    setTimeout(() => {
      if (!isListening && recognitionRef.current) {
        try {
          recognitionRef.current.start();
          setIsListening(true);
        } catch (err) {}
      }
    }, 800);
  };

  // End Conversation (From top banner)
  const handleEndConversation = () => {
    stopAudio();
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) {}
    }
    setIsListening(false);
    setConsultationStatus('Idle');
    setLiveTranscript('');
  };

  const hasSavedDetails = () => {
    if (detailsSaved) return true;
    try {
      const d = JSON.parse(localStorage.getItem('vl_customer_details') || '{}');
      return Boolean(d.name && d.email);
    } catch {
      return false;
    }
  };

  const toggleListening = () => {
    if (!hasSavedDetails()) {
      setDetailsError('Please save your Full Name and Gmail Address first before starting audio.');
      return;
    }
    if (isSpeaking) {
      stopAudio();
    }

    if (!recognitionRef.current) {
      setMicError('Speech recognition is not available in your browser.');
      return;
    }

    if (isListening) {
      finishAndSubmitVoice();
    } else {
      try {
        setConsultationStatus('In Consultation');
        setMicError(null);
        setLiveTranscript('');
        accumulatedSpeechRef.current = '';
        recognitionRef.current.start();
      } catch (err) {
        console.error('Failed to start speech recognition:', err);
      }
    }
  };

  const handleSendMessage = async (text, mode = 'text', bypassDetailsCheck = false) => {
    if (!bypassDetailsCheck && !hasSavedDetails()) {
      setDetailsError('Please save your Full Name and Gmail Address first.');
      return;
    }
    if (!text.trim() || isLoading) return;

    // Stop speaking & mic
    stopAudio();
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) {}
      setIsListening(false);
    }

    setConsultationStatus('In Consultation');

    const userMessage = {
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setLiveTranscript('');
    setIsLoading(true);

    try {
      const data = await interactWithAgent(sessionId, text, mode, selectedLanguage);

      const assistantMessage = {
        role: 'assistant',
        content: data.reply,
        sentiment: data.sentiment,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Update lead qualifications
      if (data.lead) {
        setLeadProfile(prev => ({
          ...prev,
          name: data.lead.name || prev.name,
          email: data.lead.email || prev.email,
          phone: data.lead.phone || prev.phone,
          interested_course: data.lead.interested_course || prev.interested_course,
          score: data.lead.score ?? prev.score,
          category: data.lead.category || prev.category,
          sentiment: data.sentiment || prev.sentiment
        }));
      }

      // Update RAG chunks
      if (data.rag_sources) {
        setRagSources(data.rag_sources);
      }

      // Speak aloud
      if (autoSpeak) {
        speakResponse(data.reply);
      }
    } catch (err) {
      console.error('Agent error:', err);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: "I'm having trouble connecting to the AI backend right now. Please make sure the backend server is running on port 8000 and try again.",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const demoScenarios = localizedDemoScenarios[selectedLanguage] || localizedDemoScenarios['en-IN'];

  return (
    <div className="flex-1 p-6 max-w-7xl mx-auto w-full flex flex-col gap-5 h-[calc(100vh-4.5rem)] overflow-hidden">
      {showNameModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
          <form
            onSubmit={confirmStartWithName}
            className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-md p-6 space-y-4"
          >
            <div>
              <h3 className="text-lg font-bold text-slate-900">Welcome to VoiceLead AI</h3>
              <p className="text-xs text-slate-500 mt-1">
                Please enter your name to personalize your live voice consultation.
              </p>
            </div>
            <input
              type="text"
              autoFocus
              required
              value={candidateNameInput}
              onChange={(e) => setCandidateNameInput(e.target.value)}
              placeholder="Enter your full name..."
              className="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-cyan-500"
            />
            <div className="flex items-center justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={() => setShowNameModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-5 py-2 rounded-xl text-xs font-semibold text-white bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-700 hover:to-cyan-600 shadow-md shadow-cyan-500/20 transition cursor-pointer"
              >
                Continue
              </button>
            </div>
          </form>
        </div>
      )}
      {/* 1. TOP NAVY CONSULTANT CARD (Matching Image 1) */}
      <div className="bg-[#0c1427] text-white rounded-2xl p-5 border border-slate-800 shadow-xl shrink-0">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Left Avatar & Identity */}
          <div className="flex items-center gap-4">
            <div className="w-13 h-13 rounded-full bg-gradient-to-br from-cyan-400 via-blue-500 to-indigo-600 flex items-center justify-center text-white font-extrabold text-2xl shadow-lg shadow-cyan-500/25 shrink-0">
              V
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white tracking-tight">
                  VoiceLead AI — Autonomous Tech Sales Consultant
                </h2>
                <button
                  onClick={onOpenApiKeyModal}
                  title="Configure Gemini API Key"
                  className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-cyan-950/80 hover:bg-cyan-900 text-cyan-300 border border-cyan-800/60 flex items-center gap-1 cursor-pointer transition"
                >
                  <Key className="w-2.5 h-2.5" />
                  <span>Gemini API</span>
                </button>
              </div>
              <p className="text-xs text-slate-300/80 font-medium">
                {consultationStatus === 'Idle' 
                  ? 'Ready to start a new consultation' 
                  : isSpeaking 
                    ? 'VoiceLead AI is speaking to candidate...' 
                    : isListening 
                      ? 'Listening to customer speech...' 
                      : 'Live Consultation Active — 100% Placement Counselor'}
              </p>
            </div>
          </div>

          {/* Right Action Controls: Language + Start / End Buttons */}
          <div className="flex items-center gap-3">
            <div className="relative">
              <select
                value={selectedLanguage}
                onChange={(e) => setSelectedLanguage(e.target.value)}
                className="bg-[#14213d] text-slate-200 border border-slate-700/80 text-xs font-semibold px-3 py-2 rounded-xl outline-none cursor-pointer hover:border-slate-600 transition"
              >
                <option value="en-IN">English (India) ▼</option>
                <option value="hi-IN">Hindi (हिंदी)</option>
                <option value="te-IN">Telugu (తెలుగు)</option>
                <option value="ta-IN">Tamil (தமிழ்)</option>
                <option value="kn-IN">Kannada (ಕನ್ನಡ)</option>
                <option value="ml-IN">Malayalam (മലയാളം)</option>
                <option value="en-US">English (US)</option>
              </select>
            </div>

            <button
              onClick={handleStartConversation}
              className="bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white font-semibold text-xs px-4 py-2 rounded-xl shadow-lg shadow-emerald-700/30 flex items-center gap-2 transition cursor-pointer"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Start Conversation</span>
            </button>

            <button
              onClick={handleEndConversation}
              className="bg-rose-950/60 hover:bg-rose-900/60 text-rose-300 border border-rose-800/60 active:scale-95 font-semibold text-xs px-4 py-2 rounded-xl transition cursor-pointer flex items-center gap-2"
            >
              <Square className="w-3 h-3 fill-current" />
              <span>End Conversation</span>
            </button>
          </div>
        </div>
      </div>

      {/* 2. MAIN WORKSPACE CONTAINER */}
      <div className="flex-1 flex flex-col lg:flex-row gap-5 overflow-hidden">
        {/* Chat & Voice Area (Left) */}
        <div className="flex-1 flex flex-col bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          
          {/* Status Pills & Audio Controls Header (Matching Image 1) */}
          <div className="p-4 border-b border-slate-100 bg-slate-50/70 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 flex-wrap">
              {/* Status Badge */}
              <span className={`px-3 py-1 rounded-full text-xs font-semibold flex items-center gap-1.5 ${
                consultationStatus === 'Idle' 
                  ? 'bg-slate-200/80 text-slate-700' 
                  : 'bg-emerald-100 text-emerald-800 border border-emerald-300'
              }`}>
                <span className={`w-2 h-2 rounded-full ${consultationStatus === 'Idle' ? 'bg-slate-400' : 'bg-emerald-500 animate-pulse'}`}></span>
                <span>Status: <strong>{consultationStatus}</strong></span>
              </span>

              {/* AI Speaking Indicator */}
              <span className={`px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1.5 transition ${
                isSpeaking 
                  ? 'bg-purple-100 text-purple-700 font-semibold border border-purple-300 animate-pulse' 
                  : 'bg-slate-100 text-slate-400'
              }`}>
                <Volume2 className="w-3 h-3" />
                <span>AI Speaking</span>
              </span>

              {/* Customer Speaking Indicator */}
              <span className={`px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1.5 transition ${
                isListening 
                  ? 'bg-amber-100 text-amber-800 font-semibold border border-amber-300 animate-pulse' 
                  : 'bg-slate-100 text-slate-400'
              }`}>
                <Mic className="w-3 h-3" />
                <span>Customer Speaking</span>
              </span>

              {/* Stop Audio Button */}
              {isSpeaking && (
                <button
                  onClick={stopAudio}
                  className="px-3 py-1 rounded-lg border border-slate-300 hover:bg-slate-100 text-slate-700 text-xs font-semibold flex items-center gap-1 cursor-pointer transition"
                >
                  <VolumeX className="w-3 h-3 text-rose-500" />
                  <span>Stop Audio</span>
                </button>
              )}
            </div>

            {/* Auto-Speak Checkbox */}
            <label className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={autoSpeak}
                onChange={(e) => setAutoSpeak(e.target.checked)}
                className="w-4 h-4 text-cyan-600 rounded border-slate-300 focus:ring-cyan-500 cursor-pointer"
              />
              <span>Auto-Speak Replies</span>
            </label>
          </div>

          {/* Conversation Transcript Stream */}
          <div className="flex-1 p-5 overflow-y-auto space-y-4 bg-[#fbfcfd]">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-6">
                <div className="max-w-md space-y-2">
                  <p className="text-slate-600 text-sm">
                    Click <strong className="text-emerald-700">Start Conversation</strong> to hear VoiceLead AI's greeting, or launch the <strong>Interview Demo</strong> scenario below.
                  </p>
                </div>

                {/* Interview Demo Cards */}
                <div className="w-full max-w-xl grid grid-cols-1 md:grid-cols-2 gap-3 text-left">
                  {demoScenarios.map((sc, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSendMessage(sc.query, 'text')}
                      className="p-3.5 rounded-xl border border-slate-200 bg-white hover:border-cyan-400 hover:shadow-md transition text-left cursor-pointer group"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-600 bg-cyan-50 px-2 py-0.5 rounded-full">
                          {sc.badge}
                        </span>
                        <Play className="w-3 h-3 text-slate-300 group-hover:text-cyan-600 transition" />
                      </div>
                      <h4 className="text-xs font-bold text-slate-800 mb-1">{sc.title}</h4>
                      <p className="text-[11px] text-slate-500 line-clamp-2">{sc.query}</p>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg, index) => {
                const isAssistant = msg.role === 'assistant';
                return (
                  <div 
                    key={index} 
                    className={`flex items-start gap-3 ${isAssistant ? '' : 'flex-row-reverse'}`}
                  >
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                      isAssistant 
                        ? 'bg-gradient-to-tr from-cyan-500 to-indigo-600 text-white shadow-sm' 
                        : 'bg-slate-700 text-white'
                    }`}>
                      {isAssistant ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                    </div>

                    <div className={`max-w-[80%] rounded-2xl p-4 text-xs shadow-sm ${
                      isAssistant 
                        ? 'bg-white border border-slate-200 text-slate-800' 
                        : 'bg-[#15233e] text-white'
                    }`}>
                      <div className="flex items-center justify-between gap-3 mb-1.5 border-b border-slate-100 pb-1">
                        <span className={`font-bold text-[11px] ${isAssistant ? 'text-cyan-700' : 'text-cyan-300'}`}>
                          {isAssistant ? 'VoiceLead AI (AI Counselor)' : 'Candidate'}
                        </span>
                        <span className="text-[10px] opacity-60">{msg.timestamp}</span>
                      </div>
                      
                      <p className="leading-relaxed whitespace-pre-line text-xs font-normal">
                        {msg.content}
                      </p>

                      {isAssistant && (
                        <div className="mt-2.5 pt-2 border-t border-slate-100 flex items-center justify-between">
                          <button
                            onClick={() => speakResponse(msg.content)}
                            className="text-[11px] font-semibold text-cyan-600 hover:text-cyan-800 flex items-center gap-1 cursor-pointer"
                          >
                            <Volume2 className="w-3.5 h-3.5" />
                            <span>Listen Again</span>
                          </button>
                          {msg.sentiment && (
                            <span className="text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-medium">
                              Sentiment: {msg.sentiment}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}

            {/* Interim Live Voice Speech Transcript */}
            {isListening && liveTranscript && (
              <div className="flex items-start gap-3 flex-row-reverse">
                <div className="w-8 h-8 rounded-full bg-amber-500 text-white flex items-center justify-center shrink-0 animate-pulse">
                  <Mic className="w-4 h-4" />
                </div>
                <div className="max-w-[80%] bg-amber-50 border border-amber-200 text-amber-900 rounded-2xl p-3 text-xs shadow-sm">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="font-bold text-[10px] text-amber-700 uppercase tracking-wider flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping"></span> Live Speech Input
                    </span>
                    <button
                      onClick={finishAndSubmitVoice}
                      className="bg-amber-600 hover:bg-amber-700 text-white text-[10px] px-2 py-0.5 rounded font-bold cursor-pointer"
                    >
                      Send Now ✓
                    </button>
                  </div>
                  <p className="italic text-slate-700 font-medium">{liveTranscript}...</p>
                </div>
              </div>
            )}

            {/* Loading Indicator */}
            {isLoading && (
              <div className="flex items-center gap-3 text-xs text-slate-500 italic">
                <div className="w-7 h-7 rounded-full bg-cyan-100 text-cyan-700 flex items-center justify-center">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                </div>
                <span>VoiceLead AI is evaluating with FAISS RAG Knowledge Base...</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Voice Input & Text Fallback Footer */}
          <div className="p-4 border-t border-slate-200 bg-white">
            {micError && (
              <div className="mb-3 px-3 py-2 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
                <span>{micError}</span>
              </div>
            )}

            <div className="flex items-center gap-2">
              {/* Mic Toggle Button */}
              <button
                onClick={toggleListening}
                className={`p-3 rounded-xl flex items-center justify-center transition shadow-md cursor-pointer ${
                  isListening
                    ? 'bg-rose-500 text-white animate-pulse shadow-rose-500/30'
                    : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                }`}
                title={isListening ? 'Stop Speaking (or pause for auto-send)' : 'Speak Question with Microphone'}
              >
                {isListening ? <Mic className="w-5 h-5" /> : <Mic className="w-5 h-5 text-cyan-700" />}
              </button>

              {/* Text Input */}
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSendMessage(inputText, 'text');
                }}
                placeholder="Ask about fees, curriculum, batches, placement support, or book a slot..."
                disabled={isLoading}
                className="flex-1 px-4 py-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-800 outline-none focus:border-cyan-500 focus:bg-white transition"
              />

              {/* Send Button */}
              <button
                onClick={() => handleSendMessage(inputText, 'text')}
                disabled={isLoading || !inputText.trim()}
                className="bg-[#0c1427] hover:bg-[#15233e] disabled:opacity-40 text-white p-3 rounded-xl transition cursor-pointer"
              >
                <Send className="w-4 h-4 text-cyan-400" />
              </button>
            </div>
          </div>
        </div>

        {/* Right-Side Permanent Customer Details Dashboard */}
        <aside className="w-full lg:w-80 shrink-0 bg-white rounded-2xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between overflow-y-auto">
          <div className="space-y-4">
            <div className="border-b border-slate-100 pb-3">
              <h3 className="text-sm font-bold text-slate-900">Customer Details Dashboard</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Enter your details to unlock &amp; start the live AI voice consultation.
              </p>
            </div>

            {detailsError && (
              <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-medium">
                {detailsError}
              </div>
            )}

            {detailsSaved && !detailsError && (
              <div className="p-2.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium">
                Details saved for <strong>{candidateNameInput}</strong>
              </div>
            )}

            <form onSubmit={handleSaveAndStart} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Full Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={candidateNameInput}
                  onChange={(e) => { setCandidateNameInput(e.target.value); setDetailsError(''); }}
                  placeholder="e.g. Tera Navya"
                  className="w-full px-3.5 py-2 rounded-xl border border-slate-300 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Gmail Address <span className="text-rose-500">*</span>
                </label>
                <input
                  type="email"
                  required
                  value={customerEmailInput}
                  onChange={(e) => { setCustomerEmailInput(e.target.value); setDetailsError(''); }}
                  placeholder="e.g. navyatera36@gmail.com"
                  className="w-full px-3.5 py-2 rounded-xl border border-slate-300 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                />
              </div>

              <button
                type="submit"
                className="w-full py-2.5 px-4 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-700 hover:to-cyan-600 shadow-md shadow-cyan-500/20 transition cursor-pointer"
              >
                Save &amp; Start Conversation
              </button>
            </form>
          </div>

          <div className="pt-4 mt-4 border-t border-slate-100 text-[11px] text-slate-400">
            Your details are saved securely in browser storage and synced with your consultation session.
          </div>
        </aside>
      </div>
    </div>
  );
}
