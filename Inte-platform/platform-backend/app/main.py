from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from app.routers import auth, integrations, apis, dashboard, runtime, connectors
from app.database import engine, Base

Base.metadata.create_all(bind=engine)

# Seed database on startup
from app.seed import seed_database
try:
    seed_database()
except Exception as e:
    print(f"Seed error (may be normal on first run): {e}")

app = FastAPI(title="MuleSoft Anypoint API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["Integrations"])
app.include_router(apis.router, prefix="/api/apis", tags=["API Management"])
app.include_router(runtime.router, prefix="/api/runtime", tags=["Runtime"])
app.include_router(connectors.router, prefix="/api", tags=["Connectors"])

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "platform-backend"}
