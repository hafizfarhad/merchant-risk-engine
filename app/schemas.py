"""
Pydantic schemas for request/response validation.
Ensures strong typing and automatic OpenAPI documentation.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RiskLevelEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MerchantStatusEnum(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"
    UNDER_REVIEW = "UNDER_REVIEW"


# === Merchant Schemas ===

class MerchantCreate(BaseModel):
    """Schema for creating/onboarding a new merchant."""
    merchant_id: str = Field(..., min_length=1, max_length=50, description="Unique merchant identifier")
    business_name: str = Field(..., min_length=1, max_length=255, description="Business legal name")
    country: str = Field(..., min_length=2, max_length=100, description="Country of operation")
    industry: str = Field(..., min_length=1, max_length=100, description="Business industry/sector")
    mcc_code: Optional[str] = Field(None, max_length=10, description="Merchant Category Code")
    annual_volume: Optional[float] = Field(0.0, ge=0, description="Annual transaction volume in USD")
    monthly_transaction_count: Optional[int] = Field(0, ge=0, description="Average monthly transactions")
    
    # Owner Information
    owner_name: Optional[str] = Field(None, max_length=255, description="Primary owner name")
    owner_pep: bool = Field(False, description="Is owner a Politically Exposed Person?")
    owner_sanctioned: bool = Field(False, description="Is owner on sanctions list?")
    
    # Business Characteristics
    years_in_business: Optional[int] = Field(0, ge=0, description="Years the business has operated")
    offshore_structure: bool = Field(False, description="Has offshore corporate structure?")
    cash_intensive: bool = Field(False, description="Is the business cash-intensive?")
    complex_ownership: bool = Field(False, description="Has complex ownership structure?")
    
    # Behavioral Metrics
    refund_rate: Optional[float] = Field(0.0, ge=0, le=100, description="Refund rate percentage")
    chargeback_rate: Optional[float] = Field(0.0, ge=0, le=100, description="Chargeback rate percentage")
    volume_change_pct: Optional[float] = Field(0.0, description="Month-over-month volume change %")

    class Config:
        json_schema_extra = {
            "example": {
                "merchant_id": "M123",
                "business_name": "Acme Payments Inc",
                "country": "United States",
                "industry": "PaymentProcessor",
                "mcc_code": "4829",
                "annual_volume": 500000.0,
                "owner_name": "John Doe",
                "owner_pep": True,
                "owner_sanctioned": False,
                "years_in_business": 5,
                "offshore_structure": False,
                "cash_intensive": False
            }
        }


class MerchantUpdate(BaseModel):
    """Schema for updating merchant information."""
    business_name: Optional[str] = Field(None, min_length=1, max_length=255)
    country: Optional[str] = Field(None, min_length=2, max_length=100)
    industry: Optional[str] = Field(None, min_length=1, max_length=100)
    mcc_code: Optional[str] = Field(None, max_length=10)
    annual_volume: Optional[float] = Field(None, ge=0)
    monthly_transaction_count: Optional[int] = Field(None, ge=0)
    owner_name: Optional[str] = Field(None, max_length=255)
    owner_pep: Optional[bool] = None
    owner_sanctioned: Optional[bool] = None
    years_in_business: Optional[int] = Field(None, ge=0)
    offshore_structure: Optional[bool] = None
    cash_intensive: Optional[bool] = None
    complex_ownership: Optional[bool] = None
    refund_rate: Optional[float] = Field(None, ge=0, le=100)
    chargeback_rate: Optional[float] = Field(None, ge=0, le=100)
    volume_change_pct: Optional[float] = None
    status: Optional[MerchantStatusEnum] = None


class MerchantResponse(BaseModel):
    """Response schema for merchant data."""
    id: int
    merchant_id: str
    business_name: str
    country: str
    industry: str
    mcc_code: Optional[str]
    annual_volume: float
    monthly_transaction_count: int
    owner_name: Optional[str]
    owner_pep: bool
    owner_sanctioned: bool
    years_in_business: int
    offshore_structure: bool
    cash_intensive: bool
    complex_ownership: bool
    refund_rate: float
    chargeback_rate: float
    volume_change_pct: float
    risk_score: int
    risk_level: str
    risk_reasons: List[str]
    status: str
    last_assessment_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# === Risk Assessment Schemas ===

class RiskAssessmentResponse(BaseModel):
    """Response schema for risk assessment."""
    merchant_id: str
    risk_score: int
    risk_level: str
    risk_reasons: List[str]
    assessed_at: datetime
    input_summary: Dict[str, Any]
    applied_rules: List[str]
    is_override: bool
    override_reason: Optional[str]

    class Config:
        from_attributes = True


class RiskOverrideRequest(BaseModel):
    """Request to manually override a merchant's risk level."""
    new_risk_level: RiskLevelEnum
    reason: str = Field(..., min_length=10, max_length=500, description="Justification for override")
    override_by: str = Field(..., min_length=1, max_length=100, description="User making the override")


# === Configuration Schemas ===

class RiskWeightsUpdate(BaseModel):
    """Schema for updating risk weights."""
    weights: Dict[str, int] = Field(..., description="Risk factor weights (0-100)")
    
    @validator('weights')
    def validate_weights(cls, v):
        for key, value in v.items():
            if not 0 <= value <= 100:
                raise ValueError(f"Weight for {key} must be between 0 and 100")
        return v


class RiskThresholdsUpdate(BaseModel):
    """Schema for updating risk thresholds."""
    low_max: int = Field(..., ge=0, le=100, description="Maximum score for LOW risk")
    medium_max: int = Field(..., ge=0, le=100, description="Maximum score for MEDIUM risk")
    high_min: int = Field(..., ge=0, le=100, description="Minimum score for HIGH risk")
    critical_min: int = Field(..., ge=0, le=100, description="Minimum score for CRITICAL risk")
    
    @validator('medium_max')
    def validate_medium_max(cls, v, values):
        if 'low_max' in values and v <= values['low_max']:
            raise ValueError("medium_max must be greater than low_max")
        return v
    
    @validator('high_min')
    def validate_high_min(cls, v, values):
        if 'medium_max' in values and v <= values['medium_max']:
            raise ValueError("high_min must be greater than medium_max")
        return v


class BlacklistUpdate(BaseModel):
    """Schema for updating blacklists."""
    list_type: str = Field(..., description="Type of list: countries, industries, mccs")
    items: List[str] = Field(..., description="List of items to set")


# === Audit Schemas ===

class AuditLogResponse(BaseModel):
    """Response schema for audit log entries."""
    id: int
    merchant_id: Optional[str]
    action_type: str
    action_description: str
    previous_value: Optional[Dict[str, Any]]
    new_value: Optional[Dict[str, Any]]
    user_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# === Alert Schemas ===

class AlertResponse(BaseModel):
    """Response schema for alerts."""
    id: int
    merchant_id: str
    alert_type: str
    severity: str
    title: str
    description: str
    is_resolved: bool
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AlertResolveRequest(BaseModel):
    """Request to resolve an alert."""
    resolved_by: str = Field(..., min_length=1, max_length=100)
    resolution_notes: str = Field(..., min_length=5, max_length=1000)


# === Dashboard Schemas ===

class DashboardStats(BaseModel):
    """Dashboard statistics response."""
    total_merchants: int
    merchants_by_risk_level: Dict[str, int]
    merchants_by_status: Dict[str, int]
    recent_high_risk_count: int
    unresolved_alerts_count: int
    average_risk_score: float
    high_risk_countries: List[Dict[str, Any]]
    recent_assessments: List[Dict[str, Any]]
