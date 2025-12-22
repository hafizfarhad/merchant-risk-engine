"""
Audit Service - Logging and tracking all system actions.
Provides complete audit trail for GRC compliance.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging

from ..models import AuditLog, RiskConfiguration

logger = logging.getLogger(__name__)


class AuditService:
    """
    Service for creating and querying audit logs.
    Ensures complete traceability of all system actions.
    """

    @staticmethod
    def log_action(
        db: Session,
        action_type: str,
        action_description: str,
        merchant_id: Optional[str] = None,
        previous_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        endpoint: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> AuditLog:
        """
        Create an audit log entry.
        
        Args:
            db: Database session
            action_type: Type of action (CREATE, UPDATE, DELETE, ASSESS, CONFIG_CHANGE, etc.)
            action_description: Human-readable description of the action
            merchant_id: Related merchant ID if applicable
            previous_value: Previous state before change
            new_value: New state after change
            endpoint: API endpoint that triggered the action
            ip_address: Client IP address
            user_agent: Client user agent
            user_id: ID of user performing the action
            
        Returns:
            Created AuditLog instance
        """
        audit_log = AuditLog(
            merchant_id=merchant_id,
            action_type=action_type,
            action_description=action_description,
            previous_value=previous_value,
            new_value=new_value,
            endpoint=endpoint,
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user_id
        )
        
        db.add(audit_log)
        db.flush()  # Get the ID without committing
        
        logger.info(f"Audit log created: {action_type} - {action_description}")
        
        return audit_log

    @staticmethod
    def log_merchant_create(
        db: Session,
        merchant_id: str,
        merchant_data: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> AuditLog:
        """Log merchant creation."""
        return AuditService.log_action(
            db=db,
            action_type="MERCHANT_CREATE",
            action_description=f"Merchant {merchant_id} created/onboarded",
            merchant_id=merchant_id,
            new_value=merchant_data,
            ip_address=ip_address,
            user_id=user_id,
            endpoint="POST /merchants"
        )

    @staticmethod
    def log_merchant_update(
        db: Session,
        merchant_id: str,
        previous_data: Dict[str, Any],
        new_data: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> AuditLog:
        """Log merchant update."""
        return AuditService.log_action(
            db=db,
            action_type="MERCHANT_UPDATE",
            action_description=f"Merchant {merchant_id} updated",
            merchant_id=merchant_id,
            previous_value=previous_data,
            new_value=new_data,
            ip_address=ip_address,
            user_id=user_id,
            endpoint=f"PUT /merchants/{merchant_id}"
        )

    @staticmethod
    def log_risk_assessment(
        db: Session,
        merchant_id: str,
        risk_score: int,
        risk_level: str,
        reasons: List[str],
        is_override: bool = False,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> AuditLog:
        """Log risk assessment."""
        action_type = "RISK_OVERRIDE" if is_override else "RISK_ASSESSMENT"
        
        return AuditService.log_action(
            db=db,
            action_type=action_type,
            action_description=f"Merchant {merchant_id} assessed: Score={risk_score}, Level={risk_level}",
            merchant_id=merchant_id,
            new_value={
                "risk_score": risk_score,
                "risk_level": risk_level,
                "reasons": reasons,
                "is_override": is_override
            },
            ip_address=ip_address,
            user_id=user_id,
            endpoint=f"GET /merchants/{merchant_id}/risk"
        )

    @staticmethod
    def log_config_change(
        db: Session,
        config_key: str,
        previous_value: Any,
        new_value: Any,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> AuditLog:
        """Log configuration change."""
        return AuditService.log_action(
            db=db,
            action_type="CONFIG_CHANGE",
            action_description=f"Configuration '{config_key}' updated",
            previous_value={"config_key": config_key, "value": previous_value},
            new_value={"config_key": config_key, "value": new_value},
            ip_address=ip_address,
            user_id=user_id,
            endpoint="PUT /config/*"
        )

    @staticmethod
    def log_alert_action(
        db: Session,
        alert_id: int,
        action: str,
        merchant_id: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> AuditLog:
        """Log alert creation or resolution."""
        return AuditService.log_action(
            db=db,
            action_type=f"ALERT_{action.upper()}",
            action_description=f"Alert {alert_id} {action.lower()} for merchant {merchant_id}",
            merchant_id=merchant_id,
            new_value=details,
            ip_address=ip_address,
            user_id=user_id
        )

    @staticmethod
    def get_merchant_audit_trail(
        db: Session,
        merchant_id: str,
        limit: int = 100
    ) -> List[AuditLog]:
        """Get audit trail for a specific merchant."""
        return db.query(AuditLog).filter(
            AuditLog.merchant_id == merchant_id
        ).order_by(desc(AuditLog.created_at)).limit(limit).all()

    @staticmethod
    def get_recent_audit_logs(
        db: Session,
        action_type: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[AuditLog]:
        """Get recent audit logs with optional filtering."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        query = db.query(AuditLog).filter(AuditLog.created_at >= cutoff)
        
        if action_type:
            query = query.filter(AuditLog.action_type == action_type)
        
        return query.order_by(desc(AuditLog.created_at)).limit(limit).all()

    @staticmethod
    def get_config_change_history(
        db: Session,
        config_key: Optional[str] = None,
        limit: int = 50
    ) -> List[AuditLog]:
        """Get history of configuration changes for audit."""
        query = db.query(AuditLog).filter(AuditLog.action_type == "CONFIG_CHANGE")
        
        if config_key:
            # Filter by config key in the new_value JSON
            query = query.filter(
                AuditLog.new_value.contains({"config_key": config_key})
            )
        
        return query.order_by(desc(AuditLog.created_at)).limit(limit).all()
