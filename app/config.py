"""
Configuration settings for the Merchant Risk & AML Scoring Engine.
Contains risk factors, thresholds, and security settings.
"""

from pydantic_settings import BaseSettings
from typing import List, Dict
import secrets


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    APP_NAME: str = "Merchant Risk & AML Scoring Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    API_KEY_HEADER: str = "X-API-Key"
    ADMIN_API_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str = "sqlite:///./merchant_risk.db"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


# FATF High-Risk Countries (Sample list based on FATF guidance)
FATF_HIGH_RISK_COUNTRIES = [
    "North Korea", "Iran", "Myanmar", "Syria", "Yemen",
    "Afghanistan", "Albania", "Barbados", "Burkina Faso", 
    "Cambodia", "Cayman Islands", "Haiti", "Jamaica", 
    "Jordan", "Mali", "Morocco", "Nicaragua", "Pakistan",
    "Panama", "Philippines", "Senegal", "South Sudan",
    "Tanzania", "Turkey", "Uganda", "United Arab Emirates",
    "Vietnam", "Zimbabwe"
]

# High-Risk Industries for AML (Based on sanctions.io and FATF guidance)
HIGH_RISK_INDUSTRIES = [
    "Gambling", "Casino", "Gaming",
    "CurrencyExchange", "MoneyServices", "CryptoExchange",
    "RealEstate", "HighValueGoods", "JewelryDealer",
    "ArtDealer", "PreciousMetals",
    "Arms", "Defense", "Weapons",
    "AdultEntertainment",
    "CharityNonProfit",  # Can be used for illicit finance
    "PaymentProcessor", "MoneyRemittance",
    "TobaccoAlcohol",
    "UsedCarDealer", "BoatDealer",
    "TravelAgency",
    "LegalServices", "AccountingServices"
]

# Blacklisted Merchant Category Codes (MCCs)
BLACKLISTED_MCCS = [
    "7995",  # Gambling
    "7994",  # Video game arcades
    "7801",  # Government-owned lotteries
    "7802",  # Government-licensed horse/dog racing
    "5933",  # Pawn shops
    "5944",  # Jewelry stores (high-value)
    "6051",  # Non-financial institutions – foreign currency
    "6211",  # Security brokers/dealers
    "4829",  # Wire transfers
    "6540",  # Non-financial institutions – stored value
]

# Default Risk Scoring Weights
DEFAULT_RISK_WEIGHTS = {
    "high_risk_country": 30,
    "fatf_grey_list_country": 20,
    "high_risk_industry": 25,
    "blacklisted_mcc": 35,
    "owner_pep": 50,
    "owner_sanctioned": 100,  # Automatic high risk
    "high_annual_volume": 15,
    "new_business": 10,
    "offshore_structure": 25,
    "cash_intensive": 20,
    "complex_ownership": 15,
    "high_refund_rate": 20,
    "abnormal_volume_spike": 25,
}

# Risk Level Thresholds
DEFAULT_RISK_THRESHOLDS = {
    "low_max": 30,       # 0-30 = Low Risk
    "medium_max": 60,    # 31-60 = Medium Risk
    "high_min": 61,      # 61+ = High Risk
    "critical_min": 85   # 85+ = Critical Risk (auto-reject)
}

# Hard Override Rules (these automatically set risk level regardless of score)
HARD_OVERRIDE_RULES = {
    "owner_sanctioned": "CRITICAL",
    "owner_pep_high_risk_country": "HIGH",
    "blacklisted_mcc_high_volume": "HIGH"
}
