"""Custom exceptions for business logic."""


class BusinessException(Exception):
    """Base class for business logic exceptions."""    
    def __init__(self, message: str = "A business error occurred"):
        self.message = message
        super().__init__(self.message)


class NotFoundException(BusinessException):
    """Raised when a requested resource is not found."""    
    def __init__(self, resource: str = "Resource", identifier: str = ""):
        if identifier:
            message = f"{resource} not found: {identifier}"
        else:
            message = f"{resource} not found"
        super().__init__(message)


class AlreadyExistsException(BusinessException):
    """Raised when trying to create a resource that already exists."""    
    def __init__(self, resource: str = "Resource", details: str = ""):
        if details:
            message = f"{resource} already exists: {details}"
        else:
            message = f"{resource} already exists"
        super().__init__(message)


class InvalidStatusException(BusinessException):
    """Raised when an operation is not allowed for the current resource status."""    
    def __init__(self, current_status: str, operation: str = "", allowed_statuses: list = None):
        if operation and allowed_statuses:
            message = f"Cannot {operation} with status '{current_status}'. Allowed statuses: {', '.join(allowed_statuses)}"
        elif operation:
            message = f"Cannot {operation} with status '{current_status}'"
        else:
            message = f"Invalid status for operation: {current_status}"
        super().__init__(message)


class ValidationException(BusinessException):
    """Raised when input validation fails."""
    
    def __init__(self, field: str = "", message: str = "Validation failed"):
        if field:
            message = f"Validation failed for {field}: {message}"
        super().__init__(message)


class AssetNotFoundException(NotFoundException):
    """Raised when an asset is not found."""
    
    def __init__(self, asset_id: str):
        super().__init__("Asset", asset_id)


class AssetAlreadyExistsException(AlreadyExistsException): 
    """Raised when an asset already exists."""
       
    def __init__(self, manufacturer: str, model: str, current_status: str):
        details = f"{manufacturer} {model} with status '{current_status}'"
        super().__init__("Asset", details)


class AssetInvalidStatusException(InvalidStatusException):
    """Raised when asset status doesn't allow the requested operation."""
    
    def __init__(self, current_status: str, operation: str, allowed_statuses: list = None):
        super().__init__(current_status, operation, allowed_statuses)