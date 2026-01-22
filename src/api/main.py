"""
FastAPI Application

Main entry point for the training planner web API.
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict

from src.api.routes import validation, plans, fragility, sensitivity, methodologies, strava

# Initialize FastAPI app
app = FastAPI(
    title="Human-in-the-Loop Training Planner API",
    description="Transparent, interpretable training plan generation with multi-methodology support",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration - allow frontend to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(methodologies.router, prefix="/api", tags=["Methodologies"])
app.include_router(validation.router, prefix="/api", tags=["Validation"])
app.include_router(fragility.router, prefix="/api", tags=["Fragility"])
app.include_router(plans.router, prefix="/api", tags=["Plans"])
app.include_router(sensitivity.router, prefix="/api", tags=["Sensitivity"])
app.include_router(strava.router, prefix="/api", tags=["Strava Integration (Phase 5)"])


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint - API information."""
    return {
        "name": "Human-in-the-Loop Training Planner API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "training-planner-api"}


# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "message": str(exc.detail)},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle unexpected exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
