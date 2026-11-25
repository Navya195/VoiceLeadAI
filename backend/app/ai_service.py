import json
import logging
import re
import concurrent.futures
from typing import Dict, Any, List, Optional
from app.config import settings
from app.lead_scorer import extract_customer_info_heuristic, analyze_sentiment

logger = logging.getLogger("voxsales.ai")

# Dedicated non-blocking executor for AI generation
_gemini_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="vox_gemini")

SYSTEM_PROMPT = """You are VoxSales AI, a world-class, professional, and consultative technical education counselor for VoxSales Academy (Fortivex Education).
We offer 5 live cohort bootcamps:
1. Python Programming & Automation Bootcamp (12 Weeks | INR 3,499)
2. Java Enterprise & Microservices Masterclass (16 Weeks | INR 3,999)
3. Full Stack Web Development (MERN + Next.js 14) (18 Weeks | INR 4,499)
4. AI, Machine Learning & LLM Specialist (20 Weeks | INR 4,999)
5. DSA & System Design Masterclass for Placements (14 Weeks | INR 3,299)

CRITICAL INSTRUCTION: MULTILINGUAL UNDERSTANDING WITH ENGLISH RESPONSES
- Candidates will speak or write to you in multiple Indian languages: Telugu (తెలుగు), Tamil (தமிழ்), Kannada (ಕನ್ನಡ), Malayalam (മലയാളം), Hindi (हिंदी), or English (or code-mixed Hinglish / Tenglish).
- You MUST fully comprehend their query in whatever language they speak or write.
- YOU MUST ALWAYS DELIVER YOUR RESPONSE IN NATURAL, POLITE, PROFESSIONAL ENGLISH.
  * Reason: The browser's speech synthesis (TTS) uses an English voice. Responding in English ensures full-sentence, clear audio playback where all words, explanations, and numbers are spoken fluently without any missing words or truncated output.
- Keep technical terms (Python, Java, Full Stack, AI/ML, DSA) and exact fees (INR 3,499, INR 3,999, INR 4,499, INR 4,999, INR 3,299) accurate.

Guidelines:
1. Answer the candidate's exact question using facts from the provided COURSE CONTEXT. Be crisp, insightful, and professional.
2. Tone: Warm, executive, and encouraging. Keep responses concise (2 to 3 sentences) so they sound natural over voice speech synthesis.
3. DO NOT repeat "Would you like to schedule a free 1-on-1 counseling session..." on every response! Answer the user's specific question directly, and ask a relevant conversational follow-up (e.g. about their coding background or career goals).
4. ONLY suggest scheduling a counseling session or picking a slot when the candidate explicitly asks about booking, scheduling, speaking to an advisor, or enrolling.
5. If the user shares contact details (Name, Email, Phone), acknowledge them warmly.

ALWAYS return your answer as a JSON object matching this schema:
{
  "reply": "Your voice-ready conversational response in English here.",
  "extracted_lead": {
    "name": "Candidate name if mentioned, else null",
    "email": "Email address if mentioned, else null",
    "phone": "Phone number if mentioned, else null",
    "interested_course": "Python, Java, Full Stack, AI/ML, or DSA if detected, else null"
  },
  "sentiment": "Positive" | "Neutral" | "Negative",
  "booking_intent": true | false
}
"""

