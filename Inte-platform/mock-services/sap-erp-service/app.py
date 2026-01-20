from fastapi import FastAPI, HTTPException, Query, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import jwt
import uuid
import xml.etree.ElementTree as ET

app = FastAPI(title="SAP ERP API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)

JWT_SECRET = "sap-erp-secret-key"
JWT_ALGORITHM = "HS256"

# ============== DATA STORES ==============
users_db = {"admin": {"password": "admin123", "role": "admin"}}

orders_db = [
    {"order_id": "SO-2024-00001", "customer_id": "CUST-001", "customer_name": "Acme Corp", "order_date": "2024-01-15", "delivery_date": "2024-01-25", "status": "processing", "total_amount": 50000.00, "currency": "USD", "items": [{"line_item": 10, "material_id": "MAT-001", "description": "Enterprise License", "quantity": 10, "unit_price": 5000.00, "total": 50000.00}]},
    {"order_id": "SO-2024-00002", "customer_id": "CUST-002", "customer_name": "TechStart Inc", "order_date": "2024-01-16", "delivery_date": "2024-01-28", "status": "new", "total_amount": 25000.00, "currency": "USD", "items": [{"line_item": 10, "material_id": "MAT-002", "description": "Support Package", "quantity": 5, "unit_price": 5000.00, "total": 25000.00}]},
    {"order_id": "SO-2024-00003", "customer_id": "CUST-003", "customer_name": "Global Industries", "order_date": "2024-01-17", "delivery_date": "2024-02-01", "status": "shipped", "total_amount": 75000.00, "currency": "USD", "items": [{"line_item": 10, "material_id": "MAT-001", "description": "Enterprise License", "quantity": 15, "unit_price": 5000.00, "total": 75000.00}]},
]

stock_db = [
    {"material_id": "MAT-001", "material_description": "Enterprise License", "plant": "1000", "storage_location": "WH01", "available_stock": 500, "reserved_stock": 50, "blocked_stock": 0, "unit_of_measure": "EA", "last_updated": "2024-01-15T10:30:00Z"},
    {"material_id": "MAT-002", "material_description": "Support Package", "plant": "1000", "storage_location": "WH01", "available_stock": 999, "reserved_stock": 10, "blocked_stock": 0, "unit_of_measure": "EA", "last_updated": "2024-01-15T10:30:00Z"},
    {"material_id": "RAW-001", "material_description": "Raw Material 1", "plant": "1000", "storage_location": "WH02", "available_stock": 2500, "reserved_stock": 200, "blocked_stock": 50, "unit_of_measure": "KG", "last_updated": "2024-01-15T11:00:00Z"},
]

movements_db = [
    {"movement_id": "MOV-000001", "material_id": "MAT-001", "quantity": 100, "movement_type": "receipt", "plant": "1000", "storage_location": "WH01", "movement_date": "2024-01-15T10:30:00Z", "reference_doc": "PO-2024-00001"},
    {"movement_id": "MOV-000002", "material_id": "MAT-001", "quantity": 10, "movement_type": "issue", "plant": "1000", "storage_location": "WH01", "movement_date": "2024-01-16T09:00:00Z", "reference_doc": "SO-2024-00001"},
]

customers_db = [
    {"customer_id": "CUST-001", "name": "Acme Corporation", "type": "organization", "industry": "Technology", "address": {"street": "123 Tech Park", "city": "San Francisco", "country": "US", "postal_code": "94105"}, "contact": {"email": "contact@acme.com", "phone": "+1-555-0100"}, "credit_limit": 100000.00, "credit_used": 45000.00, "credit_available": 55000.00, "payment_terms": "NET30", "status": "active"},
    {"customer_id": "CUST-002", "name": "TechStart Inc", "type": "organization", "industry": "Technology", "address": {"street": "456 Innovation Blvd", "city": "Austin", "country": "US", "postal_code": "78701"}, "contact": {"email": "info@techstart.com", "phone": "+1-555-0200"}, "credit_limit": 50000.00, "credit_used": 25000.00, "credit_available": 25000.00, "payment_terms": "NET30", "status": "active"},
    {"customer_id": "CUST-003", "name": "Global Industries", "type": "organization", "industry": "Manufacturing", "address": {"street": "789 Industrial Way", "city": "Chicago", "country": "US", "postal_code": "60601"}, "contact": {"email": "sales@global.com", "phone": "+1-555-0300"}, "credit_limit": 200000.00, "credit_used": 75000.00, "credit_available": 125000.00, "payment_terms": "NET45", "status": "active"},
]

vendors_db = [
    {"vendor_id": "VEND-001", "name": "Tech Supplies Inc", "type": "organization", "industry": "Wholesale", "address": {"street": "789 Supply Chain Rd", "city": "Dallas", "country": "US", "postal_code": "75201"}, "contact": {"email": "sales@techsupplies.com", "phone": "+1-555-0300"}, "payment_terms": "NET30", "bank_details": {"bank_name": "First National", "account": "****1234"}, "status": "active"},
    {"vendor_id": "VEND-002", "name": "Raw Materials Co", "type": "organization", "industry": "Manufacturing", "address": {"street": "321 Factory Lane", "city": "Detroit", "country": "US", "postal_code": "48201"}, "contact": {"email": "orders@rawmaterials.com", "phone": "+1-555-0400"}, "payment_terms": "NET45", "bank_details": {"bank_name": "Commerce Bank", "account": "****5678"}, "status": "active"},
]

invoices_db = [
    {"invoice_id": "INV-2024-00001", "order_id": "SO-2024-00001", "customer_id": "CUST-001", "customer_name": "Acme Corp", "invoice_date": "2024-01-20", "due_date": "2024-02-19", "amount": 50000.00, "tax_amount": 4500.00, "total_amount": 54500.00, "currency": "USD", "status": "pending", "payment_status": "unpaid"},
    {"invoice_id": "INV-2024-00002", "order_id": "SO-2024-00002", "customer_id": "CUST-002", "customer_name": "TechStart Inc", "invoice_date": "2024-01-21", "due_date": "2024-02-20", "amount": 25000.00, "tax_amount": 2250.00, "total_amount": 27250.00, "currency": "USD", "status": "pending", "payment_status": "unpaid"},
]

payments_db = [
    {"payment_id": "PAY-2024-00001", "invoice_id": "INV-2024-00001", "amount": 54500.00, "payment_method": "bank_transfer", "payment_date": "2024-02-10T14:30:00Z", "reference": "TRF-123456", "status": "completed"},
]

purchase_orders_db = [
    {"po_id": "PO-2024-00001", "vendor_id": "VEND-001", "vendor_name": "Tech Supplies Inc", "order_date": "2024-01-10", "delivery_date": "2024-01-25", "status": "open", "total_amount": 25000.00, "currency": "USD", "items": [{"line_item": 10, "material_id": "RAW-001", "description": "Raw Material", "quantity": 500, "unit_price": 50.00, "total": 25000.00}]},
]

production_orders_db = [
    {"order_id": "PRD-2024-00001", "material_id": "FG-001", "material_description": "Finished Product A", "quantity": 100, "unit_of_measure": "EA", "status": "in_progress", "planned_start": "2024-01-15T08:00:00Z", "planned_end": "2024-01-20T17:00:00Z", "actual_start": "2024-01-15T08:30:00Z", "actual_end": None, "work_center": "WC-ASSEMBLY-01"},
]

bom_db = {
    "FG-001": {"bom_id": "BOM-FG-001", "material_id": "FG-001", "material_description": "Finished Product A", "base_quantity": 1, "unit_of_measure": "EA", "components": [{"component_id": "COMP-001", "material_id": "RAW-001", "description": "Raw Material 1", "quantity": 2.0, "unit_of_measure": "KG"}, {"component_id": "COMP-002", "material_id": "RAW-002", "description": "Raw Material 2", "quantity": 1.5, "unit_of_measure": "KG"}]}
}

changes_db = [
    {"entity_type": "orders", "entity_id": "SO-2024-00001", "change_type": "updated", "changed_at": "2024-01-15T14:00:00Z", "changed_by": "admin", "changes": {"status": {"from": "new", "to": "processing"}}},
]


# ============== MODELS ==============
class LoginRequest(BaseModel):
    username: str
    password: str

class OrderCreate(BaseModel):
    customer_id: str
    customer_name: str
    delivery_date: str
    currency: str = "USD"
    items: List[dict]

class OrderUpdate(BaseModel):
    customer_name: Optional[str] = None
    delivery_date: Optional[str] = None
    status: Optional[str] = None

class StatusUpdate(BaseModel):
    status: str

class MovementCreate(BaseModel):
    material_id: str
    quantity: int
    movement_type: str
    plant: str
    storage_location: str
    reference_doc: Optional[str] = None
    notes: Optional[str] = None

class InvoiceCreate(BaseModel):
    order_id: str
    customer_id: str
    customer_name: str
    due_date: str
    tax_rate: float = 0.09
    currency: str = "USD"
    items: List[dict]

class PaymentCreate(BaseModel):
    invoice_id: str
    amount: float
    payment_method: str
    reference: str

class PurchaseOrderCreate(BaseModel):
    vendor_id: str
    vendor_name: str
    delivery_date: str
    currency: str = "USD"
    items: List[dict]

class GoodsReceiptCreate(BaseModel):
    po_id: str
    received_by: str
    notes: Optional[str] = None
    items: List[dict]

class ProductionConfirmation(BaseModel):
    order_id: str
    operation_number: int
    quantity_confirmed: int
    yield_quantity: int
    scrap_quantity: int
    confirmed_by: str
    notes: Optional[str] = None

class BulkExportRequest(BaseModel):
    entity_type: str
    filters: Optional[dict] = None
    fields: Optional[List[str]] = None
    format: str = "json"

class WebhookRequest(BaseModel):
    event_type: str
    entity_type: str
    entity_id: str
    timestamp: str
    data: dict

# ============== AUTH ==============
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None:
        return None
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/v1/auth/login")
def login(request: LoginRequest):
    user = users_db.get(request.username)
    if not user or user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = jwt.encode({"sub": request.username, "role": user["role"], "exp": datetime.utcnow() + timedelta(hours=1)}, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"access_token": token, "token_type": "bearer", "expires_in": 3600}

# ============== SALES & ORDERS ==============
@app.get("/api/sales/orders")
def list_orders(status: Optional[str] = None, customer_id: Optional[str] = None, page: int = 1, page_size: int = 20):
    filtered = orders_db
    if status:
        filtered = [o for o in filtered if o["status"] == status]
    if customer_id:
        filtered = [o for o in filtered if o["customer_id"] == customer_id]
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    return {"orders": filtered[start:end], "pagination": {"page": page, "total_pages": (total + page_size - 1) // page_size, "total_records": total}}

@app.get("/api/sales/orders/{order_id}")
def get_order(order_id: str):
    order = next((o for o in orders_db if o["order_id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.post("/api/sales/orders")
def create_order(order: OrderCreate):
    new_id = f"SO-2024-{str(len(orders_db) + 1).zfill(5)}"
    total = sum(item.get("total", 0) for item in order.items)
    new_order = {"order_id": new_id, "customer_id": order.customer_id, "customer_name": order.customer_name, "order_date": datetime.utcnow().strftime("%Y-%m-%d"), "delivery_date": order.delivery_date, "status": "new", "total_amount": total, "currency": order.currency, "items": order.items}
    orders_db.append(new_order)
    return new_order

@app.put("/api/sales/orders/{order_id}")
def update_order(order_id: str, update: OrderUpdate):
    order = next((o for o in orders_db if o["order_id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if update.customer_name:
        order["customer_name"] = update.customer_name
    if update.delivery_date:
        order["delivery_date"] = update.delivery_date
    if update.status:
        order["status"] = update.status
    return order

@app.patch("/api/sales/orders/{order_id}/status")
def update_order_status(order_id: str, update: StatusUpdate):
    order = next((o for o in orders_db if o["order_id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order["status"] = update.status
    return order


# ============== INVENTORY ==============
@app.get("/api/inventory/stock")
def get_stock(plant: Optional[str] = None, storage_location: Optional[str] = None, material_id: Optional[str] = None):
    filtered = stock_db
    if plant:
        filtered = [s for s in filtered if s["plant"] == plant]
    if storage_location:
        filtered = [s for s in filtered if s["storage_location"] == storage_location]
    if material_id:
        filtered = [s for s in filtered if s["material_id"] == material_id]
    return {"stock": filtered, "total": len(filtered)}

@app.get("/api/inventory/movements")
def get_movements(from_date: Optional[str] = None, to_date: Optional[str] = None, material_id: Optional[str] = None, movement_type: Optional[str] = None):
    filtered = movements_db
    if material_id:
        filtered = [m for m in filtered if m["material_id"] == material_id]
    if movement_type:
        filtered = [m for m in filtered if m["movement_type"] == movement_type]
    return {"movements": filtered, "total": len(filtered)}

@app.post("/api/inventory/movements")
def create_movement(movement: MovementCreate):
    new_id = f"MOV-{str(len(movements_db) + 1).zfill(6)}"
    new_movement = {"movement_id": new_id, "material_id": movement.material_id, "quantity": movement.quantity, "movement_type": movement.movement_type, "plant": movement.plant, "storage_location": movement.storage_location, "movement_date": datetime.utcnow().isoformat() + "Z", "reference_doc": movement.reference_doc}
    movements_db.append(new_movement)
    return new_movement

# ============== CUSTOMERS ==============
@app.get("/api/customers")
def list_customers(status: Optional[str] = None, industry: Optional[str] = None):
    filtered = customers_db
    if status:
        filtered = [c for c in filtered if c["status"] == status]
    if industry:
        filtered = [c for c in filtered if c["industry"] == industry]
    return {"customers": filtered, "pagination": {"page": 1, "total_pages": 1, "total_records": len(filtered)}}

@app.get("/api/customers/{customer_id}")
def get_customer(customer_id: str):
    customer = next((c for c in customers_db if c["customer_id"] == customer_id), None)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

# ============== VENDORS ==============
@app.get("/api/vendors")
def list_vendors():
    return {"vendors": vendors_db, "pagination": {"page": 1, "total_pages": 1, "total_records": len(vendors_db)}}

@app.get("/api/vendors/{vendor_id}")
def get_vendor(vendor_id: str):
    vendor = next((v for v in vendors_db if v["vendor_id"] == vendor_id), None)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor

# ============== BUSINESS PARTNERS ==============
@app.get("/api/business-partners")
def list_business_partners(type: Optional[str] = None, status: Optional[str] = None):
    partners = []
    for c in customers_db:
        partners.append({"partner_id": c["customer_id"], "partner_type": "customer", "name": c["name"], "type": c["type"], "industry": c["industry"], "address": c["address"], "contact": c["contact"], "status": c["status"]})
    for v in vendors_db:
        partners.append({"partner_id": v["vendor_id"], "partner_type": "vendor", "name": v["name"], "type": v["type"], "industry": v["industry"], "address": v["address"], "contact": v["contact"], "status": v["status"]})
    if type:
        partners = [p for p in partners if p["partner_type"] == type]
    if status:
        partners = [p for p in partners if p["status"] == status]
    return partners

# ============== FINANCE ==============
@app.get("/api/finance/invoices")
def list_invoices(status: Optional[str] = None, customer_id: Optional[str] = None, payment_status: Optional[str] = None):
    filtered = invoices_db
    if status:
        filtered = [i for i in filtered if i["status"] == status]
    if customer_id:
        filtered = [i for i in filtered if i["customer_id"] == customer_id]
    if payment_status:
        filtered = [i for i in filtered if i["payment_status"] == payment_status]
    return {"invoices": filtered, "pagination": {"page": 1, "total_pages": 1, "total_records": len(filtered)}}

@app.post("/api/finance/invoices")
def create_invoice(invoice: InvoiceCreate):
    new_id = f"INV-2024-{str(len(invoices_db) + 1).zfill(5)}"
    amount = sum(item.get("total", 0) for item in invoice.items)
    tax_amount = amount * invoice.tax_rate
    new_invoice = {"invoice_id": new_id, "order_id": invoice.order_id, "customer_id": invoice.customer_id, "customer_name": invoice.customer_name, "invoice_date": datetime.utcnow().strftime("%Y-%m-%d"), "due_date": invoice.due_date, "amount": amount, "tax_amount": tax_amount, "total_amount": amount + tax_amount, "currency": invoice.currency, "status": "pending", "payment_status": "unpaid"}
    invoices_db.append(new_invoice)
    return new_invoice

@app.get("/api/finance/payments")
def list_payments():
    return {"payments": payments_db, "pagination": {"page": 1, "total_pages": 1, "total_records": len(payments_db)}}

@app.post("/api/finance/payments")
def create_payment(payment: PaymentCreate):
    new_id = f"PAY-2024-{str(len(payments_db) + 1).zfill(5)}"
    new_payment = {"payment_id": new_id, "invoice_id": payment.invoice_id, "amount": payment.amount, "payment_method": payment.payment_method, "payment_date": datetime.utcnow().isoformat() + "Z", "reference": payment.reference, "status": "completed"}
    payments_db.append(new_payment)
    invoice = next((i for i in invoices_db if i["invoice_id"] == payment.invoice_id), None)
    if invoice:
        invoice["payment_status"] = "paid"
        invoice["status"] = "paid"
    return new_payment

@app.get("/api/finance/accounts-receivable")
def get_accounts_receivable():
    items = []
    for c in customers_db:
        items.append({"customer_id": c["customer_id"], "customer_name": c["name"], "current": 15000.00, "days_30": 10000.00, "days_60": 5000.00, "days_90": 0.00, "over_90": 0.00, "total": 30000.00})
    return {"as_of_date": datetime.utcnow().strftime("%Y-%m-%d"), "items": items, "totals": {"current": 40000.00, "days_30": 25000.00, "days_60": 13000.00, "days_90": 2000.00, "over_90": 0.00, "total": 80000.00}}


# ============== PURCHASING ==============
@app.get("/api/purchasing/orders")
def list_purchase_orders():
    return {"purchase_orders": purchase_orders_db, "pagination": {"page": 1, "total_pages": 1, "total_records": len(purchase_orders_db)}}

@app.post("/api/purchasing/orders")
def create_purchase_order(po: PurchaseOrderCreate):
    new_id = f"PO-2024-{str(len(purchase_orders_db) + 1).zfill(5)}"
    total = sum(item.get("total", 0) for item in po.items)
    new_po = {"po_id": new_id, "vendor_id": po.vendor_id, "vendor_name": po.vendor_name, "order_date": datetime.utcnow().strftime("%Y-%m-%d"), "delivery_date": po.delivery_date, "status": "open", "total_amount": total, "currency": po.currency, "items": po.items}
    purchase_orders_db.append(new_po)
    return new_po

@app.post("/api/purchasing/goods-receipt")
def create_goods_receipt(receipt: GoodsReceiptCreate):
    new_id = f"GR-2024-{str(uuid.uuid4())[:5].upper()}"
    return {"receipt_id": new_id, "po_id": receipt.po_id, "receipt_date": datetime.utcnow().isoformat() + "Z", "received_by": receipt.received_by, "items": receipt.items, "status": "posted"}

# ============== PRODUCTION ==============
@app.get("/api/production/orders")
def list_production_orders(status: Optional[str] = None, material_id: Optional[str] = None, work_center: Optional[str] = None):
    filtered = production_orders_db
    if status:
        filtered = [p for p in filtered if p["status"] == status]
    if material_id:
        filtered = [p for p in filtered if p["material_id"] == material_id]
    if work_center:
        filtered = [p for p in filtered if p["work_center"] == work_center]
    return {"production_orders": filtered, "pagination": {"page": 1, "total_pages": 1, "total_records": len(filtered)}}

@app.get("/api/production/bom")
def get_bom(material_id: str):
    bom = bom_db.get(material_id)
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")
    return bom

@app.post("/api/production/confirmations")
def create_production_confirmation(confirmation: ProductionConfirmation):
    return {"confirmation_id": f"CONF-{uuid.uuid4().hex[:8].upper()}", "order_id": confirmation.order_id, "operation_number": confirmation.operation_number, "quantity_confirmed": confirmation.quantity_confirmed, "yield_quantity": confirmation.yield_quantity, "scrap_quantity": confirmation.scrap_quantity, "confirmed_by": confirmation.confirmed_by, "confirmed_at": datetime.utcnow().isoformat() + "Z", "status": "posted"}

# ============== REPORTS ==============
@app.get("/api/reports/sales-summary")
def get_sales_summary(period: str = "monthly", year: int = 2024):
    return {"period_type": period, "year": year, "data": [{"period": "January", "total_orders": 150, "total_revenue": 450000.00, "average_order_value": 3000.00, "top_customer": "Acme Corp", "currency": "USD"}, {"period": "February", "total_orders": 175, "total_revenue": 525000.00, "average_order_value": 3000.00, "top_customer": "Global Industries", "currency": "USD"}], "totals": {"total_orders": 525, "total_revenue": 1595000.00, "average_order_value": 3038.10}}

@app.get("/api/reports/inventory-valuation")
def get_inventory_valuation(as_of_date: Optional[str] = None):
    date = as_of_date or datetime.utcnow().strftime("%Y-%m-%d")
    items = [{"material_id": s["material_id"], "description": s["material_description"], "quantity": s["available_stock"], "unit_cost": 1000.00, "total_value": s["available_stock"] * 1000.00, "storage_location": s["storage_location"]} for s in stock_db]
    total = sum(i["total_value"] for i in items)
    return {"as_of_date": date, "items": items, "total_value": total, "currency": "USD"}

@app.get("/api/reports/profit-loss")
def get_profit_loss(from_date: str = "2024-01-01", to_date: str = "2024-01-31"):
    return {"from_date": from_date, "to_date": to_date, "revenue": [{"category": "Sales", "description": "Product Sales", "amount": 1500000.00}, {"category": "Sales", "description": "Service Revenue", "amount": 250000.00}], "expenses": [{"category": "COGS", "description": "Cost of Goods Sold", "amount": 750000.00}, {"category": "Operating", "description": "Salaries & Wages", "amount": 300000.00}], "total_revenue": 1755000.00, "total_expenses": 1200000.00, "net_income": 555000.00, "currency": "USD"}

# ============== INTEGRATION ==============
@app.get("/api/integration/changes")
def get_changes(entity: str, since: str):
    filtered = [c for c in changes_db if c["entity_type"] == entity]
    return {"entity": entity, "since": since, "records": filtered, "total": len(filtered), "has_more": False}

@app.post("/api/integration/bulk-export")
def bulk_export(request: BulkExportRequest):
    return {"export_id": f"EXP-{uuid.uuid4().hex[:6].upper()}", "entity_type": request.entity_type, "record_count": 0, "status": "processing", "download_url": None, "created_at": datetime.utcnow().isoformat() + "Z"}

@app.post("/api/integration/webhook")
def receive_webhook(request: WebhookRequest):
    return {"received": True, "event_type": request.event_type, "entity_id": request.entity_id, "processed_at": datetime.utcnow().isoformat() + "Z"}

# ============== SYSTEM ==============
@app.get("/api/system/health")
def health_check():
    return {"status": "healthy", "service": "sap-erp-backend", "version": "1.0.0", "timestamp": datetime.utcnow().isoformat() + "Z", "components": {"database": "healthy", "cache": "healthy", "message_queue": "healthy"}}

@app.get("/api/system/config")
def get_config():
    return {"company_code": "1000", "company_name": "Demo Corporation", "currency": "USD", "fiscal_year_start": "01-01", "timezone": "America/New_York", "modules_enabled": ["SD", "MM", "FI", "PM", "PP"], "integration_endpoints": {"crm": "http://crm-service:8092", "itsm": "http://itsm-service:8093"}}

@app.get("/")
def root():
    return {"service": "SAP ERP API", "version": "1.0.0", "docs": "/docs", "modules": ["sales", "inventory", "customers", "vendors", "finance", "purchasing", "production", "reports", "integration", "system", "electricity-load"]}

# ============== ELECTRICITY LOAD REQUEST ==============
electricity_load_requests_db = []

@app.post("/api/electricity-load-request", status_code=201)
async def create_electricity_load_request(request: Request):
    """
    Receive electricity load increase request in XML format from integration engine
    """
    try:
        # Get XML body
        xml_body = await request.body()
        xml_string = xml_body.decode('utf-8')
        
        # Parse XML
        root = ET.fromstring(xml_string)
        
        # Extract data from XML
        request_data = {
            "request_id": root.find('RequestID').text if root.find('RequestID') is not None else None,
            "customer_id": root.find('CustomerID').text if root.find('CustomerID') is not None else None,
            "current_load": int(root.find('CurrentLoad').text) if root.find('CurrentLoad') is not None else 0,
            "requested_load": int(root.find('RequestedLoad').text) if root.find('RequestedLoad') is not None else 0,
            "connection_type": root.find('ConnectionType').text if root.find('ConnectionType') is not None else None,
            "city": root.find('City').text if root.find('City') is not None else None,
            "pin_code": root.find('PinCode').text if root.find('PinCode') is not None else None,
            "received_at": datetime.utcnow().isoformat() + "Z",
            "status": "RECEIVED",
            "sap_order_id": f"SAP-EL-{str(len(electricity_load_requests_db) + 1).zfill(6)}"
        }
        
        # Store in database
        electricity_load_requests_db.append(request_data)
        
        # Create XML response
        response_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ElectricityLoadResponse>
    <Status>SUCCESS</Status>
    <Message>Electricity load request received successfully</Message>
    <RequestID>{request_data['request_id']}</RequestID>
    <SAPOrderID>{request_data['sap_order_id']}</SAPOrderID>
    <ProcessingTime>2024-01-20T10:30:00Z</ProcessingTime>
    <EstimatedCompletionDays>7</EstimatedCompletionDays>
    <ApprovalRequired>true</ApprovalRequired>
    <TechnicalFeasibility>PENDING_REVIEW</TechnicalFeasibility>
</ElectricityLoadResponse>"""
        
        return Response(content=response_xml, media_type="application/xml")
        
    except ET.ParseError as e:
        raise HTTPException(status_code=400, detail=f"Invalid XML format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.post("/api/integration/mulesoft/load-request/xml", status_code=201)
async def mulesoft_integration_endpoint(request: Request):
    """
    MuleSoft Integration Endpoint - Receive electricity load increase request in XML format
    This is the standardized endpoint for Salesforce → MuleSoft → SAP integration
    """
    try:
        # Get XML body
        xml_body = await request.body()
        xml_string = xml_body.decode('utf-8')
        
        # Parse XML
        root = ET.fromstring(xml_string)
        
        # Extract data from XML
        request_data = {
            "request_id": root.find('RequestID').text if root.find('RequestID') is not None else None,
            "customer_id": root.find('CustomerID').text if root.find('CustomerID') is not None else None,
            "current_load": int(root.find('CurrentLoad').text) if root.find('CurrentLoad') is not None else 0,
            "requested_load": int(root.find('RequestedLoad').text) if root.find('RequestedLoad') is not None else 0,
            "connection_type": root.find('ConnectionType').text if root.find('ConnectionType') is not None else None,
            "city": root.find('City').text if root.find('City') is not None else None,
            "pin_code": root.find('PinCode').text if root.find('PinCode') is not None else None,
            "received_at": datetime.utcnow().isoformat() + "Z",
            "status": "RECEIVED",
            "source": "SALESFORCE_MULESOFT",
            "sap_order_id": f"SAP-EL-{str(len(electricity_load_requests_db) + 1).zfill(6)}"
        }
        
        # Store in database
        electricity_load_requests_db.append(request_data)
        
        # Create XML response
        response_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ElectricityLoadResponse>
    <Status>SUCCESS</Status>
    <Message>Electricity load request received and processed successfully</Message>
    <RequestID>{request_data['request_id']}</RequestID>
    <SAPOrderID>{request_data['sap_order_id']}</SAPOrderID>
    <ProcessingTime>{request_data['received_at']}</ProcessingTime>
    <EstimatedCompletionDays>7</EstimatedCompletionDays>
    <ApprovalRequired>true</ApprovalRequired>
    <TechnicalFeasibility>PENDING_REVIEW</TechnicalFeasibility>
    <IntegrationSource>SALESFORCE_MULESOFT</IntegrationSource>
</ElectricityLoadResponse>"""
        
        return Response(content=response_xml, media_type="application/xml")
        
    except ET.ParseError as e:
        error_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ElectricityLoadResponse>
    <Status>FAILURE</Status>
    <Message>Invalid XML format: {str(e)}</Message>
    <ErrorCode>ERR_XML_PARSE</ErrorCode>
</ElectricityLoadResponse>"""
        return Response(content=error_xml, media_type="application/xml", status_code=400)
    except Exception as e:
        error_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ElectricityLoadResponse>
    <Status>FAILURE</Status>
    <Message>Error processing request: {str(e)}</Message>
    <ErrorCode>ERR_PROCESSING</ErrorCode>
</ElectricityLoadResponse>"""
        return Response(content=error_xml, media_type="application/xml", status_code=500)

@app.get("/api/electricity-load-request/{request_id}")
def get_electricity_load_request(request_id: str):
    """
    Get electricity load request status by request ID
    """
    request = next((r for r in electricity_load_requests_db if r["request_id"] == request_id), None)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return request

@app.get("/api/electricity-load-requests")
def list_electricity_load_requests(status: Optional[str] = None, city: Optional[str] = None):
    """
    List all electricity load requests with optional filters
    """
    filtered = electricity_load_requests_db
    if status:
        filtered = [r for r in filtered if r["status"] == status]
    if city:
        filtered = [r for r in filtered if r["city"] == city]
    return {
        "requests": filtered,
        "total": len(filtered),
        "pagination": {"page": 1, "total_pages": 1, "total_records": len(filtered)}
    }
