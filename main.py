import os
import html
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path

APP_DIR = Path(__file__).parent
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()

app = FastAPI(
    title="OFSS AI Blog Writer",
    version="1.0.0",
    description="Generate useful, WordPress-ready blog posts in a natural Bihar-style Hindi tone."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BlogRequest(BaseModel):
    keyword: str = Field(min_length=2, max_length=300)
    example_article: str = Field(default="", max_length=30000)
    article_type: str = Field(default="Bihar Board / Admission / Result / Scholarship / Jobs", max_length=150)
    language: str = Field(default="Hindi - Bihar conversational tone", max_length=100)
    word_count: int = Field(default=1500, ge=500, le=5000)
    extra_facts: str = Field(default="", max_length=12000)
    verified_sources: str = Field(default="", max_length=5000)

@app.get("/", response_class=HTMLResponse)
def home():
    path = APP_DIR / "index.html"
    if not path.exists():
        return HTMLResponse("<h1>OFSS AI Blog Writer</h1><p>index.html file is missing.</p>", status_code=500)
    return HTMLResponse(path.read_text(encoding="utf-8"))

@app.get("/api/health")
def health():
    return {
        "service": "OFSS AI Blog Writer",
        "status": "ok",
        "api_key_configured": bool(GEMINI_API_KEY),
        "model": GEMINI_MODEL
    }

@app.post("/api/generate")
def generate_blog(data: BlogRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY set nahi hai. Render ke Environment settings mein API key add karein."
        )

    example = data.example_article.strip() or (
        "कोई example article नहीं दिया गया है। सरल, स्वाभाविक, बातचीत वाली हिंदी में लिखें।"
    )
    facts = data.extra_facts.strip() or "कोई अतिरिक्त तथ्य नहीं दिए गए।"
    sources = data.verified_sources.strip() or "कोई verified source/official notice नहीं दिया गया।"

    prompt = f"""
आप OFSS Bihar Board वेबसाइट के लिए एक अनुभवी हिंदी ब्लॉग लेखक और संपादक हैं।

USER KEYWORD:
{data.keyword}

ARTICLE TYPE:
{data.article_type}

LANGUAGE / STYLE:
{data.language}

TARGET LENGTH:
लगभग {data.word_count} शब्द। जरूरत हो तो स्पष्टता को शब्द संख्या से अधिक महत्व दें।

EXAMPLE ARTICLE FOR STYLE ANALYSIS:
<example_article>
{example}
</example_article>

STYLE RULES:
- Example को केवल भाषा, टोन, वाक्य की सहजता, पैराग्राफ की लंबाई, पाठक को संबोधित करने के तरीके और heading structure समझने के लिए इस्तेमाल करें।
- बिहार के पाठकों के लिए स्वाभाविक, आसान, अपनापन वाली हिंदी लिखें। जरूरत के अनुसार “भाई-बहन”, “देखिए”, “चलिए समझते हैं”, “घबराइए मत” जैसे वाक्य कभी-कभी इस्तेमाल कर सकते हैं; हर पैराग्राफ में नहीं।
- सामान्य प्रचलित English terms जैसे Online Apply, Download Link, Last Date, Correction, Registration Number को जरूरत के अनुसार रखें।
- भाषा देसी और बातचीत जैसी हो, लेकिन जबरदस्ती की बोली, नकली उच्चारण, अपमानजनक शब्द या जरूरत से ज्यादा slang न डालें।
- छोटे मोबाइल-फ्रेंडली पैराग्राफ, स्पष्ट H2/H3 headings, उपयोगी lists और जरूरत पड़ने पर overview table रखें।
- Example के वाक्य या पूरे पैराग्राफ कॉपी न करें। नया लेख मौलिक और विषय के अनुसार लिखें।
- AI detector के 0% score की गारंटी या detector को धोखा देने के निर्देश न अपनाएं। लक्ष्य स्वाभाविक, उपयोगी, तथ्य-आधारित लेख है।

FACTUAL ACCURACY RULES:
- कोई तारीख, फीस, हेल्पलाइन नंबर, vacancy, link, login method, eligibility, सरकारी घोषणा या correction deadline गढ़कर न लिखें।
- Extra facts और verified sources को प्राथमिकता दें।
- अगर कोई जरूरी तथ्य उपलब्ध नहीं है, तो स्पष्ट लिखें कि आधिकारिक नोटिस से पुष्टि करनी होगी। अनुमान को तथ्य की तरह न दिखाएं।
- Official website का direct link केवल तभी दें जब user ने दिया हो या verified sources में मौजूद हो। अनुमान से URL न बनाएं।
- किसी घटना या घोषणा को “Out Now”, “जारी हो गया” या “आज से शुरू” तभी कहें जब दिए गए verified sources से पुष्टि होती हो। नहीं तो शीर्षक/लेख में इसे confirmed न बताएं।
- तारीखें current होने का दावा बिना प्रमाण न करें।
- SEO keyword स्वाभाविक रूप से उपयोग करें; keyword stuffing न करें।
- AdSense approval, Google Discover traffic या AI detector score की guarantee न दें।
- लेख के अंत में छोटा editorial note तभी जोड़ें जब जरूरी तथ्यों की पुष्टि बाकी हो।

OUTPUT FORMAT:
सिर्फ पूरा HTML fragment दें, Markdown code fences नहीं।
- <article> के अंदर पूरा लेख रखें।
- शुरुआत में <h1> SEO title, फिर एक छोटा intro।
- उसके बाद <h2> headings, जरूरी होने पर <table>, <ol>/<ul>, FAQs और conclusion।
- SEO Meta Title और Meta Description को article के ऊपर छोटे <div class="seo-meta"> में अलग दिखाएं।
- WordPress Gutenberg में paste करने लायक clean HTML रखें। Inline scripts न लिखें।
- अगर facts अपर्याप्त हों तो झूठी निश्चितता के बजाय साफ caveat दें।
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    try:
        response = requests.post(
            url,
            headers={
                "x-goog-api-key": GEMINI_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.85,
                    "maxOutputTokens": 10000
                }
            },
            timeout=180,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"AI service se connection nahi ho paya: {str(exc)}")

    if response.status_code != 200:
        try:
            detail = response.json().get("error", {}).get("message", response.text)
        except Exception:
            detail = response.text
        raise HTTPException(status_code=502, detail=f"Gemini API error ({response.status_code}): {detail[:900]}")

    try:
        payload = response.json()
        parts = payload["candidates"][0]["content"]["parts"]
        article = "\n".join(part.get("text", "") for part in parts).strip()
    except (KeyError, IndexError, TypeError):
        raise HTTPException(status_code=502, detail="AI se response mila, lekin article text read nahi ho paya. Dobara try karein.")

    article = article.removeprefix("```html").removeprefix("```").removesuffix("```").strip()
    return {"article_html": article, "model": GEMINI_MODEL}
