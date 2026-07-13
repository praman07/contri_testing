import threading
from typing import Dict, List, Set, Tuple, Any, Optional
from override.runtime.context.models import EntityNode, EntityEdge

class EntityGraph:
    """
    Thread-safe in-memory graph representation of environmental entities
    and their relationships (applications, files, browser tabs, etc.).
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._nodes: Dict[str, EntityNode] = {}
        # Map (source_id, target_id, relationship_type) -> EntityEdge
        self._edges: Dict[Tuple[str, str, str], EntityEdge] = {}

    def add_node(self, node: EntityNode) -> None:
        with self._lock:
            self._nodes[node.entity_id] = node

    def add_edge(self, edge: EntityEdge) -> None:
        with self._lock:
            # Enforce that source and target nodes exist in the graph.
            # If not, create simple placeholder nodes.
            if edge.source_id not in self._nodes:
                self._nodes[edge.source_id] = EntityNode(
                    entity_id=edge.source_id,
                    entity_type="unknown"
                )
            if edge.target_id not in self._nodes:
                self._nodes[edge.target_id] = EntityNode(
                    entity_id=edge.target_id,
                    entity_type="unknown"
                )
            key = (edge.source_id, edge.target_id, edge.relationship_type)
            self._edges[key] = edge

    def remove_node(self, entity_id: str) -> None:
        with self._lock:
            if entity_id in self._nodes:
                del self._nodes[entity_id]
            # Remove all associated edges
            edges_to_remove = [
                key for key in self._edges
                if key[0] == entity_id or key[1] == entity_id
            ]
            for key in edges_to_remove:
                del self._edges[key]

    def remove_edge(self, source_id: str, target_id: str, relationship_type: str) -> None:
        with self._lock:
            key = (source_id, target_id, relationship_type)
            if key in self._edges:
                del self._edges[key]

    def get_node(self, entity_id: str) -> Optional[EntityNode]:
        with self._lock:
            return self._nodes.get(entity_id)

    def get_all_nodes(self) -> List[EntityNode]:
        with self._lock:
            return list(self._nodes.values())

    def get_all_edges(self) -> List[EntityEdge]:
        with self._lock:
            return list(self._edges.values())

    def get_neighbors(self, entity_id: str) -> List[EntityNode]:
        """Gets all target nodes connected to the source entity_id."""
        with self._lock:
            neighbors = []
            for key in self._edges:
                if key[0] == entity_id:
                    target_id = key[1]
                    if target_id in self._nodes:
                        neighbors.append(self._nodes[target_id])
            return neighbors

    def clear(self) -> None:
        with self._lock:
            self._nodes.clear()
            self._edges.clear()
