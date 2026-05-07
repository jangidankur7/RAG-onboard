"""
Logging configuration and utilities for the messaging API.
"""
import logging
import sys
from fastapi import Request
from fastapi.responses import JSONResponse


class EndpointFilter(logging.Filter):
    """Filter out logs for specific endpoints (health checks, swagger, etc.)"""
    
    # Endpoints to exclude from logging
    EXCLUDED_ENDPOINTS = {
        "/health",
        "/health/",
        "/onboarding/health",  # Full path with API prefix
        "/onboarding/health/",
        "/docs",
        "/docs/",
        "/onboarding/docs",  # Full path with API prefix
        "/onboarding/docs/",
        "/redoc",
        "/redoc/",
        "/onboarding/redoc",  # Full path with API prefix
        "/onboarding/redoc/",
        "/openapi.json",
        "/onboarding/openapi.json",  # Full path with API prefix
        "/",
    }
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Return False to suppress log, True to allow it."""
        # Check if this is an access log from uvicorn
        try:
            message = record.getMessage()

            for endpoint in self.EXCLUDED_ENDPOINTS:
                endpoint_clean = endpoint.strip("/")
                
                # Handle root path specially: matches "GET / HTTP/1.1"
                if endpoint == "/":
                    if ' / HTTP/' in message:
                        return False
                elif endpoint_clean and (f'/{endpoint_clean} HTTP/' in message or \
                     f'/{endpoint_clean}/ HTTP/' in message):
                    return False
        except:
            pass
        return True


def suppress_library_logs():
    """Suppress verbose logs from third-party libraries."""
    # Suppress verbose library logs to reduce noise in CloudWatch/Grafana
    logging.getLogger("httpx").setLevel(logging.WARNING)  # HTTP request details
    logging.getLogger("botocore").setLevel(logging.WARNING)  # AWS SDK internals
    logging.getLogger("boto3").setLevel(logging.WARNING)  # AWS SDK internals
    logging.getLogger("aioboto3").setLevel(logging.WARNING)  # Async AWS SDK internals
    logging.getLogger("aiobotocore").setLevel(logging.WARNING)  # Async AWS SDK core internals
    logging.getLogger("urllib3").setLevel(logging.WARNING)  # HTTP connection pooling
    logging.getLogger("s3transfer").setLevel(logging.WARNING)  # S3 transfer internals


def configure_logging():
    """Configure application logging with structured format and filters."""
    # Configure structured logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        stream=sys.stdout
    )
    
    # Suppress verbose third-party library logs
    suppress_library_logs()
    
    # Add filter to uvicorn loggers to suppress health checks and swagger
    endpoint_filter = EndpointFilter()
    
    # Apply to all uvicorn loggers
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.addFilter(endpoint_filter)
    
    # Also apply to the main uvicorn logger (in case)
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.addFilter(endpoint_filter)
    
    return logging.getLogger(__name__)


def setup_exception_handler(app):
    """
    Setup global exception handler for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    logger = logging.getLogger(__name__)
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Catch and log all unhandled exceptions."""
        logger.error(
            f"Unhandled exception: {request.method} {request.url.path} - {str(exc)}",
            exc_info=True,
            extra={
                "method": request.method,
                "path": request.url.path,
                "error": str(exc),
            }
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

