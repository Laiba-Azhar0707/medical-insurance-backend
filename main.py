from concurrent.futures import ThreadPoolExecutor
import os
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import shutil
from dotenv import load_dotenv

load_dotenv()

from database import get_db
from models import User, Claim, Document, ExtractedData, Deduction
from auth import verify_password, create_access_token, decode_access_token, hash_password
from ocr import extract_text_from_image
from extraction import extract_structured_data
from image_quality import check_image_quality, validate_file_type
from comparison import compare_prescribed_vs_billed
from deduction import calculate_deductions
from pdf_utils import is_pdf, convert_pdf_to_images

app = FastAPI()

ALLOWED_ORIGINS = ["http://localhost:5173"]
extra_origins = os.environ.get("FRONTEND_ORIGIN")
if extra_origins:
    ALLOWED_ORIGINS.extend(o.strip() for o in extra_origins.split(","))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated. Contact an administrator.")

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


def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@app.get("/dashboard")
def dashboard(current_user: User = Depends(get_current_user)):
    return {
        "message": f"Welcome, {current_user.name}",
        "role": current_user.role,
    }


def process_document_type(doc_type, upload_list, claim_id, doc_config, upload_dir):
    """Saves pages to disk and runs OCR + structured extraction for one document type.
    Pure function — no DB access — so it's safe to run in a thread pool alongside
    the other document types instead of one at a time.
    PDFs are converted to one image per page before OCR; each PDF still counts
    as a single uploaded file for DB/Document purposes, but every rendered page
    goes through OCR individually, same as a multi-page image upload would."""
    combined_text = ""
    combined_identity_flag = False
    page_errors = []
    saved_pages = []  # original uploaded file_paths, for DB writes done later
    ocr_page_counter = 0

    for upload in upload_list:
        filename = f"claim_{claim_id}_{doc_type}_{upload.filename}"
        file_path = os.path.join(upload_dir, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)

        saved_pages.append(file_path)

        type_check = validate_file_type(file_path)
        if not type_check["valid"]:
            page_errors.append(f"{upload.filename}: {type_check['reason']}")
            continue

        # PDFs get expanded into one image per page; regular images are
        # treated as a single "page" so the rest of the pipeline is identical.
        if is_pdf(file_path):
            try:
                image_paths = convert_pdf_to_images(file_path, upload_dir)
            except Exception as e:
                page_errors.append(f"{upload.filename}: Could not read PDF ({str(e)})")
                continue
        else:
            image_paths = [file_path]

        for image_path in image_paths:
            ocr_page_counter += 1

            quality_check = check_image_quality(image_path)
            if not quality_check["acceptable"]:
                page_errors.append(f"Page {ocr_page_counter}: {quality_check['reason']}")
                continue

            ocr_mode, extraction_type = doc_config[doc_type]
            ocr_result = extract_text_from_image(image_path, document_type=ocr_mode)

            if ocr_result["success"]:
                combined_text += f"\n\n--- Page {ocr_page_counter} ---\n\n" + ocr_result["text"]
                combined_identity_flag = combined_identity_flag or ocr_result.get("identity_flag", False)
            else:
                page_errors.append(f"Page {ocr_page_counter}: {ocr_result['error']}")

    result = {
        "doc_type": doc_type,
        "saved_pages": saved_pages,
        "page_errors": page_errors,
        "combined_identity_flag": combined_identity_flag,
        "upload_count": ocr_page_counter,
    }

    if not combined_text.strip():
        result["error"] = "; ".join(page_errors) if page_errors else "No usable pages"
        return result

    _, extraction_type = doc_config[doc_type]
    structured = extract_structured_data(combined_text, extraction_type)
    result["structured"] = structured
    return result


BILL_DOC_TYPES = {"medicine_bill", "lab_bill", "consultation_receipt"}


