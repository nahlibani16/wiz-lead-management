import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Lead

# Gunakan StaticPool agar database :memory: dapat diakses secara konsisten oleh seluruh thread
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Menyediakan koneksi yang sama untuk semua thread test
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    # Buat semua tabel sebelum tiap test dijalankan
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Seed 1 dummy lead untuk testing
    lead1 = Lead(
        name="John Doe",
        email="john.doe@acme.com",
        phone="+1 234 567 890",
        company="Acme Corp",
        country="United States",
        status="New",
        owner="Sales Agent",
        notes="Met at booth TechCrunch Expo 2026",
    )
    db.add(lead1)
    db.commit()

    yield

    # Hapus tabel setelah test selesai
    Base.metadata.drop_all(bind=engine)


def test_get_leads():
    response = client.get("/leads")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "John Doe"


def test_patch_lead_status():
    response = client.patch(
        "/leads/1", json={"status": "Qualified", "notes": "Updated note"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Qualified"
    assert data["notes"] == "Updated note"


def test_ingest_duplicate_lead():
    payload = {
        "name": "Johnathan Doe",
        "email": "john.doe@acme.com",
        "message": "Following up over email",
    }
    response = client.post("/leads/ingest", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "updated"


def test_extract_source_endpoint():
    response = client.post("/leads/extract-sources?limit=10")
    assert response.status_code == 200