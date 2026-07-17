from abc import ABC


class BaseService(ABC):
    """
    Abstract base for all application services.

    Application services orchestrate domain operations via injected
    repository interfaces. They must not import from infrastructure directly.
    """
