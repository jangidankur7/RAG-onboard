from typing import TypeVar, Type, Dict, Any
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

def filter_dataclass_fields(data: Dict[str, Any], model_type: Type[T]) -> Dict[str, Any]:
    """Filters dictionary to only valid Pydantic model fields."""
    # Get field names from Pydantic model
    if hasattr(model_type, 'model_fields'):
        # Pydantic v2
        allowed = set(model_type.model_fields.keys())
    elif hasattr(model_type, '__fields__'):
        # Pydantic v1
        allowed = set(model_type.__fields__.keys())
    else:
        # Fallback to all keys if we can't determine the fields
        return data
    
    return {k: v for k, v in data.items() if k in allowed}