"""
API Routes for Merchant Risk Engine.
Implements all REST endpoints for merchant management and risk assessment.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from ..database import get_db
from ..models import Merchant, RiskAssessment, AuditLog, Alert, RiskConfiguration, MerchantStatus
from ..schemas import (
    MerchantCreate, MerchantUpdate, MerchantResponse,
    RiskAssessmentResponse, RiskOverrideRequest,
    RiskWeightsUpdate, RiskThresholdsUpdate, BlacklistUpdate,
    AuditLogResponse, AlertResponse, AlertResolveRequest,
    DashboardStats
)
from ..services import RiskEngineService, AuditService
from ..security import verify_api_key, get_client_ip, check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()


# === Merchant Endpoints ===

@router.post("/merchants", response_model=MerchantResponse, tags=["Merchants"])
async def create_merchant(
    merchant_data: MerchantCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Onboard a new merchant and compute initial risk assessment.
    
    This endpoint:
    1. Validates merchant data
    2. Creates merchant record
    3. Performs risk assessment
    4. Creates alerts if high-risk
    5. Logs all actions for audit
    """
    # Check if merchant already exists
    existing = db.query(Merchant).filter(
        Merchant.merchant_id == merchant_data.merchant_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Merchant {merchant_data.merchant_id} already exists"
        )
    
    # Create merchant record
    merchant = Merchant(**merchant_data.model_dump())
    db.add(merchant)
    db.flush()  # Get ID without committing
    
    # Perform risk assessment
    risk_score, risk_level, reasons, applied_rules = RiskEngineService.assess_merchant_risk(
        db, merchant
    )
    
    # Update merchant with risk data
    merchant.risk_score = risk_score
    merchant.risk_level = risk_level
    merchant.risk_reasons = reasons
    merchant.last_assessment_date = datetime.utcnow()
    
    # Auto-approve LOW risk, send others for manual review
    if risk_level == "LOW":
        merchant.status = MerchantStatus.ACTIVE.value  # Auto-approved
    else:
        merchant.status = MerchantStatus.UNDER_REVIEW.value  # Manual review required
    
    # Record assessment for audit
    RiskEngineService.record_assessment(
        db, merchant, risk_score, risk_level, reasons, applied_rules
    )
    
    # Create alert if needed
    RiskEngineService.create_alert_if_needed(db, merchant, risk_level, reasons)
    
    # Log merchant creation
    client_ip = get_client_ip(request)
    AuditService.log_merchant_create(
        db, 
        merchant.merchant_id, 
        merchant_data.model_dump(),
        ip_address=client_ip
    )
    
    db.commit()
    db.refresh(merchant)
    
    logger.info(f"Merchant {merchant.merchant_id} onboarded with risk level: {risk_level}")
    
    return merchant


@router.get("/merchants", response_model=List[MerchantResponse], tags=["Merchants"])
async def list_merchants(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    status: Optional[str] = Query(None, description="Filter by status"),
    country: Optional[str] = Query(None, description="Filter by country"),
    db: Session = Depends(get_db)
):
    """
    List all merchants with optional filtering.
    """
    query = db.query(Merchant)
    
    if risk_level:
        query = query.filter(Merchant.risk_level == risk_level.upper())
    if status:
        query = query.filter(Merchant.status == status.upper())
    if country:
        query = query.filter(Merchant.country.ilike(f"%{country}%"))
    
    merchants = query.order_by(desc(Merchant.risk_score)).offset(skip).limit(limit).all()
    return merchants


@router.get("/merchants/{merchant_id}", response_model=MerchantResponse, tags=["Merchants"])
async def get_merchant(
    merchant_id: str,
    db: Session = Depends(get_db)
):
    """Get merchant details by ID."""
    merchant = db.query(Merchant).filter(
        Merchant.merchant_id == merchant_id
    ).first()
    
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    return merchant


