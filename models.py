from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    claims = relationship("Claim", back_populates="user", foreign_keys="Claim.user_id")


class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    claim_type = Column(String, nullable=False)   # "pre_paid" or "reimbursement"
    status = Column(String, default="In Progress")   # AI pipeline result: In Progress / Processed / Needs Manual Review
    admin_status = Column(String, default="Pending Review")   # admin decision: Pending Review / Approved / Rejected
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    approved_amount = Column(Float, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="claims", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    documents = relationship("Document", back_populates="claim")
    deductions = relationship("Deduction", back_populates="claim")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    doc_type = Column(String, nullable=False)   # prescription, medicine_bill, lab_bill, consultation_receipt
    file_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    claim = relationship("Claim", back_populates="documents")
    extracted_items = relationship("ExtractedData", back_populates="document")


class ExtractedData(Base):
    __tablename__ = "extracted_data"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    item_name = Column(String, nullable=False)
    item_type = Column(String, nullable=True)   # medicine, test, consultation
    quantity = Column(Float, nullable=True)
    dosage = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    is_prescribed = Column(Boolean, default=None)   # set later by your validation logic

    document = relationship("Document", back_populates="extracted_items")
    deductions = relationship("Deduction", back_populates="extracted_item")


class Deduction(Base):
    __tablename__ = "deductions"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    extracted_data_id = Column(Integer, ForeignKey("extracted_data.id"), nullable=True)
    reason = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    action_type = Column(String, nullable=False)   # "return_notice" or "auto_deduct"
    created_at = Column(DateTime, default=datetime.utcnow)

    claim = relationship("Claim", back_populates="deductions")
    extracted_item = relationship("ExtractedData", back_populates="deductions")