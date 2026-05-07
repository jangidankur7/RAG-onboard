"""
Standalone error server for the On-Boarding API.

This module provides a simple HTTP server that displays an error page when 
the main FastAPI application fails to start.
"""
import traceback
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI


def create_standalone_error_server(exception: Exception) -> "FastAPI":
    """
    Create a simple error server that displays an error page.
    
    Args:
        exception: The exception that caused the application startup failure
        
    Returns:
        FastAPI: Simple FastAPI app that serves an error page
    """
    # Format error message and details from the exception
    error_message = f"Failed to initialize main application: {str(exception)}"
    error_details = traceback.format_exc()
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import HTMLResponse, JSONResponse
    except ImportError:
        raise RuntimeError("FastAPI not available - cannot create error server")
    
    # Define common prefix to match main application
    api_prefix = "/onboarding"
    
    app = FastAPI(
        title="On-Boarding API - Error",
        description="Error page for failed application startup",
        version="0.1.0-error",
        docs_url=None,  # Disable automatic /docs
        redoc_url=None,  # Disable automatic /redoc
        openapi_url=None  # Disable automatic /openapi.json
    )
    
    # Create HTML error page
    error_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>On-Boarding API - Error</title>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            margin: 0; padding: 20px; background: #f5f5f5; 
        }}
        .container {{ 
            max-width: 800px; margin: 0 auto; background: white; 
            padding: 30px; border-radius: 8px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
        }}
        .error-header {{ color: #d32f2f; margin-bottom: 20px; }}
        .error-icon {{ font-size: 48px; margin-bottom: 10px; }}
        .error-title {{ font-size: 32px; margin: 0; }}
        .error-subtitle {{ font-size: 18px; color: #666; margin: 10px 0 20px 0; }}
        .error-message {{ 
            background: #fff3e0; border: 1px solid #ffb74d; 
            padding: 15px; border-radius: 4px; margin: 20px 0; 
        }}
        .error-details {{ 
            background: #f5f5f5; border: 1px solid #ddd; 
            padding: 15px; border-radius: 4px; margin: 20px 0; 
            font-family: monospace; white-space: pre-wrap; 
            font-size: 12px; max-height: 300px; overflow-y: auto; 
        }}
        .btn {{ 
            padding: 10px 20px; margin-right: 10px; border: none; 
            border-radius: 4px; cursor: pointer; text-decoration: none; 
            display: inline-block; background: #1976d2; color: white; 
        }}
        .btn:hover {{ opacity: 0.8; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="error-header">
            <div class="error-icon">⚠️</div>
            <h1 class="error-title">On-Boarding API - Startup Error</h1>
            <p class="error-subtitle">Application Failed to Initialize</p>
        </div>
        
        <p>The On-Boarding API could not start due to an initialization error.</p>
        
        <div class="error-message">
            <strong>Error:</strong> {error_message}
        </div>
        
        {f'<div class="error-details"><strong>Technical Details:</strong><br>{error_details}</div>' if error_details else ""}
        
        <p><strong>Next steps:</strong></p>
        <ul>
            <li>Check the Docker container logs</li>
            <li>Verify all dependencies are properly installed</li>
            <li>Check configuration and environment variables</li>
            <li>Try rebuilding the container: <code>docker-compose build --no-cache</code></li>
        </ul>
        
        <button class="btn" onclick="window.location.reload()">� Reload Page</button>
    </div>
</body>
</html>"""
    
    @app.get("/")
    async def root_redirect():
        """Redirect root to the prefixed error page"""
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=f"{api_prefix}/")
    
    @app.get(f"{api_prefix}/")
    async def error_page():
        """Serve the error page at prefixed root"""
        return HTMLResponse(content=error_html)
    
    @app.get(f"{api_prefix}/docs")
    async def docs_error_page():
        """Serve the error page at prefixed /docs"""
        return HTMLResponse(content=error_html)
    
    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        """Return 404 for all other routes"""
        return JSONResponse(
            status_code=404, 
            content={"detail": "Endpoint not available - application failed to start"}
        )
    
    return app
