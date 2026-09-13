from datetime import datetime
import json
import os
from dateutil import parser
import pandas as pd
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import Lead

# Buat tabel jika belum ada
Base.metadata.create_all(bind=engine)


def clean_date(date_val):
    """Normalisasi format tanggal ke ISO format datetime"""
    if pd.isna(date_val) or not date_val:
        return None
    try:
        return parser.parse(str(date_val))
    except Exception:
        return None


def clean_lead_data(df: pd.DataFrame) -> pd.DataFrame:
    """Membersihkan dan menormalisasi data seed dari CSV"""

    # 1. Normalisasi Nama: Gabungkan First Name & Last Name jika Full Name kosong (atau sebaliknya)
    def resolve_name(row):
        full_name = str(row.get("Full Name", "")).strip()
        first_name = str(row.get("First Name", "")).strip()
        last_name = str(row.get("Last Name", "")).strip()

        if full_name and full_name.lower() != "nan":
            return full_name
        combined = f"{first_name} {last_name}".strip()
        return combined if combined and combined.lower() != "nan" else None

    df["clean_name"] = df.apply(resolve_name, axis=1)

    # 2. Normalisasi Lead Status: Trim whitespace & Title Case
    if "Lead Status" in df.columns:
        df["clean_status"] = (
            df["Lead Status"].astype(str).str.strip().str.title()
        )
        df["clean_status"] = df["clean_status"].replace("Nan", None)
    else:
        df["clean_status"] = "New"

    # 3. Handling Kolom Lain
    df["clean_email"] = (
        df["Email"].astype(str).str.strip().str.lower()
        if "Email" in df.columns
        else None
    )
    df["clean_email"] = df["clean_email"].replace("nan", None)

    df["clean_phone"] = (
        df["Phone Number"].astype(str).str.strip()
        if "Phone Number" in df.columns
        else None
    )
    df["clean_phone"] = df["clean_phone"].replace("nan", None)

    df["clean_company"] = (
        df["Company Name"].astype(str).str.strip()
        if "Company Name" in df.columns
        else None
    )
    df["clean_company"] = df["clean_company"].replace("nan", None)

    df["clean_country"] = (
        df["Country"].astype(str).str.strip()
        if "Country" in df.columns
        else None
    )
    df["clean_country"] = df["clean_country"].replace("nan", None)

    df["clean_owner"] = (
        df["Contact Owner"].astype(str).str.strip()
        if "Contact Owner" in df.columns
        else None
    )
    df["clean_owner"] = df["clean_owner"].replace("nan", None)

    df["clean_notes"] = (
        df["Notes"].astype(str).str.strip()
        if "Notes" in df.columns
        else None
    )
    df["clean_notes"] = df["clean_notes"].replace("nan", None)

    # 4. Parsing Tanggal
    date_col = (
        "Create Date"
        if "Create Date" in df.columns
        else (
            "Created Date" if "Created Date" in df.columns else "submitted_at"
        )
    )
    if date_col in df.columns:
        df["clean_created_at"] = df[date_col].apply(clean_date)
    else:
        df["clean_created_at"] = datetime.utcnow()

    return df


def seed_database():
    db: Session = SessionLocal()

    # Cek apakah data sudah pernah di-seed
    if db.query(Lead).count() > 0:
        print("Database sudah berisi data. Seeding dilewati.")
        db.close()
        return

    csv_path = os.path.join("data", "leads_seed.csv")
    if not os.path.exists(csv_path):
        print(f"File {csv_path} tidak ditemukan!")
        db.close()
        return

    print("Memproses data CSV...")
    df = pd.read_csv(csv_path)
    df_clean = clean_lead_data(df)

    leads_to_insert = []
    for _, row in df_clean.iterrows():
        lead = Lead(
            name=row["clean_name"],
            email=row["clean_email"],
            phone=row["clean_phone"],
            company=row["clean_company"],
            country=row["clean_country"],
            status=row["clean_status"],
            owner=row["clean_owner"],
            notes=row["clean_notes"],
            created_at=row["clean_created_at"],
        )
        leads_to_insert.append(lead)

    db.bulk_save_objects(leads_to_insert)
    db.commit()
    print(
        f"Berhasil meng-ingest {len(leads_to_insert)} data leads ke SQLite!"
    )
    db.close()


if __name__ == "__main__":
    seed_database()