import csv
from io import StringIO
from typing import List, Optional
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Lead
from app.schemas import LeadResponse, LeadUpdate

# Buat tabel SQLite jika belum terbuat
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WIZ.ai Mini Lead Management API",
    description="API untuk mengelola leads, dedup candidates, dan ekstraksi source channel.",
    version="1.0.0",
)


@app.get("/")
def read_root():
    return {
        "message": "WIZ.ai Lead Management API is running. Check /docs for OpenAPI documentation."
    }


# 1. GET /leads (List & Filtering)
@app.get("/leads", response_model=List[LeadResponse])
def get_leads(
    status: Optional[str] = Query(None, description="Filter berdasarkan status"),
    owner: Optional[str] = Query(None, description="Filter berdasarkan contact owner"),
    country: Optional[str] = Query(None, description="Filter berdasarkan negara"),
    q: Optional[str] = Query(
        None, description="Free-text search di nama, perusahaan, atau email"
    ),
    db: Session = Depends(get_db),
):
    query = db.query(Lead)

    if status:
        query = query.filter(Lead.status.ilike(f"%{status}%"))
    if owner:
        query = query.filter(Lead.owner.ilike(f"%{owner}%"))
    if country:
        query = query.filter(Lead.country.ilike(f"%{country}%"))
    if q:
        search_filter = or_(
            Lead.name.ilike(f"%{q}%"),
            Lead.company.ilike(f"%{q}%"),
            Lead.email.ilike(f"%{q}%"),
        )
        query = query.filter(search_filter)

    return query.all()


# 2. GET /leads/export (CSV Export)
# Catatan: Letakkan endpoint ini SEBELUM /leads/{id} agar tidak dikira ID="export"
@app.get("/leads/export")
def export_leads(
    status: Optional[str] = None,
    owner: Optional[str] = None,
    country: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    leads = get_leads(
        status=status, owner=owner, country=country, q=q, db=db
    )

    output = StringIO()
    writer = csv.writer(output)

    # Header CSV
    writer.writerow(
        [
            "ID",
            "Name",
            "Email",
            "Phone",
            "Company",
            "Country",
            "Status",
            "Owner",
            "Source Channel",
            "Source Detail",
            "Notes",
            "Created At",
        ]
    )

    for lead in leads:
        writer.writerow(
            [
                lead.id,
                lead.name,
                lead.email,
                lead.phone,
                lead.company,
                lead.country,
                lead.status,
                lead.owner,
                lead.source_channel,
                lead.source_detail,
                lead.notes,
                lead.created_at,
            ]
        )

    output.seek(0)
    headers = {"Content-Disposition": "attachment; filename=leads_export.csv"}
    return StreamingResponse(
        iter([output.getvalue()]), media_type="text/csv", headers=headers
    )


# 3. GET /leads/{id} (Detail Lead)
@app.get("/leads/{lead_id}", response_model=LeadResponse)
def get_lead_detail(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")
    return lead


# 4. PATCH /leads/{id} (Update status, owner, notes)
@app.patch("/leads/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: int, payload: LeadUpdate, db: Session = Depends(get_db)
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead tidak ditemukan")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lead, key, value)

    db.commit()
    db.refresh(lead)
    return lead

from app.schemas import DedupeCandidate
from app.services.dedupe import find_dedupe_candidates


# 6. POST /leads/dedupe-candidates
@app.post(
    "/leads/dedupe-candidates", response_model=List[DedupeCandidate]
)
def get_dedupe_candidates(
    limit: int = 10, db: Session = Depends(get_db)
):
    return find_dedupe_candidates(db, max_results=limit)

from app.schemas import FormSubmissionIngest
from app.services.extraction import extract_source_from_text, enrich_leads_source_extraction

# 7. POST /leads/ingest - Ingest web form submissions & Auto-Dedup check
@app.post("/leads/ingest")
def ingest_website_submission(data: FormSubmissionIngest, db: Session = Depends(get_db)):
    # Simple Dedup Check: Berdasarkan Email
    existing_lead = None
    if data.email:
        existing_lead = db.query(Lead).filter(Lead.email.ilike(data.email.strip())).first()

    # Extraksi Source dari message
    extracted = extract_source_from_text(data.message or "")

    if existing_lead:
        # Update existing lead
        if data.name:
            existing_lead.name = data.name
        if data.phone:
            existing_lead.phone = data.phone
        if data.company:
            existing_lead.company = data.company
        if data.country:
            existing_lead.country = data.country
        if data.message:
            existing_lead.notes = f"{existing_lead.notes or ''} | Ingest update: {data.message}".strip(" |")
        
        db.commit()
        db.refresh(existing_lead)
        return {"status": "updated", "lead_id": existing_lead.id}
    else:
        # Insert New Lead
        new_lead = Lead(
            name=data.name,
            email=data.email.lower().strip() if data.email else None,
            phone=data.phone,
            company=data.company,
            country=data.country,
            status="New",
            notes=data.message,
            source_channel=extracted.get("channel"),
            source_detail=extracted.get("detail")
        )
        db.add(new_lead)
        db.commit()
        db.refresh(new_lead)
        return {"status": "created", "lead_id": new_lead.id}

# 8. POST /leads/extract-sources - Batch process extraction
@app.post("/leads/extract-sources")
def trigger_source_extraction(limit: int = 100, db: Session = Depends(get_db)):
    updated_count = enrich_leads_source_extraction(db, limit=limit)
    return {"message": f"Berhasil memproses ekstraksi source untuk {updated_count} leads"}