@router.put("/merchants/{merchant_id}", response_model=MerchantResponse, tags=["Merchants"])
async def update_merchant(
    merchant_id: str,
    update_data: MerchantUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Update merchant information and re-assess risk.
    """
    merchant = db.query(Merchant).filter(
        Merchant.merchant_id == merchant_id
    ).first()
    
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    # Store previous state for audit
    previous_data = {
        "country": merchant.country,
        "industry": merchant.industry,
        "owner_pep": merchant.owner_pep,
        "risk_score": merchant.risk_score,
        "risk_level": merchant.risk_level
    }
    
    # Apply updates
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        if value is not None:
            setattr(merchant, field, value.value if hasattr(value, 'value') else value)
    
    # Re-assess risk
    risk_score, risk_level, reasons, applied_rules = RiskEngineService.assess_merchant_risk(
        db, merchant
    )
    
    merchant.risk_score = risk_score
    merchant.risk_level = risk_level
    merchant.risk_reasons = reasons
    merchant.last_assessment_date = datetime.utcnow()
    merchant.updated_at = datetime.utcnow()
    
    # Auto-approve LOW risk, send others for manual review
    if risk_level == "LOW":
        merchant.status = MerchantStatus.ACTIVE.value  # Auto-approved
    else:
        merchant.status = MerchantStatus.UNDER_REVIEW.value  # Manual review required
    
    # Record assessment
    RiskEngineService.record_assessment(
        db, merchant, risk_score, risk_level, reasons, applied_rules
    )
    
    # Create alert if needed
    RiskEngineService.create_alert_if_needed(db, merchant, risk_level, reasons)
    
    # Log update
    client_ip = get_client_ip(request)
    AuditService.log_merchant_update(
        db,
        merchant_id,
        previous_data,
        update_dict,
        ip_address=client_ip
    )
    
    db.commit()
    db.refresh(merchant)
    
    return merchant


@router.delete("/merchants/{merchant_id}", tags=["Merchants"])
async def delete_merchant(
    merchant_id: str,
    request: Request,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Delete a merchant (admin only).
    """
    merchant = db.query(Merchant).filter(
        Merchant.merchant_id == merchant_id
    ).first()
    
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    # Log deletion
    client_ip = get_client_ip(request)
    AuditService.log_action(
        db,
        action_type="MERCHANT_DELETE",
        action_description=f"Merchant {merchant_id} deleted",
        merchant_id=merchant_id,
        previous_value={"business_name": merchant.business_name, "risk_level": merchant.risk_level},
        ip_address=client_ip
    )
    
    db.delete(merchant)
    db.commit()
    
    return {"message": f"Merchant {merchant_id} deleted successfully"}


@router.post("/merchants/{merchant_id}/approve", tags=["Merchants"])
async def approve_merchant(
    merchant_id: str,
    request: Request,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Manually approve a merchant (admin only).
    Sets status to ACTIVE.
    """
    merchant = db.query(Merchant).filter(
        Merchant.merchant_id == merchant_id
    ).first()
    
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    previous_status = merchant.status
    merchant.status = MerchantStatus.ACTIVE.value
    merchant.updated_at = datetime.utcnow()
    
    # Log approval
    client_ip = get_client_ip(request)
    AuditService.log_action(
        db,
        action_type="MERCHANT_APPROVED",
        action_description=f"Merchant {merchant_id} manually approved",
        merchant_id=merchant_id,
        previous_value={"status": previous_status},
        new_value={"status": merchant.status},
        ip_address=client_ip
    )
    
    db.commit()
    db.refresh(merchant)
    
    logger.info(f"Merchant {merchant_id} approved manually")
    return {"message": f"Merchant {merchant_id} approved successfully", "status": merchant.status}


@router.post("/merchants/{merchant_id}/reject", tags=["Merchants"])
async def reject_merchant(
    merchant_id: str,
    request: Request,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Manually reject a merchant (admin only).
    Sets status to TERMINATED.
    """
    merchant = db.query(Merchant).filter(
        Merchant.merchant_id == merchant_id
    ).first()
    
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    previous_status = merchant.status
    merchant.status = MerchantStatus.TERMINATED.value
    merchant.updated_at = datetime.utcnow()
    
    # Log rejection
    client_ip = get_client_ip(request)
    AuditService.log_action(
        db,
        action_type="MERCHANT_REJECTED",
        action_description=f"Merchant {merchant_id} manually rejected",
        merchant_id=merchant_id,
        previous_value={"status": previous_status},
        new_value={"status": merchant.status},
        ip_address=client_ip
    )
    
    db.commit()
    db.refresh(merchant)
    
    logger.info(f"Merchant {merchant_id} rejected manually")
    return {"message": f"Merchant {merchant_id} rejected successfully", "status": merchant.status}


# === Risk Assessment Endpoints ===

@router.get("/merchants/{merchant_id}/risk", response_model=RiskAssessmentResponse, tags=["Risk Assessment"])
async def get_merchant_risk(
    merchant_id: str,
    reassess: bool = Query(False, description="Force re-assessment"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Get current risk assessment for a merchant.
    Optionally force re-assessment with ?reassess=true
    """
    merchant = db.query(Merchant).filter(
        Merchant.merchant_id == merchant_id
    ).first()
    
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    if reassess:
        # Perform fresh assessment
        risk_score, risk_level, reasons, applied_rules = RiskEngineService.assess_merchant_risk(
            db, merchant
        )
        
        # Update merchant
        merchant.risk_score = risk_score
        merchant.risk_level = risk_level
        merchant.risk_reasons = reasons
        merchant.last_assessment_date = datetime.utcnow()
        
        # Record assessment
        RiskEngineService.record_assessment(
            db, merchant, risk_score, risk_level, reasons, applied_rules
        )
        
        # Log
        client_ip = get_client_ip(request) if request else None
        AuditService.log_risk_assessment(
            db, merchant_id, risk_score, risk_level, reasons,
            ip_address=client_ip
        )
        
        db.commit()
    
    return RiskAssessmentResponse(
        merchant_id=merchant.merchant_id,
        risk_score=merchant.risk_score,
        risk_level=merchant.risk_level,
        risk_reasons=merchant.risk_reasons or [],
        assessed_at=merchant.last_assessment_date or merchant.updated_at,
        input_summary={
            "country": merchant.country,
            "industry": merchant.industry,
            "owner_pep": merchant.owner_pep,
            "annual_volume": merchant.annual_volume
        },
        applied_rules=[],  # Would come from latest assessment
        is_override=False,
        override_reason=None
    )


@router.post("/merchants/{merchant_id}/risk/override", response_model=RiskAssessmentResponse, tags=["Risk Assessment"])
async def override_merchant_risk(
    merchant_id: str,
    override_request: RiskOverrideRequest,
    request: Request,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Manually override a merchant's risk level (admin only).
    Requires justification for audit trail.
    """
    merchant = db.query(Merchant).filter(
        Merchant.merchant_id == merchant_id
    ).first()
    
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    previous_level = merchant.risk_level
    previous_score = merchant.risk_score
    
    # Map risk level to approximate score
    score_map = {"LOW": 15, "MEDIUM": 45, "HIGH": 75, "CRITICAL": 95}
    new_score = score_map.get(override_request.new_risk_level.value, 50)
    
    # Update merchant
    merchant.risk_level = override_request.new_risk_level.value
    merchant.risk_score = new_score
    merchant.risk_reasons = [f"Manual override: {override_request.reason}"]
    merchant.last_assessment_date = datetime.utcnow()
    
    # Record override assessment
    RiskEngineService.record_assessment(
        db, merchant, new_score, override_request.new_risk_level.value,
        [f"Manual override from {previous_level} to {override_request.new_risk_level.value}"],
        ["MANUAL_OVERRIDE"],
        assessed_by=override_request.override_by,
        is_override=True,
        override_reason=override_request.reason
    )
    
    # Log override
    client_ip = get_client_ip(request)
    AuditService.log_risk_assessment(
        db, merchant_id, new_score, override_request.new_risk_level.value,
        merchant.risk_reasons, is_override=True,
        ip_address=client_ip, user_id=override_request.override_by
    )
    
    db.commit()
    db.refresh(merchant)
    
    return RiskAssessmentResponse(
        merchant_id=merchant.merchant_id,
        risk_score=merchant.risk_score,
        risk_level=merchant.risk_level,
        risk_reasons=merchant.risk_reasons,
        assessed_at=merchant.last_assessment_date,
        input_summary={
            "previous_level": previous_level,
            "previous_score": previous_score
        },
        applied_rules=["MANUAL_OVERRIDE"],
        is_override=True,
        override_reason=override_request.reason
    )


@router.get("/merchants/{merchant_id}/risk/history", tags=["Risk Assessment"])
async def get_risk_history(
    merchant_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get historical risk assessments for a merchant.
    """
    assessments = db.query(RiskAssessment).filter(
        RiskAssessment.merchant_id == merchant_id
    ).order_by(desc(RiskAssessment.assessed_at)).limit(limit).all()
    
    return [{
        "id": a.id,
        "risk_score": a.risk_score,
        "risk_level": a.risk_level,
        "risk_reasons": a.risk_reasons,
        "assessed_at": a.assessed_at,
        "assessed_by": a.assessed_by,
        "is_override": a.is_override,
        "override_reason": a.override_reason
    } for a in assessments]


# === Configuration Endpoints ===

@router.get("/config/weights", tags=["Configuration"])
async def get_risk_weights(db: Session = Depends(get_db)):
    """Get current risk factor weights."""
    weights = RiskEngineService.get_risk_weights(db)
    return {"weights": weights}


@router.put("/config/weights", tags=["Configuration"])
async def update_risk_weights(
    weights_update: RiskWeightsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Update risk factor weights (admin only)."""
    # Get current weights for audit
    current_weights = RiskEngineService.get_risk_weights(db)
    
    # Update or create config
    config = db.query(RiskConfiguration).filter(
        RiskConfiguration.config_key == "risk_weights"
    ).first()
    
    if config:
        config.config_value = weights_update.weights
        config.updated_at = datetime.utcnow()
    else:
        config = RiskConfiguration(
            config_key="risk_weights",
            config_value=weights_update.weights,
            config_type="WEIGHT",
            description="Risk factor weights"
        )
        db.add(config)
    
    # Log change
    client_ip = get_client_ip(request)
    AuditService.log_config_change(
        db, "risk_weights", current_weights, weights_update.weights,
        ip_address=client_ip
    )
    
    db.commit()
    
    return {"message": "Risk weights updated", "weights": weights_update.weights}


@router.get("/config/thresholds", tags=["Configuration"])
async def get_risk_thresholds(db: Session = Depends(get_db)):
    """Get current risk level thresholds."""
    thresholds = RiskEngineService.get_risk_thresholds(db)
    return {"thresholds": thresholds}


@router.put("/config/thresholds", tags=["Configuration"])
async def update_risk_thresholds(
    thresholds_update: RiskThresholdsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Update risk level thresholds (admin only)."""
    current = RiskEngineService.get_risk_thresholds(db)
    new_thresholds = thresholds_update.model_dump()
    
    config = db.query(RiskConfiguration).filter(
        RiskConfiguration.config_key == "risk_thresholds"
    ).first()
    
    if config:
        config.config_value = new_thresholds
        config.updated_at = datetime.utcnow()
    else:
        config = RiskConfiguration(
            config_key="risk_thresholds",
            config_value=new_thresholds,
            config_type="THRESHOLD"
        )
        db.add(config)
    
    client_ip = get_client_ip(request)
    AuditService.log_config_change(
        db, "risk_thresholds", current, new_thresholds,
        ip_address=client_ip
    )
    
    db.commit()
    
    return {"message": "Thresholds updated", "thresholds": new_thresholds}


@router.get("/config/lists", tags=["Configuration"])
async def get_risk_lists(db: Session = Depends(get_db)):
    """Get all configured risk lists (countries, industries, MCCs)."""
    return {
        "high_risk_countries": RiskEngineService.get_high_risk_countries(db),
        "high_risk_industries": RiskEngineService.get_high_risk_industries(db),
        "blacklisted_mccs": RiskEngineService.get_blacklisted_mccs(db)
    }


@router.put("/config/lists", tags=["Configuration"])
async def update_risk_list(
    list_update: BlacklistUpdate,
    request: Request,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Update a risk list (admin only)."""
    list_type_map = {
        "countries": "high_risk_countries",
        "industries": "high_risk_industries",
        "mccs": "blacklisted_mccs"
    }
    
    config_key = list_type_map.get(list_update.list_type)
    if not config_key:
        raise HTTPException(status_code=400, detail="Invalid list type")
    
    config = db.query(RiskConfiguration).filter(
        RiskConfiguration.config_key == config_key
    ).first()
    
    if config:
        previous = config.config_value
        config.config_value = list_update.items
        config.updated_at = datetime.utcnow()
    else:
        previous = []
        config = RiskConfiguration(
            config_key=config_key,
            config_value=list_update.items,
            config_type="LIST"
        )
        db.add(config)
    
    client_ip = get_client_ip(request)
    AuditService.log_config_change(
        db, config_key, previous, list_update.items,
        ip_address=client_ip
    )
    
    db.commit()
    
    return {"message": f"{config_key} updated", "items": list_update.items}


# === Alert Endpoints ===

@router.get("/alerts", response_model=List[AlertResponse], tags=["Alerts"])
async def list_alerts(
    resolved: Optional[bool] = Query(None, description="Filter by resolved status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """List alerts with optional filtering."""
    query = db.query(Alert)
    
    if resolved is not None:
        query = query.filter(Alert.is_resolved == resolved)
    if severity:
        query = query.filter(Alert.severity == severity.upper())
    
    alerts = query.order_by(desc(Alert.created_at)).limit(limit).all()
    return alerts


@router.post("/alerts/{alert_id}/resolve", response_model=AlertResponse, tags=["Alerts"])
async def resolve_alert(
    alert_id: int,
    resolve_request: AlertResolveRequest,
    request: Request,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Resolve an alert (admin only)."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    if alert.is_resolved:
        raise HTTPException(status_code=400, detail="Alert already resolved")
    
    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    alert.resolved_by = resolve_request.resolved_by
    alert.resolution_notes = resolve_request.resolution_notes
    
    client_ip = get_client_ip(request)
    AuditService.log_alert_action(
        db, alert_id, "RESOLVED", alert.merchant_id,
        {"resolved_by": resolve_request.resolved_by, "notes": resolve_request.resolution_notes},
        ip_address=client_ip
    )
    
    db.commit()
    db.refresh(alert)
    
    return alert


# === Audit Endpoints ===

@router.get("/audit/logs", response_model=List[AuditLogResponse], tags=["Audit"])
async def get_audit_logs(
    merchant_id: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get audit logs (admin only).
    """
    if merchant_id:
        logs = AuditService.get_merchant_audit_trail(db, merchant_id, limit)
    else:
        logs = AuditService.get_recent_audit_logs(db, action_type, hours, limit)
    
    return logs


@router.get("/audit/config-history", tags=["Audit"])
async def get_config_history(
    config_key: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get configuration change history for audit (admin only).
    """
    logs = AuditService.get_config_change_history(db, config_key, limit)
    return [{
        "id": log.id,
        "action_type": log.action_type,
        "previous_value": log.previous_value,
        "new_value": log.new_value,
        "user_id": log.user_id,
        "created_at": log.created_at
    } for log in logs]


# === Dashboard/Stats Endpoints ===

@router.get("/dashboard/stats", response_model=DashboardStats, tags=["Dashboard"])
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Get dashboard statistics for overview.
    """
    # Total merchants
    total = db.query(func.count(Merchant.id)).scalar()
    
    # By risk level
    risk_counts = db.query(
        Merchant.risk_level, func.count(Merchant.id)
    ).group_by(Merchant.risk_level).all()
    risk_by_level = {level: count for level, count in risk_counts}
    
    # By status
    status_counts = db.query(
        Merchant.status, func.count(Merchant.id)
    ).group_by(Merchant.status).all()
    status_by_status = {status: count for status, count in status_counts}
    
    # Recent high-risk (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_high = db.query(func.count(Merchant.id)).filter(
        Merchant.risk_level.in_(["HIGH", "CRITICAL"]),
        Merchant.created_at >= week_ago
    ).scalar()
    
    # Unresolved alerts
    unresolved_alerts = db.query(func.count(Alert.id)).filter(
        Alert.is_resolved == False
    ).scalar()
    
    # Average risk score
    avg_score = db.query(func.avg(Merchant.risk_score)).scalar() or 0
    
    # High-risk countries breakdown
    high_risk_countries = db.query(
        Merchant.country, func.count(Merchant.id)
    ).filter(
        Merchant.risk_level.in_(["HIGH", "CRITICAL"])
    ).group_by(Merchant.country).order_by(desc(func.count(Merchant.id))).limit(10).all()
    
    # Recent assessments
    recent_assessments = db.query(RiskAssessment).order_by(
        desc(RiskAssessment.assessed_at)
    ).limit(10).all()
    
    return DashboardStats(
        total_merchants=total,
        merchants_by_risk_level=risk_by_level,
        merchants_by_status=status_by_status,
        recent_high_risk_count=recent_high,
        unresolved_alerts_count=unresolved_alerts,
        average_risk_score=round(avg_score, 2),
        high_risk_countries=[{"country": c, "count": n} for c, n in high_risk_countries],
        recent_assessments=[{
            "merchant_id": a.merchant_id,
            "risk_score": a.risk_score,
            "risk_level": a.risk_level,
            "assessed_at": a.assessed_at.isoformat()
        } for a in recent_assessments]
    )
