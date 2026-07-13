import threading
from typing import Dict, List, Set, Tuple
from override.runtime.registry.metadata import ModuleMetadata
from override.runtime.registry.module import OverrideModule

class ModuleRegistry:
    """
    Manages module metadata, tracking active states and verifying dependency orders.
    Performs topological sorts to identify legal boot paths.
    """

    def __init__(self):
        self._modules: Dict[str, OverrideModule] = {}
        self._metadata: Dict[str, ModuleMetadata] = {}
        self._lock = threading.RLock()

    def register(self, module: OverrideModule, metadata: ModuleMetadata) -> None:
        """
        Registers an instantiated module and its metadata.
        Does not instantiate the module itself.
        """
        with self._lock:
            if module.module_id != metadata.module_id:
                raise ValueError(
                    f"Mismatch between module ID '{module.module_id}' and metadata ID '{metadata.module_id}'"
                )
            if module.module_id in self._modules:
                raise ValueError(f"Module '{module.module_id}' is already registered.")
            
            self._modules[module.module_id] = module
            self._metadata[module.module_id] = metadata

    def get_module(self, module_id: str) -> OverrideModule:
        with self._lock:
            if module_id not in self._modules:
                raise ValueError(f"Module '{module_id}' is not registered.")
            return self._modules[module_id]

    def get_all_modules(self) -> List[OverrideModule]:
        with self._lock:
            return list(self._modules.values())

    def get_boot_order(self) -> List[str]:
        """
        Computes the topological sorting of modules based on dependency declarations.
        Raises ValueError if circular dependency loops are detected.
        """
        with self._lock:
            # Build graph
            adjacency: Dict[str, Set[str]] = {}
            in_degree: Dict[str, int] = {}
            
            for mod_id in self._modules:
                adjacency[mod_id] = set()
                in_degree[mod_id] = 0

            for mod_id, meta in self._metadata.items():
                for dep in meta.dependencies:
                    if dep not in self._modules:
                        raise ValueError(
                            f"Missing dependency: module '{mod_id}' requires unregistered module '{dep}'"
                        )
                    # dep must start before mod_id. So edge goes dep -> mod_id
                    adjacency[dep].add(mod_id)
                    in_degree[mod_id] += 1

            # Topological Sort (Kahn's Algorithm)
            queue = [node for node, degree in in_degree.items() if degree == 0]
            order: List[str] = []

            while queue:
                current = queue.pop(0)
                order.append(current)
                for neighbor in adjacency[current]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

            if len(order) != len(self._modules):
                # Unprocessed nodes remain due to circular dependencies
                cycles = [node for node, degree in in_degree.items() if degree > 0]
                raise ValueError(
                    f"Circular dependency detected among modules: {cycles}"
                )

            return order
