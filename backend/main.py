import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from . import models, schemas, crud
from .database import Base, engine, SessionLocal, add_missing_columns
from .sample_data import seed_database
from .routers import auth_routes, user_routes, admin_routes

# Create tables
Base.metadata.create_all(bind=engine)
add_missing_columns()

app = FastAPI(
    title="Train Ticket Scheduler and Route Optimizer",
    description="FastAPI backend with role-based access, ticket booking, and "
    "Dijkstra-based route optimization.",
    version="1.0.0",
)


# TODO set FRONTEND_ORIGINS before deploying, "*" lets any site call the API
_origins_env = os.getenv("FRONTEND_ORIGINS", "*").strip()
if _origins_env == "*":
    _allow_origins = ["*"]
else:
    _allow_origins = [o.strip() for o in _origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_middleware(
    GZipMiddleware, minimum_size=2000
)  # the map data is ~300 KB before gzip

app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(admin_routes.router)


@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    try:
        seed_database(db, models)
        # default admin
        # the one admin account. set these in .env, the defaults are only for trying it out
        admin_user = os.getenv("ADMIN_USERNAME", "admin")
        admin_pass = os.getenv("ADMIN_PASSWORD", "admin123")
        if admin_pass == "admin123":
            print(
                "ADMIN: using the default password admin123, set ADMIN_PASSWORD in .env"
            )
        if not crud.get_user_by_username(db, admin_user):
            crud.create_user(
                db,
                schemas.UserCreate(
                    username=admin_user,
                    email=os.getenv("ADMIN_EMAIL", "admin@trainscheduler.com"),
                    password=admin_pass,
                    role="admin",
                ),
                auto_verify=True,
            )  # default admin is pre-verified # default admin is pre-verified
    finally:
        db.close()


@app.get("/")
def root():
    return {
        "message": "Train Ticket Scheduler and Route Optimizer API is running",
        "docs": "/docs",
    }
