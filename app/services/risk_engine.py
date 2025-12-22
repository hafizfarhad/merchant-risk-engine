"""
Risk Engine Service - Core risk scoring and assessment logic.
Implements rule-based risk evaluation with FATF-style factors.
"""

from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from ..models import Merchant, RiskAssessment, AuditLog, RiskConfiguration, Alert, RiskLevel
from ..config import (
    FATF_HIGH_RISK_COUNTRIES, HIGH_RISK_INDUSTRIES, BLACKLISTED_MCCS,
    DEFAULT_RISK_WEIGHTS, DEFAULT_RISK_THRESHOLDS, HARD_OVERRIDE_RULES
)

logger = logging.getLogger(__name__)


class RiskEngineService:
    """
    Core risk scoring engine for merchant AML assessment.
    Computes risk scores based on configurable rules and weights.
    """

    @staticmethod
    def get_risk_weights(db: Session) -> Dict[str, int]:
        """Get current risk weights from config or defaults."""
        config = db.query(RiskConfiguration).filter(
            RiskConfiguration.config_key == "risk_weights",
            RiskConfiguration.is_active == True
        ).first()
        
        if config:
            return config.config_value
        return DEFAULT_RISK_WEIGHTS

    @staticmethod
    def get_risk_thresholds(db: Session) -> Dict[str, int]:
        """Get current risk thresholds from config or defaults."""
        config = db.query(RiskConfiguration).filter(
            RiskConfiguration.config_key == "risk_thresholds",
            RiskConfiguration.is_active == True
        ).first()
        
        if config:
            return config.config_value
        return DEFAULT_RISK_THRESHOLDS

    @staticmethod
    def get_high_risk_countries(db: Session) -> List[str]:
        """Get current high-risk countries list."""
        config = db.query(RiskConfiguration).filter(
            RiskConfiguration.config_key == "high_risk_countries",
            RiskConfiguration.is_active == True
        ).first()
        
        if config:
            return config.config_value
        return FATF_HIGH_RISK_COUNTRIES

    @staticmethod
    def get_high_risk_industries(db: Session) -> List[str]:
        """Get current high-risk industries list."""
        config = db.query(RiskConfiguration).filter(
            RiskConfiguration.config_key == "high_risk_industries",
            RiskConfiguration.is_active == True
        ).first()
        
        if config:
            return config.config_value
        return HIGH_RISK_INDUSTRIES

    @staticmethod
    def get_blacklisted_mccs(db: Session) -> List[str]:
        """Get current blacklisted MCCs."""
        config = db.query(RiskConfiguration).filter(
            RiskConfiguration.config_key == "blacklisted_mccs",
            RiskConfiguration.is_active == True
        ).first()
        
        if config:
            return config.config_value
        return BLACKLISTED_MCCS

    @classmethod
    def assess_merchant_risk(
        cls,
        db: Session,
        merchant: Merchant,
        assessed_by: str = "SYSTEM"
    ) -> Tuple[int, str, List[str], List[str]]:
        """
        Perform comprehensive risk assessment for a merchant.
        
        Returns:
            Tuple of (risk_score, risk_level, reason_codes, applied_rules)
        """
        # Load current configuration
        weights = cls.get_risk_weights(db)
        thresholds = cls.get_risk_thresholds(db)
        high_risk_countries = cls.get_high_risk_countries(db)
        high_risk_industries = cls.get_high_risk_industries(db)
        blacklisted_mccs = cls.get_blacklisted_mccs(db)
        
        risk_score = 0
        reasons: List[str] = []
        applied_rules: List[str] = []
        
        # === Check for Hard Overrides First ===
        
        # Sanctioned owner - automatic CRITICAL
        if merchant.owner_sanctioned:
            return (
                100,
                RiskLevel.CRITICAL.value,
                ["Owner on sanctions list - automatic CRITICAL risk"],
                ["HARD_OVERRIDE: owner_sanctioned"]
            )
        
        # === Evaluate Risk Factors ===
        
        # 1. Country Risk (FATF)
        if merchant.country in high_risk_countries:
            risk_score += weights.get("high_risk_country", 30)
            reasons.append(f"High-risk country: {merchant.country}")
            applied_rules.append("RULE: high_risk_country")
        
        # 2. Industry Risk
        if merchant.industry in high_risk_industries:
            risk_score += weights.get("high_risk_industry", 25)
            reasons.append(f"High-risk industry: {merchant.industry}")
            applied_rules.append("RULE: high_risk_industry")
        
        # 3. MCC Risk
        if merchant.mcc_code and merchant.mcc_code in blacklisted_mccs:
            risk_score += weights.get("blacklisted_mcc", 35)
            reasons.append(f"Blacklisted MCC: {merchant.mcc_code}")
            applied_rules.append("RULE: blacklisted_mcc")
        
        # 4. PEP Owner
        if merchant.owner_pep:
            risk_score += weights.get("owner_pep", 50)
            reasons.append("Owner is Politically Exposed Person (PEP)")
            applied_rules.append("RULE: owner_pep")
            
            # Combined PEP + High-risk country = Hard override to HIGH
            if merchant.country in high_risk_countries:
                return (
                    max(risk_score, thresholds.get("high_min", 61)),
                    RiskLevel.HIGH.value,
                    reasons + ["PEP owner in high-risk country - elevated to HIGH"],
                    applied_rules + ["HARD_OVERRIDE: owner_pep_high_risk_country"]
                )
        
        # 5. High Annual Volume (> $1M considered higher risk for AML)
        if merchant.annual_volume > 1000000:
            risk_score += weights.get("high_annual_volume", 15)
            reasons.append(f"High annual volume: ${merchant.annual_volume:,.2f}")
            applied_rules.append("RULE: high_annual_volume")
        
        # 6. New Business (< 2 years)
        if merchant.years_in_business < 2:
            risk_score += weights.get("new_business", 10)
            reasons.append(f"New business: {merchant.years_in_business} years")
            applied_rules.append("RULE: new_business")
        
        # 7. Offshore Structure
        if merchant.offshore_structure:
            risk_score += weights.get("offshore_structure", 25)
            reasons.append("Offshore corporate structure")
            applied_rules.append("RULE: offshore_structure")
        
        # 8. Cash Intensive
        if merchant.cash_intensive:
            risk_score += weights.get("cash_intensive", 20)
            reasons.append("Cash-intensive business")
            applied_rules.append("RULE: cash_intensive")
        
        # 9. Complex Ownership
        if merchant.complex_ownership:
            risk_score += weights.get("complex_ownership", 15)
            reasons.append("Complex ownership structure")
            applied_rules.append("RULE: complex_ownership")
        
        # 10. High Refund Rate (> 5% considered suspicious)
        if merchant.refund_rate > 5.0:
            risk_score += weights.get("high_refund_rate", 20)
            reasons.append(f"High refund rate: {merchant.refund_rate:.1f}%")
            applied_rules.append("RULE: high_refund_rate")
        
        # 11. Abnormal Volume Spike (> 50% month-over-month increase)
        if merchant.volume_change_pct > 50.0:
            risk_score += weights.get("abnormal_volume_spike", 25)
            reasons.append(f"Abnormal volume spike: {merchant.volume_change_pct:.1f}% increase")
            applied_rules.append("RULE: abnormal_volume_spike")
        
        # 12. High Chargeback Rate (> 1% is concerning)
        if merchant.chargeback_rate > 1.0:
            risk_score += int(merchant.chargeback_rate * 10)  # Dynamic weight
            reasons.append(f"High chargeback rate: {merchant.chargeback_rate:.2f}%")
            applied_rules.append("RULE: high_chargeback_rate")
        
        # === Cap score at 100 ===
        risk_score = min(risk_score, 100)
        
        # === Determine Risk Level ===
        risk_level = cls.calculate_risk_level(risk_score, thresholds)
        
        # Add default reason if no factors found
        if not reasons:
            reasons.append("No high-risk factors identified")
        
        return risk_score, risk_level, reasons, applied_rules

    @staticmethod
    def calculate_risk_level(score: int, thresholds: Dict[str, int]) -> str:
        """Calculate risk level from score using thresholds."""
        if score >= thresholds.get("critical_min", 85):
            return RiskLevel.CRITICAL.value
        elif score >= thresholds.get("high_min", 61):
            return RiskLevel.HIGH.value
        elif score > thresholds.get("low_max", 30):
            return RiskLevel.MEDIUM.value
        else:
            return RiskLevel.LOW.value

    @classmethod
    def record_assessment(
        cls,
        db: Session,
        merchant: Merchant,
        risk_score: int,
        risk_level: str,
        reasons: List[str],
        applied_rules: List[str],
        assessed_by: str = "SYSTEM",
        is_override: bool = False,
        override_reason: Optional[str] = None
    ) -> RiskAssessment:
        """Create and store a risk assessment record for audit."""
        
        # Create input snapshot
        input_data = {
            "merchant_id": merchant.merchant_id,
            "country": merchant.country,
            "industry": merchant.industry,
            "mcc_code": merchant.mcc_code,
            "annual_volume": merchant.annual_volume,
            "owner_pep": merchant.owner_pep,
            "owner_sanctioned": merchant.owner_sanctioned,
            "years_in_business": merchant.years_in_business,
            "offshore_structure": merchant.offshore_structure,
            "cash_intensive": merchant.cash_intensive,
            "complex_ownership": merchant.complex_ownership,
            "refund_rate": merchant.refund_rate,
            "chargeback_rate": merchant.chargeback_rate,
            "volume_change_pct": merchant.volume_change_pct,
        }
        
        # Get current config for audit
        weights = cls.get_risk_weights(db)
        thresholds = cls.get_risk_thresholds(db)
        
        assessment = RiskAssessment(
            merchant_id=merchant.merchant_id,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_reasons=reasons,
            input_data=input_data,
            applied_rules=applied_rules,
            weights_used=weights,
            thresholds_used=thresholds,
            is_override=is_override,
            override_reason=override_reason,
            assessed_by=assessed_by
        )
        
        db.add(assessment)
        return assessment

    @classmethod
    def create_alert_if_needed(
        cls,
        db: Session,
        merchant: Merchant,
        risk_level: str,
        reasons: List[str]
    ) -> Optional[Alert]:
        """Create an alert for high-risk or critical merchants."""
        
        if risk_level not in [RiskLevel.HIGH.value, RiskLevel.CRITICAL.value]:
            return None
        
        severity = "CRITICAL" if risk_level == RiskLevel.CRITICAL.value else "WARNING"
        alert_type = f"{risk_level}_RISK_DETECTED"
        
        alert = Alert(
            merchant_id=merchant.merchant_id,
            alert_type=alert_type,
            severity=severity,
            title=f"{risk_level} Risk Merchant Detected: {merchant.business_name}",
            description=f"Merchant {merchant.merchant_id} assessed as {risk_level} risk. Reasons: {'; '.join(reasons)}"
        )
        
        db.add(alert)
        logger.warning(f"Alert created for merchant {merchant.merchant_id}: {alert_type}")
        
        return alert

    @staticmethod
    def initialize_default_config(db: Session):
        """Initialize default configurations if not present."""
        
        configs = [
            {
                "config_key": "risk_weights",
                "config_value": DEFAULT_RISK_WEIGHTS,
                "config_type": "WEIGHT",
                "description": "Risk factor weights for score calculation"
            },
            {
                "config_key": "risk_thresholds",
                "config_value": DEFAULT_RISK_THRESHOLDS,
                "config_type": "THRESHOLD",
                "description": "Risk level threshold boundaries"
            },
            {
                "config_key": "high_risk_countries",
                "config_value": FATF_HIGH_RISK_COUNTRIES,
                "config_type": "LIST",
                "description": "FATF high-risk and monitored countries"
            },
            {
                "config_key": "high_risk_industries",
                "config_value": HIGH_RISK_INDUSTRIES,
                "config_type": "LIST",
                "description": "Industries with elevated AML risk"
            },
            {
                "config_key": "blacklisted_mccs",
                "config_value": BLACKLISTED_MCCS,
                "config_type": "LIST",
                "description": "Blacklisted Merchant Category Codes"
            }
        ]
        
        for config_data in configs:
            existing = db.query(RiskConfiguration).filter(
                RiskConfiguration.config_key == config_data["config_key"]
            ).first()
            
            if not existing:
                config = RiskConfiguration(**config_data)
                db.add(config)
                logger.info(f"Initialized config: {config_data['config_key']}")
