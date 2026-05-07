"""
FastAPI application factory for the onboarding service.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.utils.cors_utils import get_allowed_origins
from app.utils.logging_config import configure_logging, setup_exception_handler

# Configure logging with filters and structured format
configure_logging()
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Creates and configures the FastAPI application."""
    # Try to load .env file for local development, but don't fail if it's not available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        # python-dotenv not available, which is fine for production
        pass

    # Define common prefix for all endpoints including docs
    api_prefix = "/onboarding"
    
    app = FastAPI(
        title="Assistant Chat Onboarding API",
        description="Onboarding service for document management and RAGIE integration",
        version="1.0.0",
        docs_url=f"{api_prefix}/docs",
        redoc_url=f"{api_prefix}/redoc",
        openapi_url=f"{api_prefix}/openapi.json"
    )

    # Add CORS middleware with configured allowed origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_allowed_origins(),  # Use our configured origins
        allow_credentials=True, 
        allow_methods=["*"],  # Allow all HTTP methods
        allow_headers=["*"],  # Allow all headers
    )

    # Setup global exception handler for unhandled exceptions
    setup_exception_handler(app)

    # Configure dependency injection FIRST, before importing routes
    from app.di_container import configure_dependencies
    configure_dependencies(app)

    # Import and include FastAPI routers
    from app.routes.health import router as health_router
    from app.routes.assets import router as assets_router
    
    # Use the same prefix for routers as defined above
    app.include_router(health_router, prefix=api_prefix)
    app.include_router(assets_router, prefix=api_prefix)

    # Register custom exception handlers
    from app.exception_handlers import register_exception_handlers
    register_exception_handlers(app)
    
    logger.info("FastAPI onboarding application created successfully")    
    return app


def create_app_with_fallback() -> FastAPI:
    """
    Create the FastAPI application with error fallback.
    
    Returns:
        FastAPI: Either the main app or an error server
    """
    try:
        return create_app()
    except Exception as e:
        logger.error(f"Main application creation failed, starting error server: {e}")
        from app.error_server import create_standalone_error_server
        return create_standalone_error_server(e)


# Create the app instance with fallback capability
app = create_app_with_fallback()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)