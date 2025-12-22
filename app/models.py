"""
Database models for the Merchant Risk & AML Scoring Engine.
Uses SQLAlchemy ORM with SQLite for persistence.
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class RiskLevel(str, enum.Enum):
    """Risk level classifications."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MerchantStatus(str, enum.Enum):
    """Merchant account status."""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"
    UNDER_REVIEW = "UNDER_REVIEW"


class Merchant(Base):
    """Merchant profile and KYC data."""
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(String(50), unique=True, index=True, nullable=False)
    business_name = Column(String(255), nullable=False)
    country = Column(String(100), nullable=False)
    industry = Column(String(100), nullable=False)
    mcc_code = Column(String(10), nullable=True)
    annual_volume = Column(Float, default=0.0)
    monthly_transaction_count = Column(Integer, default=0)
    
    # Owner/KYC Information
    owner_name = Column(String(255), nullable=True)
    owner_pep = Column(Boolean, default=False)  # Politically Exposed Person
    owner_sanctioned = Column(Boolean, default=False)  # On sanctions list
    
    # Business Structure
    years_in_business = Column(Integer, default=0)
    offshore_structure = Column(Boolean, default=False)
    cash_intensive = Column(Boolean, default=False)
    complex_ownership = Column(Boolean, default=False)
    
    # Behavioral Signals
    refund_rate = Column(Float, default=0.0)  # Percentage
    chargeback_rate = Column(Float, default=0.0)
    volume_change_pct = Column(Float, default=0.0)  # Month-over-month change
    
    # Risk Assessment Results
    risk_score = Column(Integer, default=0)
    risk_level = Column(String(20), default=RiskLevel.LOW.value)
    risk_reasons = Column(JSON, default=list)
    last_assessment_date = Column(DateTime, nullable=True)
    
    # Account Status
    status = Column(String(20), default=MerchantStatus.PENDING.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    audit_logs = relationship("AuditLog", back_populates="merchant", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="merchant", cascade="all, delete-orphan")


class RiskAssessment(Base):
    """Historical record of risk assessments for audit trail."""
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(String(50), ForeignKey("merchants.merchant_id"), nullable=False)
    
    # Assessment Details
    risk_score = Column(Integer, nullable=False)
    risk_level = Column(String(20), nullable=False)
    risk_reasons = Column(JSON, default=list)
    
    # Input Snapshot (for audit)
    input_data = Column(JSON, nullable=False)
    applied_rules = Column(JSON, default=list)
    weights_used = Column(JSON, default=dict)
    thresholds_used = Column(JSON, default=dict)
    
    # Override Information
    is_override = Column(Boolean, default=False)
    override_reason = Column(String(255), nullable=True)
    override_by = Column(String(100), nullable=True)
    
    # Timestamps
    assessed_at = Column(DateTime, default=datetime.utcnow)
    assessed_by = Column(String(100), default="SYSTEM")
    
    # Relationship
    merchant = relationship("Merchant", back_populates="risk_assessments")


class AuditLog(Base):
    """Comprehensive audit log for all actions and changes."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(String(50), ForeignKey("merchants.merchant_id"), nullable=True)
    
    # Action Details
    action_type = Column(String(50), nullable=False)  # CREATE, UPDATE, ASSESS, CONFIG_CHANGE, etc.
    action_description = Column(Text, nullable=False)
    
    # Change Tracking
    previous_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    
    # Context
    endpoint = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    user_id = Column(String(100), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    merchant = relationship("Merchant", back_populates="audit_logs")


class RiskConfiguration(Base):
    """Configurable risk weights and thresholds."""
    __tablename__ = "risk_configurations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(JSON, nullable=False)
    config_type = Column(String(50), nullable=False)  # WEIGHT, THRESHOLD, LIST, RULE
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Change Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(100), nullable=True)


class Alert(Base):
    """Risk alerts for high-risk merchants."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    merchant_id = Column(String(50), index=True, nullable=False)
    
    # Alert Details
    alert_type = Column(String(50), nullable=False)  # HIGH_RISK, CRITICAL_RISK, THRESHOLD_EXCEEDED, etc.
    severity = Column(String(20), nullable=False)  # INFO, WARNING, CRITICAL
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    # Status
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
