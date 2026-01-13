from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="Mock ERP Service")

@app.get("/")
def root():
    return {"service": "ERP Mock API", "version": "1.0.0", "endpoints": ["/orders", "/inventory", "/invoices", "/health"]}

@app.get("/orders")
def get_orders():
    return [
        {"id": "ORD-001", "product": "Enterprise License", "quantity": 10, "amount": 50000, "status": "shipped", "customer": "Acme Corp"},
        {"id": "ORD-002", "product": "Support Package", "quantity": 1, "amount": 15000, "status": "processing", "customer": "TechStart Inc"},
        {"id": "ORD-003", "product": "Cloud Credits", "quantity": 100, "amount": 10000, "status": "pending", "customer": "Global Industries"},
        {"id": "ORD-004", "product": "Training Bundle", "quantity": 5, "amount": 7500, "status": "shipped", "customer": "DataFlow LLC"},
        {"id": "ORD-005", "product": "API Gateway License", "quantity": 2, "amount": 25000, "status": "delivered", "customer": "CloudNine Systems"}
    ]

@app.get("/inventory")
def get_inventory():
    return [
        {"sku": "LIC-ENT-001", "name": "Enterprise License", "stock": 500, "warehouse": "WH-DIGITAL", "reorderPoint": 100},
        {"sku": "SUP-PKG-001", "name": "Support Package", "stock": 999, "warehouse": "WH-DIGITAL", "reorderPoint": 50},
        {"sku": "CLD-CRD-001", "name": "Cloud Credits", "stock": 10000, "warehouse": "WH-DIGITAL", "reorderPoint": 1000},
        {"sku": "TRN-BND-001", "name": "Training Bundle", "stock": 250, "warehouse": "WH-DIGITAL", "reorderPoint": 25},
        {"sku": "API-GW-001", "name": "API Gateway License", "stock": 150, "warehouse": "WH-DIGITAL", "reorderPoint": 20}
    ]

@app.get("/invoices")
def get_invoices():
    return [
        {"id": "INV-2024-001", "orderId": "ORD-001", "amount": 50000, "status": "paid", "dueDate": "2024-02-15"},
        {"id": "INV-2024-002", "orderId": "ORD-002", "amount": 15000, "status": "pending", "dueDate": "2024-02-28"},
        {"id": "INV-2024-003", "orderId": "ORD-003", "amount": 10000, "status": "overdue", "dueDate": "2024-01-15"}
    ]

@app.get("/health")
def health():
    return {"status": "healthy", "service": "erp-mock", "timestamp": datetime.utcnow().isoformat()}
