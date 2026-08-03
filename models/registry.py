"""Model registry."""

from __future__ import annotations

from typing import Any, Callable, Type

from models.base import BaseForecaster

_REGISTRY: dict[str, Type[BaseForecaster]] = {}


def register(name: str | None = None) -> Callable[[Type[BaseForecaster]], Type[BaseForecaster]]:
    def deco(cls: Type[BaseForecaster]) -> Type[BaseForecaster]:
        key = name or cls.name
        _REGISTRY[key] = cls
        return cls

    return deco


def get_model_class(name: str) -> Type[BaseForecaster]:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown model '{name}'. Available: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def list_available_models() -> list[str]:
    return sorted(_REGISTRY)


def build_model(name: str, **kwargs: Any) -> BaseForecaster:
    cls = get_model_class(name)
    return cls(**kwargs)


def get_model_metadata(model: BaseForecaster) -> dict[str, Any]:
    return model.metadata.to_dict()
