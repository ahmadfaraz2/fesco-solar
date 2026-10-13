"""Lightweight pure-Python Pydantic v2 compatibility layer.

Provides zero-dependency BaseModel, Field, computed_field, and field_validator
using standard library types. Enables instant execution with zero disk space
overhead on mobile/Termux environments.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Type, get_args, get_origin

_MODEL_REGISTRY: Dict[str, Type["BaseModel"]] = {}


def computed_field(prop: Any) -> Any:
    """Decorator for computed properties on models."""
    return prop


def field_validator(*field_names: str) -> Callable:
    """Decorator to mark class methods as field validators."""
    def decorator(fn: Callable) -> Callable:
        fn.__validator_fields__ = field_names
        return fn
    return decorator


def Field(
    default: Any = ...,
    default_factory: Optional[Callable[[], Any]] = None,
    description: Optional[str] = None,
    ge: Optional[float] = None,
    le: Optional[float] = None,
    **extra: Any,
) -> Any:
    """Field specification with default or factory."""
    if default_factory is not None:
        return default_factory()
    return default


def _coerce_value(val: Any, target_type: Any) -> Any:
    """Recursively instantiate nested BaseModel and List[BaseModel] types."""
    if target_type is None or val is None:
        return val

    # If target_type is string (due to 'from __future__ import annotations')
    if isinstance(target_type, str):
        for model_name, model_cls in _MODEL_REGISTRY.items():
            if model_name in target_type:
                if isinstance(val, dict):
                    return model_cls(**val)
                elif isinstance(val, list):
                    return [model_cls(**item) if isinstance(item, dict) else item for item in val]
        return val

    origin = get_origin(target_type)
    args = get_args(target_type)

    # Handle Optional[T] / Union[T, None]
    if origin is not None and type(None) in args:
        non_none = [a for a in args if a is not type(None)]
        if non_none:
            target_type = non_none[0]
            origin = get_origin(target_type)
            args = get_args(target_type)

    # Single nested BaseModel
    if isinstance(target_type, type) and issubclass(target_type, BaseModel):
        if isinstance(val, dict):
            return target_type(**val)
        return val

    # List of nested BaseModels
    if origin in (list, List) and args:
        item_type = args[0]
        if isinstance(item_type, type) and issubclass(item_type, BaseModel):
            if isinstance(val, list):
                return [item_type(**item) if isinstance(item, dict) else item for item in val]

    return val


class BaseModel:
    """Pure-Python drop-in replacement for Pydantic v2 BaseModel."""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        _MODEL_REGISTRY[cls.__name__] = cls

    def __init__(self, **kwargs: Any):
        cls = self.__class__
        # Discover declared type annotations on class and base classes
        annotations: Dict[str, Any] = {}
        for base in reversed(cls.__mro__):
            if hasattr(base, "__annotations__"):
                annotations.update(base.__annotations__)

        # Run field_validators if defined
        for name, member in cls.__dict__.items():
            if hasattr(member, "__validator_fields__"):
                for target_field in member.__validator_fields__:
                    if target_field in kwargs:
                        kwargs[target_field] = member.__func__(cls, kwargs[target_field])

        for key, val_type in annotations.items():
            if key in kwargs:
                val = kwargs[key]
                coerced = _coerce_value(val, val_type)
                setattr(self, key, coerced)
            elif hasattr(cls, key):
                default_val = getattr(cls, key)
                if default_val is ...:
                    raise ValueError(f"Missing required field: '{key}' for {cls.__name__}")
                if isinstance(default_val, list):
                    setattr(self, key, list(default_val))
                elif isinstance(default_val, dict):
                    setattr(self, key, dict(default_val))
                else:
                    setattr(self, key, default_val)
            else:
                setattr(self, key, None)

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def model_dump(self) -> Dict[str, Any]:
        """Convert model and its computed fields to a dictionary."""
        result: Dict[str, Any] = {}
        for key, value in self.__dict__.items():
            if key.startswith("_"):
                continue
            if isinstance(value, BaseModel):
                result[key] = value.model_dump()
            elif isinstance(value, list):
                result[key] = [
                    item.model_dump() if isinstance(item, BaseModel) else item
                    for item in value
                ]
            elif isinstance(value, dict):
                result[key] = {
                    k: v.model_dump() if isinstance(v, BaseModel) else v
                    for k, v in value.items()
                }
            else:
                result[key] = value

        # Serialize computed properties
        for key in dir(self.__class__):
            if not key.startswith("_"):
                prop = getattr(self.__class__, key, None)
                if isinstance(prop, property):
                    try:
                        prop_val = getattr(self, key)
                        result[key] = prop_val
                    except Exception:
                        pass
        return result

    def model_dump_json(self, indent: Optional[int] = None) -> str:
        """Serialize model to JSON string."""
        return json.dumps(self.model_dump(), indent=indent, default=str)

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items() if not k.startswith("_"))
        return f"{self.__class__.__name__}({attrs})"
