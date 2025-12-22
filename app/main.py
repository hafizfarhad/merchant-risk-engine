"""
Main FastAPI application for Merchant Risk & AML Scoring Engine.
Entry point for the web service with complete setup.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from contextlib import asynccontextmanager
import logging
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('merchant_risk_engine.log')
    ]
)
logger = logging.getLogger(__name__)

from .config import settings
from .database import init_database
from .routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    init_database()
    logger.info("Database initialized")
    
    # Print API key for testing (in production, this would be set via env vars)
    logger.info(f"Admin API Key: {settings.ADMIN_API_KEY}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## Merchant Risk & AML Scoring Engine
    
    A comprehensive risk assessment system for merchant onboarding and monitoring.
    
    ### Features:
    - **Merchant Onboarding**: Register merchants with KYC data
    - **Risk Assessment**: Automatic risk scoring using FATF-style rules
    - **Configurable Rules**: Adjust risk weights, thresholds, and blacklists
    - **Audit Trail**: Complete logging of all actions and decisions
    - **Alert Management**: Automatic alerts for high-risk merchants
    
    ### Authentication:
    Protected endpoints require the `X-API-Key` header.
    """,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


# Root endpoint with dashboard redirect
@app.get("/", response_class=HTMLResponse, tags=["Dashboard"])
async def root():
    """Serve the main dashboard."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Merchant Risk Engine - Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">
        <style>
            :root {
                --primary-color: #2c3e50;
                --danger-color: #e74c3c;
                --warning-color: #f39c12;
                --success-color: #27ae60;
                --info-color: #3498db;
            }
            body { background-color: #f8f9fa; }
            .sidebar { 
                background: linear-gradient(180deg, #2c3e50, #34495e);
                min-height: 100vh;
                position: fixed;
                width: 250px;
            }
            .sidebar .nav-link { color: rgba(255,255,255,0.8); padding: 12px 20px; }
            .sidebar .nav-link:hover { background: rgba(255,255,255,0.1); color: #fff; }
            .sidebar .nav-link.active { background: rgba(255,255,255,0.15); color: #fff; }
            .main-content { margin-left: 250px; padding: 20px; }
            .stat-card { 
                border: none; 
                border-radius: 12px; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.07);
                transition: transform 0.2s;
            }
            .stat-card:hover { transform: translateY(-2px); }
            .stat-card .stat-icon { font-size: 2.5rem; opacity: 0.3; }
            .risk-badge { padding: 6px 12px; border-radius: 20px; font-weight: 600; }
            .risk-low { background: #d4edda; color: #155724; }
            .risk-medium { background: #fff3cd; color: #856404; }
            .risk-high { background: #f8d7da; color: #721c24; }
            .risk-critical { background: #721c24; color: #fff; }
            .form-section { background: #fff; border-radius: 12px; padding: 25px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
            .table-container { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
            .api-key-display { background: #2c3e50; color: #fff; padding: 10px 15px; border-radius: 8px; font-family: monospace; word-break: break-all; }
            .progress-bar { transition: width 0.5s ease-in-out; }
        </style>
    </head>
    <body>
        <!-- Sidebar -->
        <nav class="sidebar d-flex flex-column">
            <div class="p-4">
                <h5 class="text-white mb-0"><i class="bi bi-shield-check me-2"></i>Risk Engine</h5>
                <small class="text-white-50">Merchant AML Scoring</small>
            </div>
            <hr class="text-white-50 mx-3">
            <ul class="nav flex-column">
                <li class="nav-item">
                    <a class="nav-link active" href="#" onclick="showSection('dashboard')"><i class="bi bi-speedometer2 me-2"></i>Dashboard</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#" onclick="showSection('merchants')"><i class="bi bi-building me-2"></i>Merchants</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#" onclick="showSection('onboard')"><i class="bi bi-plus-circle me-2"></i>Onboard Merchant</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#" onclick="showSection('alerts')"><i class="bi bi-bell me-2"></i>Alerts</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#" onclick="showSection('config')"><i class="bi bi-gear me-2"></i>Configuration</a>
                </li>
                <li class="nav-item">
                    <a class="nav-link" href="#" onclick="showSection('audit')"><i class="bi bi-journal-text me-2"></i>Audit Logs</a>
                </li>
            </ul>
            <div class="mt-auto p-3">
                <a href="/docs" class="btn btn-outline-light btn-sm w-100" target="_blank">
                    <i class="bi bi-code-slash me-1"></i>API Docs
                </a>
            </div>
        </nav>

        <!-- Main Content -->
        <div class="main-content">
            <!-- Dashboard Section -->
            <div id="section-dashboard" class="section">
                <h4 class="mb-4"><i class="bi bi-speedometer2 me-2"></i>Dashboard Overview</h4>
                
                <!-- Stats Cards -->
                <div class="row mb-4" id="stats-cards">
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card bg-white">
                            <div class="card-body d-flex justify-content-between align-items-center">
                                <div>
                                    <h6 class="text-muted mb-1">Total Merchants</h6>
                                    <h3 class="mb-0" id="stat-total">-</h3>
                                </div>
                                <i class="bi bi-building stat-icon text-primary"></i>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card bg-white">
                            <div class="card-body d-flex justify-content-between align-items-center">
                                <div>
                                    <h6 class="text-muted mb-1">High Risk</h6>
                                    <h3 class="mb-0" id="stat-high">-</h3>
                                </div>
                                <i class="bi bi-exclamation-triangle stat-icon text-danger"></i>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card bg-white">
                            <div class="card-body d-flex justify-content-between align-items-center">
                                <div>
                                    <h6 class="text-muted mb-1">Pending Alerts</h6>
                                    <h3 class="mb-0" id="stat-alerts">-</h3>
                                </div>
                                <i class="bi bi-bell stat-icon text-warning"></i>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card bg-white">
                            <div class="card-body d-flex justify-content-between align-items-center">
                                <div>
                                    <h6 class="text-muted mb-1">Avg Risk Score</h6>
                                    <h3 class="mb-0" id="stat-avg">-</h3>
                                </div>
                                <i class="bi bi-graph-up stat-icon text-info"></i>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Risk Distribution -->
                <div class="row mb-4">
                    <div class="col-md-6">
                        <div class="card form-section">
                            <h6 class="mb-3"><i class="bi bi-pie-chart me-2"></i>Risk Distribution</h6>
                            <div id="risk-distribution">
                                <div class="mb-2">
                                    <div class="d-flex justify-content-between mb-1">
                                        <span>Low Risk</span>
                                        <span id="dist-low">0</span>
                                    </div>
                                    <div class="progress" style="height: 10px;">
                                        <div class="progress-bar bg-success" id="bar-low" style="width: 0%"></div>
                                    </div>
                                </div>
                                <div class="mb-2">
                                    <div class="d-flex justify-content-between mb-1">
                                        <span>Medium Risk</span>
                                        <span id="dist-medium">0</span>
                                    </div>
                                    <div class="progress" style="height: 10px;">
                                        <div class="progress-bar bg-warning" id="bar-medium" style="width: 0%"></div>
                                    </div>
                                </div>
                                <div class="mb-2">
                                    <div class="d-flex justify-content-between mb-1">
                                        <span>High Risk</span>
                                        <span id="dist-high">0</span>
                                    </div>
                                    <div class="progress" style="height: 10px;">
                                        <div class="progress-bar bg-danger" id="bar-high" style="width: 0%"></div>
                                    </div>
                                </div>
                                <div class="mb-2">
                                    <div class="d-flex justify-content-between mb-1">
                                        <span>Critical Risk</span>
                                        <span id="dist-critical">0</span>
                                    </div>
                                    <div class="progress" style="height: 10px;">
                                        <div class="progress-bar bg-dark" id="bar-critical" style="width: 0%"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="card form-section">
                            <h6 class="mb-3"><i class="bi bi-clock-history me-2"></i>Recent Assessments</h6>
                            <div id="recent-assessments" style="max-height: 200px; overflow-y: auto;">
                                <p class="text-muted">Loading...</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Merchants Section -->
            <div id="section-merchants" class="section" style="display: none;">
                <h4 class="mb-4"><i class="bi bi-building me-2"></i>Merchants</h4>
                
                <!-- Filters -->
                <div class="form-section mb-4">
                    <div class="row g-3">
                        <div class="col-md-3">
                            <select class="form-select" id="filter-risk" onchange="loadMerchants()">
                                <option value="">All Risk Levels</option>
                                <option value="LOW">Low</option>
                                <option value="MEDIUM">Medium</option>
                                <option value="HIGH">High</option>
                                <option value="CRITICAL">Critical</option>
                            </select>
                        </div>
                        <div class="col-md-3">
                            <input type="text" class="form-control" id="filter-country" placeholder="Filter by country" onkeyup="loadMerchants()">
                        </div>
                        <div class="col-md-3">
                            <button class="btn btn-primary" onclick="loadMerchants()"><i class="bi bi-search me-1"></i>Search</button>
                        </div>
                    </div>
                </div>

                <div class="table-container">
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>Merchant ID</th>
                                    <th>Business Name</th>
                                    <th>Country</th>
                                    <th>Industry</th>
                                    <th>Risk Score</th>
                                    <th>Risk Level</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="merchants-table">
                                <tr><td colspan="7" class="text-center text-muted">Loading...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Onboard Section -->
            <div id="section-onboard" class="section" style="display: none;">
                <h4 class="mb-4"><i class="bi bi-plus-circle me-2"></i>Onboard New Merchant</h4>
                
                <div class="form-section">
                    <form id="onboard-form">
                        <div class="row g-3">
                            <div class="col-md-4">
                                <label class="form-label">Merchant ID *</label>
                                <input type="text" class="form-control" id="merchant_id" required placeholder="e.g., M001">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Business Name *</label>
                                <input type="text" class="form-control" id="business_name" required placeholder="Business legal name">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Country *</label>
                                <input type="text" class="form-control" id="country" required placeholder="e.g., United States">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Industry *</label>
                                <select class="form-select" id="industry" required>
                                    <option value="">Select industry</option>
                                    <option value="Retail">Retail</option>
                                    <option value="ECommerce">E-Commerce</option>
                                    <option value="PaymentProcessor">Payment Processor</option>
                                    <option value="Gambling">Gambling</option>
                                    <option value="CryptoExchange">Crypto Exchange</option>
                                    <option value="RealEstate">Real Estate</option>
                                    <option value="FinancialServices">Financial Services</option>
                                    <option value="Healthcare">Healthcare</option>
                                    <option value="Technology">Technology</option>
                                    <option value="Manufacturing">Manufacturing</option>
                                </select>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">MCC Code</label>
                                <input type="text" class="form-control" id="mcc_code" placeholder="e.g., 5411">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Annual Volume (USD)</label>
                                <input type="number" class="form-control" id="annual_volume" value="0" min="0">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Owner Name</label>
                                <input type="text" class="form-control" id="owner_name" placeholder="Primary owner name">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Years in Business</label>
                                <input type="number" class="form-control" id="years_in_business" value="0" min="0">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Refund Rate (%)</label>
                                <input type="number" class="form-control" id="refund_rate" value="0" min="0" max="100" step="0.1">
                            </div>
                            
                            <div class="col-12">
                                <h6 class="mt-3 mb-3">Risk Indicators</h6>
                            </div>
                            <div class="col-md-3">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="owner_pep">
                                    <label class="form-check-label" for="owner_pep">Owner is PEP</label>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="owner_sanctioned">
                                    <label class="form-check-label" for="owner_sanctioned">Owner Sanctioned</label>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="offshore_structure">
                                    <label class="form-check-label" for="offshore_structure">Offshore Structure</label>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="form-check">
                                    <input class="form-check-input" type="checkbox" id="cash_intensive">
                                    <label class="form-check-label" for="cash_intensive">Cash Intensive</label>
                                </div>
                            </div>
                            
                            <div class="col-12 mt-4">
                                <button type="submit" class="btn btn-primary btn-lg">
                                    <i class="bi bi-shield-check me-2"></i>Onboard & Assess Risk
                                </button>
                            </div>
                        </div>
                    </form>
                </div>

                <!-- Result Display -->
                <div id="onboard-result" class="form-section mt-4" style="display: none;">
                    <h5>Assessment Result</h5>
                    <div id="result-content"></div>
                </div>
            </div>

            <!-- Alerts Section -->
            <div id="section-alerts" class="section" style="display: none;">
                <h4 class="mb-4"><i class="bi bi-bell me-2"></i>Risk Alerts</h4>
                
                <div class="form-section mb-4">
                    <div class="row g-3">
                        <div class="col-md-3">
                            <select class="form-select" id="filter-alert-resolved" onchange="loadAlerts()">
                                <option value="false">Unresolved Only</option>
                                <option value="">All Alerts</option>
                                <option value="true">Resolved Only</option>
                            </select>
                        </div>
                    </div>
                </div>

                <div class="table-container">
                    <div class="table-responsive">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Merchant</th>
                                    <th>Severity</th>
                                    <th>Title</th>
                                    <th>Created</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody id="alerts-table">
                                <tr><td colspan="6" class="text-center text-muted">Loading...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Configuration Section -->
            <div id="section-config" class="section" style="display: none;">
                <h4 class="mb-4"><i class="bi bi-gear me-2"></i>Risk Configuration</h4>
                
                <div class="alert alert-info">
                    <i class="bi bi-info-circle me-2"></i>
                    Configuration changes require admin API key. Get your key from the server logs.
                </div>

                <div class="form-section mb-4">
                    <label class="form-label">Admin API Key</label>
                    <input type="password" class="form-control" id="admin-api-key" placeholder="Enter API key for configuration changes">
                </div>

                <div class="row">
                    <div class="col-md-6">
                        <div class="form-section">
                            <h6><i class="bi bi-sliders me-2"></i>Risk Thresholds</h6>
                            <div id="thresholds-config">
                                <p class="text-muted">Loading...</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="form-section">
                            <h6><i class="bi bi-bar-chart me-2"></i>Risk Weights</h6>
                            <div id="weights-config" style="max-height: 400px; overflow-y: auto;">
                                <p class="text-muted">Loading...</p>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="form-section mt-4">
                    <h6><i class="bi bi-list-check me-2"></i>High-Risk Lists</h6>
                    <div id="lists-config">
                        <p class="text-muted">Loading...</p>
                    </div>
                </div>
            </div>

            <!-- Audit Section -->
            <div id="section-audit" class="section" style="display: none;">
                <h4 class="mb-4"><i class="bi bi-journal-text me-2"></i>Audit Logs</h4>
                
                <div class="form-section mb-4">
                    <label class="form-label">Admin API Key (required for audit access)</label>
                    <div class="row g-3">
                        <div class="col-md-4">
                            <input type="password" class="form-control" id="audit-api-key" placeholder="Enter API key">
                        </div>
                        <div class="col-md-4">
                            <input type="text" class="form-control" id="audit-merchant-filter" placeholder="Filter by Merchant ID">
                        </div>
                        <div class="col-md-4">
                            <button class="btn btn-primary" onclick="loadAuditLogs()"><i class="bi bi-search me-1"></i>Load Logs</button>
                        </div>
                    </div>
                </div>

                <div class="table-container">
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Timestamp</th>
                                    <th>Action</th>
                                    <th>Merchant</th>
                                    <th>Description</th>
                                    <th>User</th>
                                </tr>
                            </thead>
                            <tbody id="audit-table">
                                <tr><td colspan="5" class="text-center text-muted">Enter API key and click Load Logs</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            const API_BASE = '/api/v1';

            // Show section
            function showSection(name) {
                document.querySelectorAll('.section').forEach(s => s.style.display = 'none');
                document.getElementById('section-' + name).style.display = 'block';
                document.querySelectorAll('.sidebar .nav-link').forEach(l => l.classList.remove('active'));
                event.target.closest('.nav-link').classList.add('active');
                
                // Load data for section
                if (name === 'dashboard') loadDashboard();
                else if (name === 'merchants') loadMerchants();
                else if (name === 'alerts') loadAlerts();
                else if (name === 'config') loadConfig();
            }

            // Load dashboard stats
            async function loadDashboard() {
                try {
                    const res = await fetch(API_BASE + '/dashboard/stats');
                    const data = await res.json();
                    
                    document.getElementById('stat-total').textContent = data.total_merchants;
                    document.getElementById('stat-high').textContent = (data.merchants_by_risk_level.HIGH || 0) + (data.merchants_by_risk_level.CRITICAL || 0);
                    document.getElementById('stat-alerts').textContent = data.unresolved_alerts_count;
                    document.getElementById('stat-avg').textContent = data.average_risk_score.toFixed(1);
                    
                    // Risk distribution
                    const total = data.total_merchants || 1;
                    const levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
                    levels.forEach(level => {
                        const count = data.merchants_by_risk_level[level] || 0;
                        const pct = (count / total * 100).toFixed(0);
                        document.getElementById('dist-' + level.toLowerCase()).textContent = count;
                        document.getElementById('bar-' + level.toLowerCase()).style.width = pct + '%';
                    });
                    
                    // Recent assessments
                    const recentHtml = data.recent_assessments.map(a => `
                        <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
                            <span>${a.merchant_id}</span>
                            <span class="risk-badge risk-${a.risk_level.toLowerCase()}">${a.risk_level}</span>
                        </div>
                    `).join('') || '<p class="text-muted">No assessments yet</p>';
                    document.getElementById('recent-assessments').innerHTML = recentHtml;
                } catch (e) {
                    console.error('Error loading dashboard:', e);
                }
            }

            // Load merchants
            async function loadMerchants() {
                const risk = document.getElementById('filter-risk').value;
                const country = document.getElementById('filter-country').value;
                
                let url = API_BASE + '/merchants?limit=100';
                if (risk) url += '&risk_level=' + risk;
                if (country) url += '&country=' + country;
                
                try {
                    const res = await fetch(url);
                    const merchants = await res.json();
                    
                    const tbody = document.getElementById('merchants-table');
                    if (merchants.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No merchants found</td></tr>';
                        return;
                    }
                    
                    tbody.innerHTML = merchants.map(m => `
                        <tr>
                            <td><strong>${m.merchant_id}</strong></td>
                            <td>${m.business_name}</td>
                            <td>${m.country}</td>
                            <td>${m.industry}</td>
                            <td><span class="badge bg-secondary">${m.risk_score}</span></td>
                            <td><span class="risk-badge risk-${m.risk_level.toLowerCase()}">${m.risk_level}</span></td>
                            <td>
                                <button class="btn btn-sm btn-outline-primary" onclick="viewMerchant('${m.merchant_id}')">
                                    <i class="bi bi-eye"></i>
                                </button>
                            </td>
                        </tr>
                    `).join('');
                } catch (e) {
                    console.error('Error loading merchants:', e);
                }
            }

            // View merchant details
            async function viewMerchant(id) {
                try {
                    const res = await fetch(API_BASE + '/merchants/' + id + '/risk');
                    const data = await res.json();
                    
                    alert(`Merchant: ${id}\\nRisk Score: ${data.risk_score}\\nLevel: ${data.risk_level}\\n\\nReasons:\\n${data.risk_reasons.join('\\n')}`);
                } catch (e) {
                    console.error('Error:', e);
                }
            }

            // Onboard form submission
            document.getElementById('onboard-form').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const data = {
                    merchant_id: document.getElementById('merchant_id').value,
                    business_name: document.getElementById('business_name').value,
                    country: document.getElementById('country').value,
                    industry: document.getElementById('industry').value,
                    mcc_code: document.getElementById('mcc_code').value || null,
                    annual_volume: parseFloat(document.getElementById('annual_volume').value) || 0,
                    owner_name: document.getElementById('owner_name').value || null,
                    years_in_business: parseInt(document.getElementById('years_in_business').value) || 0,
                    refund_rate: parseFloat(document.getElementById('refund_rate').value) || 0,
                    owner_pep: document.getElementById('owner_pep').checked,
                    owner_sanctioned: document.getElementById('owner_sanctioned').checked,
                    offshore_structure: document.getElementById('offshore_structure').checked,
                    cash_intensive: document.getElementById('cash_intensive').checked
                };
                
                try {
                    const res = await fetch(API_BASE + '/merchants', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    
                    const result = await res.json();
                    
                    if (res.ok) {
                        document.getElementById('onboard-result').style.display = 'block';
                        document.getElementById('result-content').innerHTML = `
                            <div class="alert alert-success">
                                <strong>Merchant onboarded successfully!</strong>
                            </div>
                            <div class="row">
                                <div class="col-md-6">
                                    <p><strong>Merchant ID:</strong> ${result.merchant_id}</p>
                                    <p><strong>Business Name:</strong> ${result.business_name}</p>
                                    <p><strong>Status:</strong> ${result.status}</p>
                                </div>
                                <div class="col-md-6">
                                    <h5>Risk Assessment</h5>
                                    <p><strong>Score:</strong> <span class="badge bg-secondary">${result.risk_score}</span></p>
                                    <p><strong>Level:</strong> <span class="risk-badge risk-${result.risk_level.toLowerCase()}">${result.risk_level}</span></p>
                                    <p><strong>Reasons:</strong></p>
                                    <ul>${result.risk_reasons.map(r => '<li>' + r + '</li>').join('')}</ul>
                                </div>
                            </div>
                        `;
                        this.reset();
                    } else {
                        alert('Error: ' + (result.detail || 'Unknown error'));
                    }
                } catch (e) {
                    alert('Error: ' + e.message);
                }
            });

            // Load alerts
            async function loadAlerts() {
                const resolved = document.getElementById('filter-alert-resolved').value;
                let url = API_BASE + '/alerts?limit=50';
                if (resolved !== '') url += '&resolved=' + resolved;
                
                try {
                    const res = await fetch(url);
                    const alerts = await res.json();
                    
                    const tbody = document.getElementById('alerts-table');
                    if (alerts.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No alerts found</td></tr>';
                        return;
                    }
                    
                    tbody.innerHTML = alerts.map(a => `
                        <tr>
                            <td>${a.id}</td>
                            <td>${a.merchant_id}</td>
                            <td><span class="badge ${a.severity === 'CRITICAL' ? 'bg-danger' : 'bg-warning'}">${a.severity}</span></td>
                            <td>${a.title}</td>
                            <td>${new Date(a.created_at).toLocaleString()}</td>
                            <td>${a.is_resolved ? '<span class="text-success">Resolved</span>' : '<span class="text-danger">Open</span>'}</td>
                        </tr>
                    `).join('');
                } catch (e) {
                    console.error('Error loading alerts:', e);
                }
            }

            // Load config
            async function loadConfig() {
                try {
                    // Load thresholds
                    const thresRes = await fetch(API_BASE + '/config/thresholds');
                    const thresData = await thresRes.json();
                    document.getElementById('thresholds-config').innerHTML = Object.entries(thresData.thresholds)
                        .map(([k, v]) => `<p><strong>${k}:</strong> ${v}</p>`).join('');
                    
                    // Load weights
                    const weightsRes = await fetch(API_BASE + '/config/weights');
                    const weightsData = await weightsRes.json();
                    document.getElementById('weights-config').innerHTML = Object.entries(weightsData.weights)
                        .map(([k, v]) => `<p><strong>${k}:</strong> ${v}</p>`).join('');
                    
                    // Load lists
                    const listsRes = await fetch(API_BASE + '/config/lists');
                    const listsData = await listsRes.json();
                    document.getElementById('lists-config').innerHTML = `
                        <div class="row">
                            <div class="col-md-4">
                                <h6>High-Risk Countries (${listsData.high_risk_countries.length})</h6>
                                <div style="max-height: 200px; overflow-y: auto;">
                                    ${listsData.high_risk_countries.slice(0, 10).map(c => `<span class="badge bg-light text-dark me-1 mb-1">${c}</span>`).join('')}
                                    ${listsData.high_risk_countries.length > 10 ? '<br><small class="text-muted">...and more</small>' : ''}
                                </div>
                            </div>
                            <div class="col-md-4">
                                <h6>High-Risk Industries (${listsData.high_risk_industries.length})</h6>
                                <div style="max-height: 200px; overflow-y: auto;">
                                    ${listsData.high_risk_industries.slice(0, 10).map(i => `<span class="badge bg-light text-dark me-1 mb-1">${i}</span>`).join('')}
                                </div>
                            </div>
                            <div class="col-md-4">
                                <h6>Blacklisted MCCs (${listsData.blacklisted_mccs.length})</h6>
                                <div>
                                    ${listsData.blacklisted_mccs.map(m => `<span class="badge bg-light text-dark me-1 mb-1">${m}</span>`).join('')}
                                </div>
                            </div>
                        </div>
                    `;
                } catch (e) {
                    console.error('Error loading config:', e);
                }
            }

            // Load audit logs
            async function loadAuditLogs() {
                const apiKey = document.getElementById('audit-api-key').value;
                const merchantId = document.getElementById('audit-merchant-filter').value;
                
                if (!apiKey) {
                    alert('Please enter API key');
                    return;
                }
                
                let url = API_BASE + '/audit/logs?hours=168&limit=100';
                if (merchantId) url += '&merchant_id=' + merchantId;
                
                try {
                    const res = await fetch(url, {
                        headers: { 'X-API-Key': apiKey }
                    });
                    
                    if (res.status === 403) {
                        alert('Invalid API key');
                        return;
                    }
                    
                    const logs = await res.json();
                    
                    const tbody = document.getElementById('audit-table');
                    if (logs.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No logs found</td></tr>';
                        return;
                    }
                    
                    tbody.innerHTML = logs.map(l => `
                        <tr>
                            <td><small>${new Date(l.created_at).toLocaleString()}</small></td>
                            <td><span class="badge bg-info">${l.action_type}</span></td>
                            <td>${l.merchant_id || '-'}</td>
                            <td><small>${l.action_description}</small></td>
                            <td>${l.user_id || 'SYSTEM'}</td>
                        </tr>
                    `).join('');
                } catch (e) {
                    console.error('Error loading audit logs:', e);
                }
            }

            // Initial load
            loadDashboard();
        </script>
    </body>
    </html>
    """


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
