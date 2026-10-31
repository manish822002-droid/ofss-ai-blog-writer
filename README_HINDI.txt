OFSS AI BLOG WRITER — SETUP GUIDE

Is folder mein:
- main.py: FastAPI backend
- index.html: frontend UI
- requirements.txt: Python dependencies
- render.yaml: Render deployment blueprint

IMPORTANT: AI generation ke liye Gemini API key zaroori hai.
Google AI Studio se API key banayein:
https://aistudio.google.com/apikey

Render par deploy:
1. GitHub par naya repository banayein, jaise ofss-ai-blog-writer.
2. Is ZIP ki files repository ke root mein upload karein.
3. Render Dashboard > New > Web Service se GitHub repository connect karein.
4. Build Command: pip install -r requirements.txt
5. Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
6. Environment Variables mein:
   GEMINI_API_KEY = apni secret API key
   GEMINI_MODEL = gemini-3.6-flash
7. Deploy karein. Deploy ke baad /api/health kholkar status check karein.

API KEY SECURITY:
- API key ko index.html mein kabhi mat likhein.
- API key ko GitHub repository mein commit mat karein.
- Sirf Render Environment settings mein secret ke roop mein rakhein.

NOTES:
- Gemini free-tier availability, limits aur model access account/region ke hisab se badal sakte hain. Google AI Studio mein current limits check karein.
- Free Render service spin down ho sakti hai; pehli request slow ho sakti hai.
- AI generated content ko publish karne se pehle dates, official links, fees, phone numbers aur claims verify karein.
- 0% AI detector, AdSense approval ya Google Discover placement ki guarantee koi tool nahi de sakta.
