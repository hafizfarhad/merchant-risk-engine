# Merchant Risk & AML Scoring Engine

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)

A comprehensive **Anti-Money Laundering (AML) Risk Scoring Engine** built with FastAPI for GRC (Governance, Risk, and Compliance) projects. This system automates merchant risk assessment using FATF-compliant rules and provides real-time scoring, alerting, and audit capabilities.

## 🛡️ Tech Stack

| Technology | Purpose |
|------------|---------|
| **FastAPI** | High-performance async web framework |
| **SQLAlchemy** | ORM for database operations |
| **SQLite** | Lightweight database (configurable) |
| **Pydantic** | Data validation and serialization |
| **Uvicorn** | ASGI server |

## ✨ Features

- **Merchant Onboarding**: Register merchants with comprehensive KYC data
- **Real-time Risk Scoring**: Automatic risk scoring using 12+ FATF-style risk factors
- **Configurable Rules**: Adjust risk weights, thresholds, and blacklists at runtime via API
- **Hard Override Rules**: Automatic escalation for sanctions and combined risk factors
- **Complete Audit Trail**: Every action and decision logged for compliance
- **Alert Management**: Automatic alerts generated for HIGH/CRITICAL risk merchants
- **Web Dashboard**: Built-in UI for monitoring and management
- **RESTful API**: Full CRUD operations with OpenAPI documentation

## 📊 Risk Scoring Algorithm

### Risk Factors & Weights
cheezen miss kar rha
The engine evaluates merchants based on 12 configurable risk factors:

| Risk Factor | Default Weight | Description |
|-------------|----------------|-------------|
| 🌍 High-Risk Country | +30 | FATF high-risk jurisdictions |
| 🏭 High-Risk Industry | +25 | Gambling, crypto, money services |
| 🏷️ Blacklisted MCC | +35 | Prohibited merchant category codes |
| 👔 PEP Owner | +50 | Politically Exposed Person |
| ⛔ Sanctioned Owner | +100 | **Hard Override → CRITICAL** |
| 💰 High Annual Volume (>$1M) | +15 | Large transaction volumes |
| 🆕 New Business (<2 years) | +10 | Limited operating history |
| 🏝️ Offshore Structure | +25 | Complex international setup |
| 💵 Cash Intensive | +20 | High cash transaction ratio |
| 🔗 Complex Ownership | +15 | Opaque ownership structure |
| 🔄 High Refund Rate (>5%) | +20 | Suspicious refund patterns |
| 📈 Volume Spike (>50% MoM) | +25 | Abnormal transaction increase |
| 📉 High Chargeback Rate | Dynamic | `chargeback_rate × 10` |

### Risk Level Thresholds

| Score Range | Risk Level | Action |
|-------------|------------|--------|
| 0 - 30 | ✅ **LOW** | Auto-approve |
| 31 - 60 | ⚠️ **MEDIUM** | Standard review |
| 61 - 84 | 🔴 **HIGH** | Enhanced due diligence + Alert |
| 85 - 100 | ⛔ **CRITICAL** | Auto-reject + Critical Alert |

### Hard Override Rules

These rules bypass normal scoring and force specific risk levels:

| Condition | Forced Level |
|-----------|--------------|
| Owner on Sanctions List | → **CRITICAL** (Score: 100) |
| PEP + High-Risk Country | → **HIGH** (Minimum) |

## 🌍 FATF High-Risk Countries

The following countries are flagged based on FATF guidance:

```
North Korea, Iran, Myanmar, Syria, Yemen, Afghanistan, Albania, 
Barbados, Burkina Faso, Cambodia, Cayman Islands, Haiti, Jamaica, 
Jordan, Mali, Morocco, Nicaragua, Pakistan, Panama, Philippines, 
Senegal, South Sudan, Tanzania, Turkey, Uganda, UAE, Vietnam, Zimbabwe
```

## 🏭 High-Risk Industries

Industries with elevated AML risk:

```
Gambling, Casino, Gaming, CurrencyExchange, MoneyServices, CryptoExchange,
RealEstate, HighValueGoods, JewelryDealer, ArtDealer, PreciousMetals,
Arms, Defense, Weapons, AdultEntertainment, CharityNonProfit,
PaymentProcessor, MoneyRemittance, TobaccoAlcohol, UsedCarDealer,
BoatDealer, TravelAgency, LegalServices, AccountingServices
```

## 🏷️ Blacklisted MCCs

