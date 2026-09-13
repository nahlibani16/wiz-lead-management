import os

from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy.orm import Session
from thefuzz import fuzz

from app.models import Lead

load_dotenv()

# Inisialisasi OpenAI Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "mock-key"))


def extract_email_domain(email: str) -> str:
    if not email or "@" not in email:
        return ""
    return email.split("@")[-1].lower().strip()


def extract_digits(phone: str) -> str:
    if not phone:
        return ""
    return "".join(filter(str.isdigit, phone))


def get_candidate_pairs(db: Session, max_candidates: int = 50):
    """Step 1: Blocking / Candidate Generation (Fuzzy & Heuristic)"""
    leads = db.query(Lead).all()
    candidate_pairs = []
    seen_pairs = set()

    for i in range(len(leads)):
        for j in range(i + 1, len(leads)):
            lead_a = leads[i]
            lead_b = leads[j]

            pair_key = (
                min(lead_a.id, lead_b.id),
                max(lead_a.id, lead_b.id),
            )
            if pair_key in seen_pairs:
                continue

            is_candidate = False

            # Rule 1: Cleaned phone digits match
            phone_a = extract_digits(lead_a.phone)
            phone_b = extract_digits(lead_b.phone)
            if phone_a and phone_b and phone_a == phone_b:
                is_candidate = True

            # Rule 2: Same email domain AND name similarity > 70%
            domain_a = extract_email_domain(lead_a.email)
            domain_b = extract_email_domain(lead_a.email)
            if not is_candidate and domain_a and domain_b and domain_a == domain_b:
                if lead_a.name and lead_b.name:
                    name_score = fuzz.ratio(
                        lead_a.name.lower(), lead_b.name.lower()
                    )
                    if name_score >= 70:
                        is_candidate = True

            # Rule 3: High name similarity AND company similarity
            if not is_candidate and lead_a.name and lead_b.name:
                name_score = fuzz.ratio(
                    lead_a.name.lower(), lead_b.name.lower()
                )
                if name_score >= 80:
                    if lead_a.company and lead_b.company:
                        comp_score = fuzz.ratio(
                            lead_a.company.lower(), lead_b.company.lower()
                        )
                        if comp_score >= 60:
                            is_candidate = True

            if is_candidate:
                seen_pairs.add(pair_key)
                candidate_pairs.append((lead_a, lead_b))

            if len(candidate_pairs) >= max_candidates:
                break
        if len(candidate_pairs) >= max_candidates:
            break

    return candidate_pairs


def evaluate_pair_with_llm(lead_a: Lead, lead_b: Lead) -> dict:
    """Step 2: LLM Evaluation & Confidence Scoring"""
    prompt = f"""
Compare these two lead records from a CRM export and determine if they represent the same individual/person.

Lead A:
- ID: {lead_a.id}
- Name: {lead_a.name}
- Email: {lead_a.email}
- Phone: {lead_a.phone}
- Company: {lead_a.company}
- Country: {lead_a.country}
- Notes: {lead_a.notes}

Lead B:
- ID: {lead_b.id}
- Name: {lead_b.name}
- Email: {lead_b.email}
- Phone: {lead_b.phone}
- Company: {lead_b.company}
- Country: {lead_b.country}
- Notes: {lead_b.notes}

Return a valid JSON object ONLY with the following schema:
{{
  "is_duplicate": boolean,
  "confidence_score": float between 0.0 and 1.0,
  "reason": "short explanation of why they are or are not duplicate"
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        import json

        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        # Fallback jika tidak ada API key / error
        name_score = (
            fuzz.ratio(lead_a.name, lead_b.name) / 100.0
            if lead_a.name and lead_b.name
            else 0.5
        )
        return {
            "is_duplicate": name_score > 0.75,
            "confidence_score": name_score,
            "reason": f"Heuristic fallback scoring due to API call error: {str(e)}",
        }


def find_dedupe_candidates(db: Session, max_results: int = 10):
    pairs = get_candidate_pairs(db, max_candidates=max_results)
    results = []

    for lead_a, lead_b in pairs:
        llm_res = evaluate_pair_with_llm(lead_a, lead_b)

        if llm_res.get("is_duplicate", False):
            results.append(
                {
                    "candidate_pair": [lead_a.id, lead_b.id],
                    "confidence_score": llm_res.get("confidence_score", 0.8),
                    "reason": llm_res.get("reason", "Potential match"),
                    "leads": [lead_a, lead_b],
                }
            )

    results.sort(key=lambda x: x["confidence_score"], reverse=True)
    return results