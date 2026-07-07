from dataclasses import dataclass, field
from typing import List

@dataclass(frozen=True)
class ModuleMetadata:
    """Metadata detailing a registered cognitive layer module."""
    module_id: str
    version: str = "1.0.0"
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