| MCC Code | Description |
|----------|-------------|
| 7995 | Gambling |
| 7994 | Video game arcades |
| 7801 | Government-owned lotteries |
| 7802 | Horse/dog racing |
| 5933 | Pawn shops |
| 5944 | Jewelry stores |
| 6051 | Foreign currency exchange |
| 6211 | Security brokers |
| 4829 | Wire transfers |
| 6540 | Stored value cards |

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- pip (Python package manager)

### Installation

1. **Clone and navigate to project**:
```bash
cd merchant_risk_engine
```

2. **Create virtual environment** (recommended):
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Run the server**:
```bash
uvicorn app.main:app --reload --port 8001
```

5. **Access the application**:
- 🖥️ Dashboard: http://localhost:8001
- 📚 API Docs (Swagger): http://localhost:8001/docs
- 📖 ReDoc: http://localhost:8001/redoc
- ❤️ Health Check: http://localhost:8001/health

## ⚙️ Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./merchant_risk.db` | Database connection string |
| `ADMIN_API_KEY` | Auto-generated | API key for admin endpoints |
| `SECRET_KEY` | Auto-generated | Application secret key |
| `DEBUG` | `False` | Enable debug mode |
| `ALLOWED_ORIGINS` | `["*"]` | CORS allowed origins |

Create a `.env` file in the root directory to override defaults:

```env
DATABASE_URL=sqlite:///./merchant_risk.db
ADMIN_API_KEY=your-secure-api-key
DEBUG=True
```

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

## 🔐 Authentication

Protected endpoints require the `X-API-Key` header. The admin API key is printed in the server logs at startup.

```bash
# Example authenticated request
curl -H "X-API-Key: your-admin-key" http://localhost:8001/api/v1/audit/logs
```

### Protected Endpoints
- All `PUT` and `DELETE` operations
- Risk override endpoints
- Configuration updates
- Audit log access

## 💡 Example Usage

### Onboard a High-Risk Merchant

```bash
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
```

**Expected Response:**
```json
{
  "merchant_id": "M001",
  "business_name": "Test Corp",
  "risk_score": 100,
  "risk_level": "CRITICAL",
  "risk_reasons": [
    "High-risk country: Iran",
    "High-risk industry: Gambling",
    "Owner is Politically Exposed Person (PEP)",
    "PEP owner in high-risk country - elevated to HIGH"
  ]
}
```

### Get Risk Assessment

```bash
curl http://localhost:8001/api/v1/merchants/M001/risk
```

### Update Risk Weights (Admin)

```bash
curl -X PUT http://localhost:8001/api/v1/config/weights \
  -H "X-API-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "high_risk_country": 35,
    "owner_pep": 60
  }'
```

### List High-Risk Merchants

```bash
curl "http://localhost:8001/api/v1/merchants?risk_level=HIGH"
```

## 🏗️ Architecture

```
merchant_risk_engine/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration, risk weights, FATF lists
│   ├── database.py          # Database connection and session
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── security.py          # API key authentication
│   ├── routes/
│   │   ├── __init__.py
│   │   └── api.py           # All REST API endpoints
│   └── services/
│       ├── __init__.py
│       ├── risk_engine.py   # 🎯 Core AML scoring logic
│       └── audit_service.py # Audit trail logging
├── requirements.txt
├── merchant_risk.db         # SQLite database (auto-created)
└── README.md
```

## 📦 Database Schema

### Merchants Table
Stores merchant KYC data and current risk assessment.

### Risk Assessments Table
Historical record of all risk assessments for audit trail.

### Audit Logs Table
Complete action log for compliance reporting.

### Risk Configuration Table
Runtime-configurable weights, thresholds, and blacklists.

### Alerts Table
Generated alerts for high-risk merchants.

## 🔄 Risk Assessment Flow

```
┌─────────────────────┐
│  Merchant Onboard   │
│  POST /merchants    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  RiskEngineService  │
│  assess_merchant()  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Check Hard Overrides│
│ (Sanctions, PEP+)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Evaluate 12 Factors │
│ Apply Weights       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Calculate Score     │
│ (Cap at 100)        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Determine Risk Level│
│ LOW/MED/HIGH/CRIT   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Create Alert if     │
│ HIGH or CRITICAL    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Log to Audit Trail  │
└─────────────────────┘
```

## 🧪 Testing

```bash
# Run with test merchant
python -c "
import requests
r = requests.post('http://localhost:8001/api/v1/merchants', json={
    'merchant_id': 'TEST001',
    'business_name': 'Low Risk Corp',
    'country': 'United States',
    'industry': 'Retail',
    'annual_volume': 100000
})
print(r.json())
"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

Built for GRC (Governance, Risk, and Compliance) projects.

---

<p align="center">
  <b>⭐ If this project helped you, please give it a star!</b>
</p>
