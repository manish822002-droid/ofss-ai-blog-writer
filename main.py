
import os
import re
import time
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

APP_DIR = Path(__file__).parent

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL", "gemini-3.5-flash"
).strip()

GEMINI_TIMEOUT = 100
MAX_RETRIES = 1

app = FastAPI(
    title="OFSS AI Blog Writer",
    version="2.0.0",
    description="SEO-friendly Hindi and English blog article generator",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def home():
    index_file = APP_DIR / "index.html"

    if not index_file.exists():
        return JSONResponse(
            status_code=500,
            content={"detail": "index.html file not found"},
        )

    return FileResponse(index_file)


@app.get("/api/health")
async def health():
    return {
        "service": "OFSS AI Blog Writer",
        "status": "ok",
        "api_key_configured": bool(GEMINI_API_KEY),
        "model": GEMINI_MODEL,
    }


def clean_html(text):
    text = (text or "").strip()

    # Remove Markdown fences if the model adds them.
    text = re.sub(
        r"^\s*```(?:html)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*```\s*$", "", text)

    return text.strip()


def make_prompt(data):
    keyword = str(
        data.get("keyword")
        or data.get("topic")
        or data.get("title")
        or ""
    ).strip()

    language = str(data.get("language", "Hindi")).strip()
    tone = str(data.get("tone", "natural and conversational")).strip()

    raw_length = (
        data.get("word_count")
        or data.get("article_length")
        or data.get("length")
        or 1200
    )

    try:
        word_count = int(
            re.search(r"\d+", str(raw_length)).group()
        )
    except (AttributeError, ValueError):
        word_count = 1200

    word_count = max(400, min(word_count, 2500))

    if not keyword:
        raise HTTPException(
            status_code=400,
            detail="Please enter a keyword or article topic.",
        )

    hindi_rules = ""
    if language.lower() in ("hindi", "hi", "हिंदी"):
        hindi_rules = """
Write in simple, natural Hindi suitable for readers in Bihar.
Use conversational language, short mobile-friendly paragraphs,
and common English terms where people naturally use them.
Avoid robotic, repetitive, exaggerated or overly formal wording.
Address readers naturally when appropriate.
"""

    return f"""
You are the professional Hindi and English content writer
for OFSS Bihar Board, an independent educational information website.

Write a useful, original, SEO-friendly blog article.

ARTICLE TOPIC / PRIMARY KEYWORD:
{keyword}

LANGUAGE:
{language}

TARGET LENGTH:
Approximately {word_count} words.

WRITING STYLE:
{tone}

{hindi_rules}

IMPORTANT ACCURACY RULES:
- Never invent official dates, fees, links, notifications,
  eligibility rules, statistics or application procedures.
- Do not claim that unverified information is officially confirmed.
- If a detail cannot be verified from the supplied information,
  explain that readers should check the relevant official notice.
- Do not fabricate citations, sources or URLs.
- Clearly distinguish general guidance from confirmed facts.
- This website is independent and is not an official government website.

ARTICLE FORMAT:
Return a complete HTML fragment with this structure where relevant:

<div class="seo-meta">
  <p><strong>SEO Meta Title:</strong> ...</p>
  <p><strong>SEO Meta Description:</strong> ...</p>
</div>

<article>
  <h1>Clear, SEO-friendly article title</h1>
  <p>Helpful introduction answering the reader's main question.</p>

  <h2>Overview</h2>
  <table>
    <thead><tr><th>Details</th><th>Information</th></tr></thead>
    <tbody>...</tbody>
  </table>

  <h2>Important information</h2>
  <p>...</p>

  <h2>Eligibility or required documents</h2>
  <ul><li>...</li></ul>

  <h2>How to check or complete the process</h2>
  <ol><li>...</li></ol>

  <h2>Important instructions</h2>
  <ul><li>...</li></ul>

  <h2>Frequently Asked Questions (FAQs)</h2>
  <h3>Question?</h3>
  <p>Clear answer.</p>

  <h2>Conclusion</h2>
  <p>Practical summary and next steps.</p>
</article>

Adapt headings to the actual topic. Do not include irrelevant
sections just to fill space. Add 5-7 useful FAQs when appropriate.

HTML OUTPUT RULES:
- Return HTML only, not Markdown.
- Do not wrap the output in Markdown code fences.
- Do not include explanations outside the article.
- Use valid tags such as h1, h2, h3, p, ul, ol, li, table,
  thead, tbody, tr, th, td, strong and a.
- Do not add JavaScript, iframe, form tags or CSS.
- Do not invent internal or external links.
- Make the article readable on mobile.
- Keep SEO title and meta description concise.
"""


def call_gemini(prompt):
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail=(
                "GEMINI_API_KEY is missing in Render Environment. "
                "Add the key and redeploy."
            ),
        )

    model = GEMINI_MODEL.strip()

    if not model:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_MODEL is empty in Render Environment.",
        )

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{model}:generateContent"
    )

    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.5,
            "maxOutputTokens": 8192,
        },
    }

    last_error = "Unknown Gemini API error"

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=GEMINI_TIMEOUT,
            )

            if response.status_code == 200:
                try:
                    result = response.json()
                    candidates = result.get("candidates", [])

                    if not candidates:
                        raise HTTPException(
                            status_code=502,
                            detail=(
                                "Gemini returned no article. "
                                "Try a shorter article."
                            ),
                        )

                    parts = (
                        candidates[0]
                        .get("content", {})
                        .get("parts", [])
                    )

                    text = "".join(
                        part.get("text", "")
                        for part in parts
                        if isinstance(part, dict)
                    ).strip()

                    if not text:
                        raise HTTPException(
                            status_code=502,
                            detail=(
                                "Gemini returned empty text. "
                                "Please try again."
                            ),
                        )

                    return clean_html(text)

                except HTTPException:
                    raise
                except (ValueError, TypeError, KeyError, IndexError):
                    raise HTTPException(
                        status_code=502,
                        detail="Gemini returned an invalid response.",
                    )

            try:
                error_json = response.json()
                message = (
                    error_json.get("error", {}).get("message")
                    or response.text[:1000]
                )
            except ValueError:
                message = response.text[:1000]

            last_error = message

            if response.status_code in (429, 503):
                if attempt < MAX_RETRIES:
                    time.sleep(2)
                    continue

                raise HTTPException(
                    status_code=503,
                    detail=(
                        f"Gemini API is temporarily unavailable "
                        f"(HTTP {response.status_code}). "
                        f"Details: {message}. Please retry later."
                    ),
                )

            if response.status_code in (400, 401, 403, 404):
                raise HTTPException(
                    status_code=502,
                    detail=(
                        f"Gemini API error ({response.status_code}): "
                        f"{message}"
                    ),
                )

            raise HTTPException(
                status_code=502,
                detail=(
                    f"Gemini API error ({response.status_code}): "
                    f"{message}"
                ),
            )

        except requests.Timeout:
            last_error = "Gemini API request timed out."

            if attempt < MAX_RETRIES:
                continue

            raise HTTPException(
                status_code=504,
                detail=(
                    "Gemini took too long to respond. "
                    "Try again with a shorter article."
                ),
            )

        except requests.RequestException as exc:
            last_error = str(exc)

            if attempt < MAX_RETRIES:
                time.sleep(2)
                continue

            raise HTTPException(
                status_code=502,
                detail=(
                    "Could not connect to Gemini API. "
                    "Please try again later."
                ),
            )

    raise HTTPException(
        status_code=502,
        detail=f"Gemini request failed: {last_error}",
    )


@app.post("/api/generate")
async def generate_article(request: Request):
    try:
        content_type = request.headers.get("content-type", "")

        if "application/json" in content_type:
            data = await request.json()
        else:
            form = await request.form()
            data = dict(form)

        if not isinstance(data, dict):
            raise HTTPException(
                status_code=400,
                detail="Invalid request data.",
            )

        prompt = make_prompt(data)
        article_html = call_gemini(prompt)

        return {
            "article_html": article_html,
            "html": article_html,
            "model": GEMINI_MODEL,
        }

    except HTTPException:
        raise

    except Exception:
        # Avoid exposing secrets or internal server details.
        raise HTTPException(
            status_code=500,
            detail=(
                "Unexpected server error while generating the article. "
                "Check Render application logs."
            ),
        )
