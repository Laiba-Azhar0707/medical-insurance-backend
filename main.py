from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import shutil
import os

from database import get_db
from models import User, Claim, Document
from auth import verify_password, create_access_token, decode_access_token

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user.email, "role": user.role})

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "name": user.name,
    }


def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split(" ")[1]
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.email == payload["sub"]).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


@app.get("/dashboard")
def dashboard(current_user: User = Depends(get_current_user)):
    return {
        "message": f"Welcome, {current_user.name}",
        "role": current_user.role,
    }


@app.post("/claims")
def create_claim(
    claim_type: str = Form(...),
    prescription: UploadFile = File(...),
    medicine_bill: UploadFile = File(...),
    lab_bill: UploadFile = File(...),
    consultation_receipt: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    new_claim = Claim(
        user_id=current_user.id,
        claim_type=claim_type,
        status="In Progress",
        submitted_at=datetime.utcnow(),
    )
    db.add(new_claim)
    db.commit()
    db.refresh(new_claim)

    files = {
        "prescription": prescription,
        "medicine_bill": medicine_bill,
        "lab_bill": lab_bill,
        "consultation_receipt": consultation_receipt,
    }

    for doc_type, upload in files.items():
        filename = f"claim_{new_claim.id}_{doc_type}_{upload.filename}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)

        new_document = Document(
            claim_id=new_claim.id,
            doc_type=doc_type,
            file_path=file_path,
            uploaded_at=datetime.utcnow(),
        )
        db.add(new_document)

    db.commit()

    return {
        "claim_id": new_claim.id,
        "status": new_claim.status,
        "message": "Claim submitted successfully",
    }