@app.post("/claims")
def create_claim(
    claim_type: str = Form(...),
    prescription: list[UploadFile] = File(default=[]),
    medicine_bill: list[UploadFile] = File(default=[]),
    lab_bill: list[UploadFile] = File(default=[]),
    consultation_receipt: list[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    files = {
        "prescription": prescription,
        "medicine_bill": medicine_bill,
        "lab_bill": lab_bill,
        "consultation_receipt": consultation_receipt,
    }

    # Prescription is optional (unprescribed items just get flagged instead
    # of blocking submission), but at least one bill type is required —
    # a claim with nothing billed has nothing to process.
    submitted_bill_types = [dt for dt in BILL_DOC_TYPES if files[dt]]
    if not submitted_bill_types:
        raise HTTPException(
            status_code=400,
            detail="Please upload at least one bill (medicine bill, lab bill, or consultation receipt).",
        )

    new_claim = Claim(
        user_id=current_user.id,
        claim_type=claim_type,
        status="In Progress",
        submitted_at=datetime.utcnow(),
    )
    db.add(new_claim)
    db.commit()
    db.refresh(new_claim)

    doc_config = {
        "prescription": ("general", "prescription"),
        "medicine_bill": ("general", "medicine_bill"),
        "lab_bill": ("tabular", "lab_bill"),
        "consultation_receipt": ("general", "consultation_receipt"),
    }

    # Only process document types the user actually submitted — no point
    # spending a Groq call or generating a spurious "no pages" error for
    # something they deliberately left out.
    submitted_doc_types = {dt: files[dt] for dt in files if files[dt]}

    extraction_summary = []
    items_by_doc_type = {}

    with ThreadPoolExecutor(max_workers=max(1, len(submitted_doc_types))) as executor:
        futures = {
            executor.submit(process_document_type, doc_type, upload_list, new_claim.id, doc_config, UPLOAD_DIR): doc_type
            for doc_type, upload_list in submitted_doc_types.items()
        }
        results_by_doc_type = {futures[future]: future.result() for future in futures}

    # DB writes happen sequentially here, after all the slow network calls
    # are already done — SQLAlchemy sessions aren't thread-safe, so this
    # part can't be parallelized, but it's fast compared to the Groq calls.
    for doc_type, upload_list in submitted_doc_types.items():
        result = results_by_doc_type[doc_type]
        page_errors = result["page_errors"]
        saved_pages = result["saved_pages"]
        combined_identity_flag = result["combined_identity_flag"]

        first_document_id = None
        for file_path in saved_pages:
            new_document = Document(
                claim_id=new_claim.id,
                doc_type=doc_type,
                file_path=file_path,
                uploaded_at=datetime.utcnow(),
            )
            db.add(new_document)
            db.commit()
            db.refresh(new_document)
            if first_document_id is None:
                first_document_id = new_document.id

        items_by_doc_type[doc_type] = []

        if "structured" not in result:
            extraction_summary.append({
                "doc_type": doc_type,
                "error": result.get("error", "No usable pages"),
            })
            continue

        structured = result["structured"]

        if structured["success"]:
            for item in structured["items"]:
                new_item = ExtractedData(
                    document_id=first_document_id,
                    item_name=item.get("item_name"),
                    item_type=item.get("item_type"),
                    quantity=item.get("quantity"),
                    dosage=item.get("dosage"),
                    price=item.get("price"),
                )
                db.add(new_item)
            db.commit()

            items_by_doc_type[doc_type] = structured["items"]

            extraction_summary.append({
                "doc_type": doc_type,
                "pages_processed": result["upload_count"] - len(page_errors),
                "page_errors": page_errors,
                "items_found": len(structured["items"]),
                "needs_review": structured["needs_review"] or combined_identity_flag,
                "illegible_ratio": structured["illegible_ratio"],
                "blank_field_ratio": structured["blank_field_ratio"],
                "identity_flag": combined_identity_flag,
            })
        else:
            extraction_summary.append({"doc_type": doc_type, "error": structured["error"]})

    # --- Comparison & Deduction: medicines and tests ---
    prescribed_all = items_by_doc_type.get("prescription", [])
    prescribed_medicines = [i for i in prescribed_all if i.get("item_type") == "medicine"]
    prescribed_tests = [i for i in prescribed_all if i.get("item_type") == "test"]

    billed_medicines = items_by_doc_type.get("medicine_bill", [])
    billed_tests = items_by_doc_type.get("lab_bill", [])

    all_deductions = []
    total_unprescribed = 0.0
    comparison_errors = []

    medicine_comparison = compare_prescribed_vs_billed(prescribed_medicines, billed_medicines)
    if medicine_comparison["success"]:
        medicine_deductions = calculate_deductions(medicine_comparison["results"], claim_type)
        all_deductions.extend(medicine_deductions["deductions"])
        total_unprescribed += medicine_deductions["total_unprescribed_amount"]
    else:
        comparison_errors.append(f"Medicine comparison failed: {medicine_comparison['error']}")

    test_comparison = compare_prescribed_vs_billed(prescribed_tests, billed_tests)
    if test_comparison["success"]:
        test_deductions = calculate_deductions(test_comparison["results"], claim_type)
        all_deductions.extend(test_deductions["deductions"])
        total_unprescribed += test_deductions["total_unprescribed_amount"]
    else:
        comparison_errors.append(f"Test comparison failed: {test_comparison['error']}")

    # --- Consultation receipt validation ---
    # A consultation fee can only be considered legitimate if there's an actual
    # prescription behind it, proving a real doctor visit took place.
    consultation_items = items_by_doc_type.get("consultation_receipt", [])
    consultation_flagged = False

    if consultation_items and not prescribed_all:
        for item in consultation_items:
            all_deductions.append({
                "item_name": item.get("item_name", "Consultation Fee"),
                "amount": 0.0,
                "reason": "No prescription was provided, so this consultation cannot be verified as a legitimate doctor visit.",
                "has_price": False,
            })
        consultation_flagged = True

    action_type = "return_notice" if claim_type == "pre_paid" else "auto_deduct"

    deduction_summary = {
        "total_unprescribed_amount": round(total_unprescribed, 2),
        "deductions": all_deductions,
        "action_type": action_type,
        "errors": comparison_errors,
    }

    for d in all_deductions:
        new_deduction = Deduction(
            claim_id=new_claim.id,
            reason=d["reason"],
            amount=d["amount"],
            action_type=action_type,
            created_at=datetime.utcnow(),
        )
        db.add(new_deduction)

    new_claim.approved_amount = -total_unprescribed if any(d["has_price"] for d in all_deductions) else 0.0

    if any(d.get("needs_review") for d in extraction_summary) or consultation_flagged:
        new_claim.status = "Needs Manual Review"
    else:
        new_claim.status = "Processed"

    db.commit()

    return {
        "claim_id": new_claim.id,
        "status": new_claim.status,
        "message": "Claim submitted successfully",
        "extraction_summary": extraction_summary,
        "deduction_summary": deduction_summary,
    }


def serialize_claim_summary(claim, include_user=False):
    summary = {
        "claim_id": claim.id,
        "claim_type": claim.claim_type,
        "status": claim.status,
        "admin_status": claim.admin_status,
        "approved_amount": claim.approved_amount,
        "submitted_at": claim.submitted_at.isoformat() if claim.submitted_at else None,
        "reviewed_at": claim.reviewed_at.isoformat() if claim.reviewed_at else None,
    }
    if include_user:
        summary["user_id"] = claim.user_id
        summary["user_name"] = claim.user.name
        summary["user_email"] = claim.user.email
    return summary


@app.get("/claims/history")
def get_my_claims(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    claims = (
        db.query(Claim)
        .filter(Claim.user_id == current_user.id)
        .order_by(Claim.submitted_at.desc())
        .all()
    )
    return {"claims": [serialize_claim_summary(c) for c in claims]}


@app.get("/admin/claims")
def get_all_claims(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    claims = db.query(Claim).order_by(Claim.submitted_at.desc()).all()
    return {"claims": [serialize_claim_summary(c, include_user=True) for c in claims]}


class ClaimReviewRequest(BaseModel):
    decision: str  # "approved" or "rejected"


@app.post("/admin/claims/{claim_id}/review")
def review_claim(
    claim_id: int,
    payload: ClaimReviewRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if payload.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'")

    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")

    claim.admin_status = "Approved" if payload.decision == "approved" else "Rejected"
    claim.reviewed_by = admin.id
    claim.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(claim)

    return serialize_claim_summary(claim, include_user=True)


class CreateUserRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "user"  # "user" or "admin"


@app.post("/admin/users")
def create_user(
    payload: CreateUserRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if payload.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'")

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email already exists")

    new_user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "id": new_user.id,
        "name": new_user.name,
        "email": new_user.email,
        "role": new_user.role,
        "is_active": new_user.is_active,
    }


@app.get("/admin/users")
def list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return {
        "users": [
            {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "is_active": u.is_active, "created_at": u.created_at.isoformat()}
            for u in users
        ]
    }


@app.patch("/admin/users/{user_id}/toggle-active")
def toggle_user_active(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.id == admin.id:
        raise HTTPException(status_code=400, detail="You can't deactivate your own account")

    target_user.is_active = not target_user.is_active
    db.commit()
    db.refresh(target_user)

    return {
        "id": target_user.id,
        "name": target_user.name,
        "email": target_user.email,
        "role": target_user.role,
        "is_active": target_user.is_active,
    }


@app.delete("/admin/users/{user_id}")
def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.id == admin.id:
        raise HTTPException(status_code=400, detail="You can't delete your own account")

    existing_claims = db.query(Claim).filter(Claim.user_id == target_user.id).count()
    if existing_claims > 0:
        raise HTTPException(
            status_code=400,
            detail=f"This user has {existing_claims} claim(s) on record and can't be deleted. Deactivate the account instead to preserve claim history.",
        )

    db.delete(target_user)
    db.commit()

    return {"message": f"{target_user.name} was deleted"}