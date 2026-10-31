import os
import re
import requests
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

APP_DIR = Path(__file__).parent
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

app = FastAPI(
    title="OFSS AI Blog Writer",
    version="1.1.0",
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

def clean_html_output(text: str) -> str:
    """Remove common Markdown fences without escaping real HTML tags."""
    article = (text or "").strip()
    article = re.sub(r"^\s*```(?:html|HTML)?\s*", "", article)
    article = re.sub(r"\s*```\s*$", "", article)
    # Remove accidental leading explanation before the first HTML element.
    first_tag = re.search(r"<(?:article|div|h1|p)\b", article, flags=re.IGNORECASE)
    if first_tag:
        article = article[first_tag.start():]
    return article.strip()

@app.post("/api/generate")
def generate_blog(data: BlogRequest):
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY set nahi hai. Render ke Environment settings mein API key add karein."
        )

    example = data.example_article.strip() or "कोई example article नहीं दिया गया है। सरल, स्वाभाविक, बातचीत वाली हिंदी में लिखें।"
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

EXTRA FACTS:
{facts}

VERIFIED SOURCES:
{sources}

EXAMPLE ARTICLE FOR STYLE ANALYSIS:
<example_article>
{example}
</example_article>

STYLE RULES:
- Example को केवल भाषा, टोन, वाक्य की सहजता, पैराग्राफ की लंबाई, पाठक को संबोधित करने के तरीके और heading structure समझने के लिए इस्तेमाल करें।
- बिहार के पाठकों के लिए स्वाभाविक, आसान, अपनापन वाली हिंदी लिखें।
- छोटे मोबाइल-फ्रेंडली पैराग्राफ, स्पष्ट H2/H3 headings, उपयोगी lists और जरूरत पड़ने पर overview table रखें।
- Example के वाक्य या पूरे पैराग्राफ कॉपी न करें। नया लेख मौलिक और विषय के अनुसार लिखें।
- सामान्य प्रचलित English terms जरूरत के अनुसार रखें।

FACTUAL ACCURACY:
- कोई तारीख, फीस, हेल्पलाइन नंबर, vacancy, link, login method, eligibility, सरकारी घोषणा या correction deadline गढ़कर न लिखें।
- Extra facts और verified sources को प्राथमिकता दें।
- अगर कोई जरूरी तथ्य उपलब्ध नहीं है, तो साफ लिखें कि आधिकारिक नोटिस से पुष्टि करनी होगी।
- Official website का direct link केवल तभी दें जब user ने दिया हो या verified sources में मौजूद हो।
- AdSense approval, traffic या AI detector score की guarantee न दें।
- SEO keyword स्वाभाविक रूप से उपयोग करें।

OUTPUT RULES:
- सिर्फ HTML दें। Markdown code fences (```), Markdown headings या HTML कोड के बाहर की व्याख्या न दें।
- Output को <article>...</article> के अंदर रखें।
- SEO Meta Title और Meta Description को <div class="seo-meta"> में रखें, उसके बाद <article> दें।
- Semantic HTML इस्तेमाल करें: h1, h2, h3, p, ul, ol, table, strong, em.
- HTML tags को text के रूप में escape न करें। सही HTML markup लौटाएं।
- Inline scripts या styles न जोड़ें।
- WordPress में paste करने योग्य clean HTML दें।
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
                    "temperature": 0.7,
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
        candidate = payload["candidates"][0]
        parts = candidate["content"]["parts"]
        article = "\n".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
    except (KeyError, IndexError, TypeError):
        raise HTTPException(status_code=502, detail="AI se response mila, lekin article text read nahi ho paya. Dobara try karein.")

    article = clean_html_output(article)
    if not article:
        raise HTTPException(status_code=502, detail="AI ne khaali article diya. Dobara try karein.")

    return {"article_html": article, "model": GEMINI_MODEL}