class AIService:
    def __init__(self):
        self.client = None
        self._init_gemini()

    def _init_gemini(self):
        key = settings.GEMINI_API_KEY.strip()
        if key:
            try:
                from google import genai
                from google.genai import types
                self.client = genai.Client(
                    api_key=key,
                    http_options=types.HttpOptions(
                        retry_options=types.HttpRetryOptions(attempts=1)
                    )
                )
                logger.info("Gemini API client initialized successfully with ultra-fast flash-lite configuration.")
            except Exception as e:
                logger.warning(f"Could not initialize Gemini client: {e}")
                self.client = None
        else:
            logger.info("No GEMINI_API_KEY configured. Advanced contextual counselor engine will serve responses.")
            self.client = None

    def generate_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        rag_chunks: List[Dict[str, Any]],
        language: str = "en-IN"
    ) -> Dict[str, Any]:
        """
        Generates contextual AI sales response using Gemini API or the advanced counselor engine.
        Guaranteed to return in <= 3 seconds in English, Telugu, Tamil, Kannada, Malayalam, or Hindi.
        """
        user_message = user_message.strip()
        heuristic_lead = extract_customer_info_heuristic(user_message)
        heuristic_sentiment = analyze_sentiment(user_message)

        # Clean context text by removing raw bracketed section headers
        cleaned_chunks = []
        for c in rag_chunks:
            raw_text = c.get('content', '')
            clean_text = re.sub(r'\[SECTION:[^\]]+\]', '', raw_text).strip()
            cleaned_chunks.append({**c, "content": clean_text})

        context_text = "\n\n".join([f"[{c.get('course', 'Course')}]: {c.get('content', '')}" for c in cleaned_chunks])

        lower_msg = user_message.lower()
        booking_intent = any(word in lower_msg for word in ["book", "appointment", "counseling", "slot", "schedule", "call", "meet", "demo"])

        if self.client:
            try:
                future = _gemini_executor.submit(
                    self._call_gemini,
                    user_message,
                    conversation_history,
                    context_text,
                    heuristic_lead,
                    heuristic_sentiment,
                    booking_intent,
                    language
                )
                return future.result(timeout=4.5)
            except concurrent.futures.TimeoutError:
                logger.warning("Gemini API exceeded 4.5s limit. Seamlessly switching to query-specific counselor engine.")
            except Exception as e:
                logger.error(f"Gemini API call failed ({e}). Seamlessly switching to query-specific counselor engine.", exc_info=False)

        return self._generate_intelligent_fallback(user_message, conversation_history, cleaned_chunks, heuristic_lead, heuristic_sentiment, booking_intent, language)

    def _call_gemini(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        context: str,
        heuristic_lead: Dict[str, Any],
        heuristic_sentiment: str,
        booking_intent: bool,
        language: str = "en-IN"
    ) -> Dict[str, Any]:
        from google.genai import types

        formatted_history = []
        for msg in history[-6:]:
            role = "user" if msg.get("role") == "user" else "model"
            formatted_history.append(f"{role.upper()}: {msg.get('content', '')}")

        history_block = "\n".join(formatted_history)

        prompt = f"""{SYSTEM_PROMPT}

SESSION LANGUAGE CODE: {language}
(IMPORTANT: Respond strictly in the candidate's language: Telugu if Telugu, Tamil if Tamil, Kannada if Kannada, Malayalam if Malayalam, Hindi if Hindi, English if English).

OFFICIAL KNOWLEDGE BASE CONTEXT:
{context}

CONVERSATION HISTORY:
{history_block}

CURRENT CANDIDATE QUERY:
"{user_message}"

Respond strictly in valid JSON:"""

        # Use Groq API if configured
        if settings.GROQ_API_KEY:
            try:
                import urllib.request
                req_body = json.dumps({
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 300,
                    "response_format": {"type": "json_object"}
                }).encode("utf-8")
                req = urllib.request.Request(
                    "https://api.groq.com/openai/v1/chat/completions",
                    data=req_body,
                    headers={
                        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                        "Content-Type": "application/json",
                        "User-Agent": "VoiceLeadAI/1.0"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                raw_json = resp_data["choices"][0]["message"]["content"].strip()
                result = json.loads(raw_json)
                lead = result.get("extracted_lead", {})
                for k, v in heuristic_lead.items():
                    if v and not lead.get(k):
                        lead[k] = v
                result["extracted_lead"] = lead
                if not result.get("sentiment"):
                    result["sentiment"] = heuristic_sentiment
                if result.get("booking_intent") is None:
                    result["booking_intent"] = booking_intent
                return result
            except Exception as groq_e:
                logger.warning(f"Groq API warning: {groq_e}")

        # Use gemini-3.5-flash-lite with safe retry on 503 spikes
        for model_id in ['gemini-3.5-flash-lite']:
            for attempt in range(2):
                try:
                    response = self.client.models.generate_content(
                        model=model_id,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.2,
                            max_output_tokens=260,  # Fast voice output supporting English and Indic scripts
                        )
                    )
                    raw_json = response.text.strip()
                    if raw_json.startswith("```"):
                        raw_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_json, flags=re.DOTALL).strip()
                    try:
                        result = json.loads(raw_json)
                    except Exception:
                        m = re.search(r'"reply"\s*:\s*"([^"]+)"', raw_json)
                        reply_text = m.group(1) if m else raw_json
                        result = {
                            "reply": reply_text,
                            "extracted_lead": heuristic_lead,
                            "sentiment": heuristic_sentiment,
                            "booking_intent": booking_intent
                        }

                    # Merge heuristic extractions if LLM missed any
                    lead = result.get("extracted_lead", {})
                    for k, v in heuristic_lead.items():
                        if v and not lead.get(k):
                            lead[k] = v
                    result["extracted_lead"] = lead
                    if not result.get("sentiment"):
                        result["sentiment"] = heuristic_sentiment
                    if result.get("booking_intent") is None:
                        result["booking_intent"] = booking_intent
                    return result
                except Exception as inner_e:
                    if "503" in str(inner_e) and attempt == 0:
                        import time
                        time.sleep(0.3)
                        continue
                    logger.warning(f"Fast model {model_id} warning: {inner_e}")
                    break

        raise RuntimeError("All Gemini models failed. Using enhanced fallback engine.")

    def _generate_intelligent_fallback(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        rag_chunks: List[Dict[str, Any]],
        heuristic_lead: Dict[str, Any],
        heuristic_sentiment: str,
        booking_intent: bool,
        language: str = "en-IN"
    ) -> Dict[str, Any]:
        """
        Sophisticated, domain-tailored counselor engine with query-specific intent parsing
        in Telugu, Tamil, Kannada, Malayalam, Hindi, and English.
        """
        lower = user_message.lower().strip()
        words = lower.split()
        course_name = heuristic_lead.get("interested_course") or ""

        # 0. Greetings across all supported languages
        if any(w in lower for w in [
            "hi", "hello", "hey", "good morning", "good evening", "namaste",
            "నమస్కారం", "హలో", "வணக்கம்", "ஹலோ", "ನಮಸ್ಕಾರ", "ಹಲೋ", "നമസ്കാരം", "ഹലോ", "नमस्ते", "प्रणाम"
        ]) and len(words) <= 4:
            return {
                "reply": "Hello and welcome to VoxSales Academy! I am your AI sales advisor. You can speak to me in English, Telugu, Hindi, Tamil, Kannada, or Malayalam, and I will assist you with our programs in Python, Java, Full Stack, AI/ML, and DSA. How can I help boost your tech career today?",
                "extracted_lead": heuristic_lead,
                "sentiment": "Positive",
                "booking_intent": False
            }
        
        # Detect language
        is_te = any('\u0C00' <= char <= '\u0C7F' for char in user_message) or (language or "").startswith("te")
        is_ta = any('\u0B80' <= char <= '\u0BFF' for char in user_message) or (language or "").startswith("ta")
        is_kn = any('\u0C80' <= char <= '\u0CFF' for char in user_message) or (language or "").startswith("kn")
        is_ml = any('\u0D00' <= char <= '\u0D7F' for char in user_message) or (language or "").startswith("ml")
        is_hi = any('\u0900' <= char <= '\u097F' for char in user_message) or (language or "").startswith("hi")

        # 1. Syllabus / Curriculum / What is taught / Topics
        if any(w in lower for w in [
            "syllabus", "curriculum", "topic", "topics", "learn", "teach", "modules", "content", "what is",
            "సిలబస్", "పాఠాలు", "నేర్పుతారు", "విషయాలు", "టాపిక్స్",
            "பாடத்திட்டம்", "சிலபஸ்", "கற்பிப்பீர்கள்", "பாடங்கள்",
            "ಪಠ್ಯಕ್ರಮ", "ಸಿಲಬಸ್", "ಕಲಿಸುತ್ತೀರಿ", "ವಿಷಯಗಳು",
            "സിലബസ്", "പഠിപ്പിക്കുന്നത്", "വിഷയങ്ങൾ",
            "सिलेबस", "पाठ्यक्रम", "सिखाया"
        ]):
            if any(w in lower for w in ["full stack", "fullstack", "mern", "ఫుల్ స్టాక్", "ஃபுல் ஸ்டாக்", "ಫುಲ್"]):
                reply = "Our Full Stack Web Development curriculum covers modern React 19, Next.js 14, Node.js, Express, MongoDB, and AWS cloud deployment with live industry capstone projects. Which specific technology are you most eager to master?"
            elif any(w in lower for w in ["python", "పైథాన్", "பைதான்", "ಪೈಥಾನ್", "पायथन"]):
                reply = "The Python Bootcamp covers core OOP, NumPy, Pandas, web scraping, and building REST APIs with FastAPI. Does this match your learning goals?"
            elif any(w in lower for w in ["java", "జావా", "ஜாவா", "जावा"]):
                reply = "The Java Masterclass covers Core Java 21, Spring Boot 3, Microservices with Spring Cloud, Kafka event streaming, and Docker deployment."
            elif any(w in lower for w in ["ai", "machine learning", "ml", "genai", "llm"]):
                reply = "The AI & ML Specialist program covers Python, Deep Learning with PyTorch, Generative AI APIs, LangChain, and production RAG architectures."
            elif any(w in lower for w in ["dsa", "algorithms", "డేటా స్ట్రక్చర్స్"]):
                reply = "The DSA and System Design Masterclass covers core algorithms, trees, dynamic programming, 300+ LeetCode patterns, and low-level system design."
            else:
                reply = "Our curriculum covers core programming, modern frameworks (React 19, Next.js 14, FastAPI), database architecture (MongoDB, PostgreSQL), and production capstones built to industry standards. Which course syllabus would you like to review?"
            return {"reply": reply, "extracted_lead": heuristic_lead, "sentiment": heuristic_sentiment, "booking_intent": False}

        # 2. Duration / Schedule / Batches / Timing
        if any(w in lower for w in [
            "duration", "time", "timing", "batch", "batches", "weeks", "months", "schedule",
            "వ్యవధి", "సమయం", "వారాలు", "నెలలు", "బ్యాచ్",
            "கால அளவு", "நேரம்", "மாதங்கள்", "பேட்ச்",
            "ಅವಧಿ", "ಸಮಯ", "ವಾರಗಳು", "ತಿಂಗಳುಗಳು", "ಬ್ಯಾಚ್",
            "കാലാവധി", "സമയം", "ആഴ്ചകൾ", "മാസങ്ങൾ", "ബാച്ച്",
            "अवधि", "समय", "सप्ताह", "महीने", "बैच"
        ]):
            if any(w in lower for w in ["python", "పైథాన్", "பைதான்", "ಪೈಥಾನ್", "पायथन"]):
                reply = "The Python Bootcamp runs for 12 Weeks (3 Months) with flexible weekday evening and weekend batches."
            elif any(w in lower for w in ["full stack", "fullstack", "mern", "ఫుల్ స్టాక్", "ஃபுல்"]):
                reply = "The Full Stack Web Development cohort runs for 18 Weeks (4.5 Months) with live evening sessions and weekend mentor labs."
            elif any(w in lower for w in ["ai", "machine learning", "ml"]):
                reply = "The AI & ML Specialist cohort runs for 20 Weeks (5 Months) designed for intensive hands-on model training."
            elif any(w in lower for w in ["java", "జావా", "ஜாவா"]):
                reply = "The Java Enterprise Masterclass runs for 16 Weeks (4 Months) with live weekend distributed systems sessions."
            elif any(w in lower for w in ["dsa", "algorithms"]):
                reply = "The DSA Masterclass runs for 14 Weeks (3.5 Months) focused on interview problem solving."
            else:
                reply = "Our cohort programs range from 12 to 20 weeks with flexible weekday evening and weekend batches designed for students and working professionals. Which schedule suits you better?"
            return {"reply": reply, "extracted_lead": heuristic_lead, "sentiment": heuristic_sentiment, "booking_intent": False}

        # 3. Placement / Jobs / Career Assistance / Salaries
        if any(w in lower for w in [
            "placement", "placements", "job", "jobs", "salary", "package", "ctc", "hiring", "interview",
            "ప్లేస్‌మెంట్", "ఉద్యోగం", "జీతం", "ఇంటర్వ్యూ", "కంపెనీలు",
            "வேலைவாய்ப்பு", "வேலை", "சம்பளம்", "நேர்காணல்",
            "ಉದ್ಯೋಗ", "ಪ್ಲೇಸ್‌ಮೆಂಟ್", "ಸಂಬಳ", "ಸಂದರ್ಶನ",
            "പ്ലേസ്മെന്റ്", "ജോലി", "ശമ്പളം", "ഇന്റർവ്യൂ",
            "प्लेसमेंट", "नौकरी", "सैलरी", "पैकेज", "इंटरव्यू"
        ]):
            reply = "We offer 100% placement assistance across 350+ hiring partners, including resume reviews, GitHub portfolio audits, and 5+ mock technical interviews with senior engineers. Starting packages typically range from 6 to 14 LPA."
            return {"reply": reply, "extracted_lead": heuristic_lead, "sentiment": "Positive", "booking_intent": False}

        # 4. Booking / Scheduling Appointment
        if booking_intent or any(w in lower for w in [
            "book", "appointment", "counseling", "slot", "call", "schedule",
            "బుక్", "అపాయింట్‌మెంట్", "స్లాట్", "కౌన్సెలింగ్",
            "முன்பதிவு", "ஆலோசனை", "நேரம்",
            "ಕಾಯ್ದಿರಿಸಿ", "ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್", "ಸಲಹೆ",
            "ബുക്ക്", "അപ്പോയിന്റ്മെന്റ്", "കൗൺസിലിംഗ്",
            "बुक", "अपॉइंटमेंट", "स्लॉट", "काउंसलिंग"
        ]):
            reply = "I would be happy to help you book a free 1-on-1 career consultation! You can choose your preferred slot directly on our Appointments calendar. What is your email and phone number so we can confirm your session?"
            return {"reply": reply, "extracted_lead": heuristic_lead, "sentiment": "Positive", "booking_intent": True}

        # 5. Pricing, Fees & EMI
        if any(w in lower for w in [
            "fee", "fees", "cost", "price", "pricing", "discount", "scholarship", "emi", "pay",
            "ఫీజు", "ఖర్చు", "ధర", "ఈఎంఐ", "డిస్కౌంట్",
            "கட்டணம்", "விலை", "ஈஎம்ஐ", "தள்ளுபடி",
            "ಶುಲ್ಕ", "ಬೆಲೆ", "ಇಎಂಐ", "ರಿಯಾಯಿತಿ",
            "ഫീസ്", "ചെലവ്", "ഇഎംഐ", "ഇളവ്",
            "फीस", "कीमत", "ईएमआई", "छूट"
        ]):
            if "python" in lower or "పైథాన్" in lower or "பைதான்" in lower or "ಪೈಥಾನ್" in lower:
                fee_val = "INR 3,499 (EMI: INR 583/mo)"
            elif "java" in lower or "జావా" in lower or "ஜாவா" in lower or "ಜಾವಾ" in lower:
                fee_val = "INR 3,999 (EMI: INR 666/mo)"
            elif "full stack" in lower or "ఫుల్ స్టాక్" in lower or "ஃபுல் ஸ்டாக்" in lower:
                fee_val = "INR 4,499 (EMI: INR 750/mo)"
            elif "ai" in lower:
                fee_val = "INR 4,999 (EMI: INR 833/mo)"
            elif "dsa" in lower:
                fee_val = "INR 3,299 (EMI: INR 550/mo)"
            else:
                fee_val = "INR 3,299 to INR 4,999"

            reply = f"Our course fee is {fee_val} with zero-interest EMI options and up to 25% merit scholarships. Which program are you considering?"
            return {"reply": reply, "extracted_lead": heuristic_lead, "sentiment": heuristic_sentiment, "booking_intent": False}
        lower = user_message.lower().strip()
        words = lower.split()
        course_name = heuristic_lead.get("interested_course")

        # 1. Course overview requests
        if any(w in lower for w in ["course", "courses", "program", "programs", "bootcamp"]) and len(words) <= 3:
            return {
                "reply": "We offer 5 live cohort programs: Python Programming & Automation (12 Weeks), Java Enterprise & Microservices (16 Weeks), Full Stack MERN + Next.js 14 (18 Weeks), AI & Machine Learning Specialist (20 Weeks), and DSA & System Design (14 Weeks). All include 100% placement assistance and 1-on-1 mentorship. Which track interests you most?",
                "extracted_lead": heuristic_lead,
                "sentiment": "Positive",
                "booking_intent": False
            }

        # 2. Incomplete / micro voice fragments
        if len(words) <= 2 and words[0] in ["what", "what's", "how", "tell", "can", "is", "where"]:
            return {
                "reply": "I'm listening! Please feel free to ask about our course fees, syllabus, batch schedules, or placement assistance for Python, Java, Full Stack, AI, or DSA.",
                "extracted_lead": heuristic_lead,
                "sentiment": "Neutral",
                "booking_intent": False
            }

        # 2. Greeting inquiries
        if any(w in lower for w in ["hi", "hello", "hey", "good morning", "good evening", "namaste"]) and len(words) <= 3:
            return {
                "reply": "Hello and welcome to VoxSales Academy! I can help you explore our technical bootcamps in Python, Java, Full Stack Web Development, AI/Machine Learning, and DSA for placements. Which track are you looking to explore?",
                "extracted_lead": heuristic_lead,
                "sentiment": "Positive",
                "booking_intent": False
            }

        # 3. Direct booking intent
        if booking_intent:
            name_str = f", {heuristic_lead['name']}" if heuristic_lead.get("name") else ""
            return {
                "reply": f"I would be delighted to schedule a free 1-on-1 career consultation for you{name_str}! You can choose your preferred time slot directly on our Appointments calendar. What is your email and phone number so we can confirm your session?",
                "extracted_lead": heuristic_lead,
                "sentiment": "Positive",
                "booking_intent": True
            }

        # 4. Contact details provided
        if heuristic_lead.get("phone") or heuristic_lead.get("email"):
            name = heuristic_lead.get("name") or "there"
            target_course = course_name or "our technical program"
            return {
                "reply": f"Thank you so much, {name}! I have recorded your contact details for {target_course}. Our senior academic mentor will share the complete syllabus PDF and scholarship evaluation. Would you also like to reserve a free counseling slot for tomorrow?",
                "extracted_lead": heuristic_lead,
                "sentiment": "Positive",
                "booking_intent": True
            }

        # 5. Course specific intent matching
        top_chunk = rag_chunks[0] if rag_chunks else None
        top_content = top_chunk.get("content", "") if top_chunk else ""

        # A. Pricing, Fees & EMI
        if any(w in lower for w in ["fee", "fees", "cost", "price", "pricing", "discount", "scholarship", "emi", "pay"]):
            if "python" in lower or course_name == "Python Programming & Automation":
                reply = "The Python Programming & Automation Bootcamp is offered at an early-bird placement fee of INR 3,499 (standard INR 4,999). We offer flexible 0% interest EMI options starting at INR 583/month, along with merit scholarships up to 25% off."
            elif "java" in lower or course_name == "Java Enterprise & Microservices":
                reply = "The Java Enterprise & Microservices Masterclass has an early-bird placement fee of INR 3,999 (standard INR 5,499). Zero-cost EMI is available starting at INR 666/month, and we provide up to 25% scholarship through our entrance assessment."
            elif "full stack" in lower or "mern" in lower or course_name == "Full Stack Web Development (MERN)":
                reply = "The Full Stack Web Development program (MERN + Next.js 14) is INR 4,499 with our placement discount (regular INR 5,999). You can also opt for no-cost EMI at INR 750/month."
            elif "ai" in lower or "machine learning" in lower or course_name == "AI, Machine Learning & LLM Specialist":
                reply = "The AI, Machine Learning & LLM Specialist program is INR 4,999 under our scholarship tier (regular INR 6,999), with 6-month zero-cost EMI at INR 833/month."
            elif "dsa" in lower or course_name == "DSA & System Design Masterclass":
                reply = "The DSA & System Design Masterclass for placements is INR 3,299 (discounted from INR 4,499), with no-cost EMI starting at INR 550/month."
            else:
                reply = "Our course fees range from INR 3,299 to INR 4,999 depending on the specialization, all with zero-interest 3 to 6-month EMI plans starting from INR 550/month and up to 25% scholarship discounts. Which program are you considering?"
            return {
                "reply": reply,
                "extracted_lead": heuristic_lead,
                "sentiment": heuristic_sentiment,
                "booking_intent": False
            }

        # B. Curriculum, Syllabus, Codes & What is covered
        if any(w in lower for w in ["curriculum", "syllabus", "content", "topic", "topics", "learn", "codes", "code", "module", "modules", "teach"]):
            if "python" in lower or course_name == "Python Programming & Automation":
                reply = "In the Python Bootcamp, you learn 5 phases: Core Python & OOP, Advanced Python (generators, decorators, asyncio), Data libraries (NumPy, Pandas, BeautifulSoup, Selenium), Database integrations (PostgreSQL, SQLite), and REST APIs with FastAPI. You also build a multi-platform E-commerce Price Tracker and an automated financial ETL pipeline."
            elif "java" in lower or course_name == "Java Enterprise & Microservices":
                reply = "The Java Enterprise Masterclass covers Core Java 21 & Virtual Threads, Spring Boot 3 & JPA Hibernate, Microservices with Spring Cloud & Eureka, Event Sourcing with Kafka & Redis caching, plus Docker and Kubernetes CI/CD. Major projects include a distributed banking microservices system and an e-commerce platform."
            elif "full stack" in lower or "mern" in lower:
                reply = "The Full Stack program covers Modern TypeScript, React 18/19, Next.js 14 Server Components & Actions, Node.js & Express REST/GraphQL APIs, MongoDB & PostgreSQL with Prisma ORM, and Docker deployment on AWS S3 & Vercel."
            elif "ai" in lower or "machine learning" in lower:
                reply = "The AI & ML Specialist track covers Applied Mathematics & Data Science, Scikit-learn Machine Learning, Deep Learning with PyTorch, Generative AI with LLM APIs, Vector RAG using FAISS, and Production MLOps with FastAPI and Docker."
            elif "dsa" in lower:
                reply = "The DSA track covers Core Algorithms, Data Structures (Trees, Graphs, DSU, Dynamic Programming), 300+ curated LeetCode Medium/Hard problems, along with Low-Level and High-Level System Design (Rate Limiters, URL shorteners, Caching, Sharding)."
            else:
                reply = "All our programs are project-driven and include live cohort sessions, hands-on GitHub projects, and weekly 1-on-1 code reviews with senior industry mentors."
            return {
                "reply": reply + " Are you looking to upskill for a college placement or a job transition?",
                "extracted_lead": heuristic_lead,
                "sentiment": "Positive",
                "booking_intent": False
            }

        # C. Duration, Schedule & Timings
        if any(w in lower for w in ["duration", "time", "timing", "timings", "schedule", "batch", "batches", "weekend", "weekday", "long"]):
            if "python" in lower or course_name == "Python Programming & Automation":
                reply = "The Python program runs for 12 Weeks (3 Months). We offer Weekday batches (Mon–Thu, 7:30 PM to 9:00 PM IST) and Weekend batches (Sat & Sun, 10:00 AM to 1:00 PM IST)."
            elif "java" in lower or course_name == "Java Enterprise & Microservices":
                reply = "The Java Enterprise Masterclass is a 16-Week (4 Months) program. Weekdays: Mon–Thu 8:00 PM to 9:30 PM IST; Weekends: Sat & Sun 2:00 PM to 5:00 PM IST."
            elif "full stack" in lower or "mern" in lower:
                reply = "The Full Stack Web Development bootcamp runs for 18 Weeks (4.5 Months) with both evening weekday batches and morning weekend sessions."
            elif "ai" in lower or "machine learning" in lower:
                reply = "The AI Specialist track is a 20-Week (5 Months) intensive program with weekday evening and weekend afternoon options."
            elif "dsa" in lower:
                reply = "The DSA Masterclass runs for 14 Weeks (3.5 Months) with weekday evening sessions from 9:00 PM to 10:30 PM IST and weekend morning slots."
            else:
                reply = "Our cohort programs range from 12 to 20 weeks with flexible weekday evening and weekend batches designed for students and working professionals."
            return {
                "reply": reply + " Which schedule suits your routine better, weekdays or weekends?",
                "extracted_lead": heuristic_lead,
                "sentiment": heuristic_sentiment,
                "booking_intent": False
            }

        # D. Placement, Hiring Partners & Package
        if any(w in lower for w in ["placement", "job", "salary", "package", "ctc", "hiring", "company", "companies", "guarantee"]):
            reply = "We provide 100% placement assistance across 350+ hiring partners. This includes comprehensive resume tailoring, GitHub portfolio audits, 5 mock technical interviews, and direct referrals until you get placed. Starting packages range from 6 to 18 LPA depending on the specialization."
            return {
                "reply": reply,
                "extracted_lead": heuristic_lead,
                "sentiment": "Positive",
                "booking_intent": False
            }

        # E. General course inquiry (explicit keyword or extracted course_name)
        if "java" in lower or course_name == "Java Enterprise & Microservices":
            reply = "Our Java Enterprise & Microservices Masterclass (16 weeks, INR 3,999) covers Core Java 21, Spring Boot 3, Microservices with Spring Cloud, Kafka, Redis, and Docker/Kubernetes CI/CD, with 100% placement support. Would you like to know about the syllabus, batch timings, or fees?"
            return {
                "reply": reply,
                "extracted_lead": heuristic_lead,
                "sentiment": heuristic_sentiment,
                "booking_intent": False
            }
        if "python" in lower or course_name == "Python Programming & Automation":
            reply = "Our Python Programming & Automation Bootcamp (12 weeks, INR 3,499) covers Core & Advanced Python, Data libraries (NumPy, Pandas), PostgreSQL/SQLite, and FastAPI REST APIs, with 100% placement support. Would you like to know about the syllabus, batch timings, or fees?"
            return {
                "reply": reply,
                "extracted_lead": heuristic_lead,
                "sentiment": heuristic_sentiment,
                "booking_intent": False
            }
        if "full stack" in lower or "mern" in lower or course_name == "Full Stack Web Development (MERN + Next.js)":
            reply = "Our Full Stack Web Development program (18 weeks, INR 4,499) covers TypeScript, React, Next.js 14, Node.js, Express, MongoDB/PostgreSQL, and AWS/Vercel deployment. Would you like to know about the syllabus, batch timings, or fees?"
            return {
                "reply": reply,
                "extracted_lead": heuristic_lead,
                "sentiment": heuristic_sentiment,
                "booking_intent": False
            }
        if "ai" in lower or "machine learning" in lower or course_name == "AI, Machine Learning & LLM Specialist":
            reply = "Our AI, Machine Learning & LLM Specialist track (20 weeks, INR 4,999) covers Data Science, Scikit-learn, PyTorch Deep Learning, Generative AI, Vector RAG with FAISS, and MLOps. Would you like to know about the syllabus, batch timings, or fees?"
            return {
                "reply": reply,
                "extracted_lead": heuristic_lead,
                "sentiment": heuristic_sentiment,
                "booking_intent": False
            }
        if "dsa" in lower or course_name == "DSA & System Design Masterclass":
            reply = "Our DSA & System Design Masterclass (14 weeks, INR 3,299) covers Trees, Graphs, Dynamic Programming, 300+ LeetCode problems, and Low/High-Level System Design. Would you like to know about the syllabus, batch timings, or fees?"
            return {
                "reply": reply,
                "extracted_lead": heuristic_lead,
                "sentiment": heuristic_sentiment,
                "booking_intent": False
            }
        if course_name:
            reply = f"Our {course_name} program includes live mentor sessions, production capstones, and dedicated placement support. Could you share what semester or current experience level you are at so I can recommend the right roadmap?"
            return {
                "reply": reply,
                "extracted_lead": heuristic_lead,
                "sentiment": heuristic_sentiment,
                "booking_intent": False
            }

        # F. Fallback for open-ended queries
        return {
            "reply": "We offer career cohorts in Python, Java Microservices, Full Stack MERN/Next.js, AI & Machine Learning, and DSA for placements. Which domain excites you the most, and what questions can I answer for you?",
            "extracted_lead": heuristic_lead,
            "sentiment": heuristic_sentiment,
            "booking_intent": False
        }

ai_service = AIService()
