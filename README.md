# Merchant Risk & AML Scoring Engine

A FastAPI-based risk control system for GRC (Governance, Risk, and Compliance) projects.

## Features

- **Merchant Onboarding**: Register merchants with comprehensive KYC data
- **Risk Assessment**: Automatic risk scoring using FATF-style rules
- **Configurable Rules**: Adjust risk weights, thresholds, and blacklists at runtime
- **Audit Trail**: Complete logging of all actions and decisions for compliance
- **Alert Management**: Automatic alerts for high-risk merchants
- **Dashboard**: Web-based UI for monitoring and management

## Risk Factors

The engine evaluates merchants based on:
- **Geographic Risk**: FATF high-risk and non-cooperative jurisdictions
- **Industry Risk**: High-risk industries (gambling, crypto, etc.)
- **MCC Risk**: Blacklisted Merchant Category Codes
- **PEP Status**: Politically Exposed Persons
- **Sanctions**: Owner sanctions screening
- **Business Characteristics**: Offshore structures, cash-intensive operations
- **Behavioral Signals**: Refund rates, volume spikes, chargebacks

## Quick Start

1. **Install dependencies**:
```bash
cd merchant_risk_engine
pip install -r requirements.txt
```

2. **Run the server**:
```bash
uvicorn app.main:app --reload --port 8001
```

3. **Access the application**:
- Dashboard: http://localhost:8001
- API Docs: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## API Endpoints

### Merchants
- `POST /api/v1/merchants` - Onboard a new merchant
- `GET /api/v1/merchants` - List all merchants
- `GET /api/v1/merchants/{id}` - Get merchant details
- `PUT /api/v1/merchants/{id}` - Update merchant
- `DELETE /api/v1/merchants/{id}` - Delete merchant (admin)

### Risk Assessment
- `GET /api/v1/merchants/{id}/risk` - Get current risk assessment
- `POST /api/v1/merchants/{id}/risk/override` - Manual risk override (admin)
- `GET /api/v1/merchants/{id}/risk/history` - Risk assessment history

### Configuration
- `GET /api/v1/config/weights` - Get risk weights
- `PUT /api/v1/config/weights` - Update risk weights (admin)
- `GET /api/v1/config/thresholds` - Get risk thresholds
- `PUT /api/v1/config/thresholds` - Update thresholds (admin)
- `GET /api/v1/config/lists` - Get risk lists
- `PUT /api/v1/config/lists` - Update risk lists (admin)

### Alerts
- `GET /api/v1/alerts` - List alerts
- `POST /api/v1/alerts/{id}/resolve` - Resolve alert (admin)

### Audit
- `GET /api/v1/audit/logs` - Get audit logs (admin)
- `GET /api/v1/audit/config-history` - Config change history (admin)

### Dashboard
- `GET /api/v1/dashboard/stats` - Dashboard statistics

## Authentication

Protected endpoints require the `X-API-Key` header. The admin API key is printed in the server logs at startup.

## Example Usage

```bash
# Onboard a merchant
curl -X POST http://localhost:8001/api/v1/merchants \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "M001",
    "business_name": "Test Corp",
    "country": "Iran",
    "industry": "Gambling",
    "owner_pep": true,
    "annual_volume": 500000
  }'

# Get risk assessment
curl http://localhost:8001/api/v1/merchants/M001/risk
```

## Architecture

```
merchant_risk_engine/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── config.py         # Configuration and constants
│   ├── database.py       # Database setup
│   ├── models.py         # SQLAlchemy models
│   ├── schemas.py        # Pydantic schemas
│   ├── security.py       # Authentication
│   ├── routes/
│   │   ├── __init__.py
│   │   └── api.py        # API routes
│   └── services/
│       ├── __init__.py
│       ├── risk_engine.py    # Risk scoring logic
│       └── audit_service.py  # Audit logging
├── requirements.txt
└── README.md
```

## License

MIT
