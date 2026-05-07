"""Centralized FastAPI exception handlers for business logic exceptions."""
from fastapi import Request
from fastapi.responses import JSONResponse

from app.models.excpetions import (
    BusinessException,
    NotFoundException, 
    AlreadyExistsException
)


async def not_found_exception_handler(request: Request, exc: NotFoundException) -> JSONResponse:
    """Handle NotFoundException and return 404 response."""
    return JSONResponse(
        status_code=404,
        content={"detail": exc.message}
    )


async def already_exists_exception_handler(request: Request, exc: AlreadyExistsException) -> JSONResponse:
    """Handle AlreadyExistsException and return 409 Conflict response."""
    return JSONResponse(
        status_code=409,
        content={"detail": exc.message}
    )


async def business_exception_handler(request: Request, exc: BusinessException) -> JSONResponse:
    """Handle generic BusinessException and return 400 Bad Request response."""
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message}
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unhandled exception and return 500 Internal Server Error response."""
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )


def register_exception_handlers(app):
    """Register all custom exception handlers with the FastAPI app."""
    
    # Register base exception handlers only - child classes will inherit the behavior
    app.add_exception_handler(BusinessException, business_exception_handler)
    app.add_exception_handler(NotFoundException, not_found_exception_handler)
    app.add_exception_handler(AlreadyExistsException, already_exists_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)