import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy.orm import Session
from app.models import Lead

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "mock-key"))

VALID_CHANNELS = [
    "Website",
    "Event",
    "LinkedIn",
    "Organic Search",
    "Referral",
    "Manual/Sales",
    "Other",
]


def extract_source_from_text(notes: str) -> dict:
    """Ekstraksi channel & detail dari text notes menggunakan LLM / Rules Fallback"""
    if not notes or len(notes.strip()) == 0:
        return {"channel": "Other", "detail": "No notes provided"}

    notes_lower = notes.lower()

    # Rule-Based Fallback Cepat (jika API Error/Kosong)
    fallback_channel = "Other"
    if "booth" in notes_lower or "expo" in notes_lower or "festival" in notes_lower or "summit" in notes_lower:
        fallback_channel = "Event"
    elif "linkedin" in notes_lower:
        fallback_channel = "LinkedIn"
    elif "google" in notes_lower or "organic search" in notes_lower:
        fallback_channel = "Organic Search"
    elif "referred" in notes_lower or "intro" in notes_lower:
        fallback_channel = "Referral"
    elif "form" in notes_lower or "page" in notes_lower or "blog" in notes_lower or "website" in notes_lower:
        fallback_channel = "Website"
    elif "phone" in notes_lower or "manual" in notes_lower or "voicemail" in notes_lower:
        fallback_channel = "Manual/Sales"

    prompt = f"""
Analyze the following lead notes from CRM and extract the marketing channel and detail.

Notes: "{notes}"

Allowed Channels strictly ONE of: {VALID_CHANNELS}

Return ONLY a JSON object:
{{
  "channel": "One of the allowed channels",
  "detail": "Short summary of the specific event/source context"
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        res = json.loads(response.choices[0].message.content)
        if res.get("channel") not in VALID_CHANNELS:
            res["channel"] = fallback_channel
        return res
    except Exception:
        return {"channel": fallback_channel, "detail": notes[:100]}


def enrich_leads_source_extraction(db: Session, limit: int = 50):
    """Proses batch leads yang belum di-ekstrak source-nya"""
    leads = db.query(Lead).filter(Lead.source_channel.is_(None)).limit(limit).all()
    count = 0
    for lead in leads:
        extracted = extract_source_from_text(lead.notes)
        lead.source_channel = extracted.get("channel", "Other")
        lead.source_detail = extracted.get("detail", "")
        count += 1
    
    db.commit()
    return count