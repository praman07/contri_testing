import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from override.runtime.goal.models import GoalNode, VALID_GOAL_STATES

ALLOWED_TRANSITIONS = {
    # (old_state, new_state)
    ("DRAFT", "ACTIVE"),
    ("ACTIVE", "PAUSED"),
    ("ACTIVE", "BLOCKED"),
    ("ACTIVE", "COMPLETED"),
    ("ACTIVE", "ABANDONED"),
    ("PAUSED", "ACTIVE"),
    ("PAUSED", "ABANDONED"),
    ("BLOCKED", "ACTIVE"),
    ("BLOCKED", "ABANDONED"),
    ("COMPLETED", "ACTIVE"),
    ("ABANDONED", "ACTIVE"),
}

class GoalTree:
    """
    Thread-safe in-memory representation of the Goal Hierarchy Tree.
    Coordinates child-to-parent relationships and recalculates progress rollup recursively.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._nodes: Dict[str, GoalNode] = {}
        self._children: Dict[str, List[str]] = {}  # parent_goal_id -> list of child_goal_ids

    def clear(self) -> None:
        """Clears all nodes from the tree."""
        with self._lock:
            self._nodes.clear()
            self._children.clear()

    def add_node(self, node: GoalNode) -> None:
        """Adds a GoalNode to the tree structure."""
        with self._lock:
            self._nodes[node.goal_id] = node
            if node.parent_goal_id:
                if node.parent_goal_id not in self._nodes:
                    raise ValueError(f"Parent goal {node.parent_goal_id} does not exist.")
                if node.parent_goal_id not in self._children:
                    self._children[node.parent_goal_id] = []
                if node.goal_id not in self._children[node.parent_goal_id]:
                    self._children[node.parent_goal_id].append(node.goal_id)

    def get_node(self, goal_id: str) -> Optional[GoalNode]:
        """Retrieves a GoalNode by ID."""
        with self._lock:
            return self._nodes.get(goal_id)

    def get_all_nodes(self) -> List[GoalNode]:
        """Retrieves all GoalNodes in the tree."""
        with self._lock:
            return list(self._nodes.values())

    def get_children(self, parent_id: str) -> List[GoalNode]:
        """Retrieves children of a specific parent goal."""
        with self._lock:
            child_ids = self._children.get(parent_id, [])
            return [self._nodes[cid] for cid in child_ids if cid in self._nodes]

    def validate_transition(self, current_state: str, new_state: str) -> None:
        """Validates if a state transition is permitted in the state machine."""
        if new_state not in VALID_GOAL_STATES:
            raise ValueError(f"Invalid state target: {new_state}")
        if current_state == new_state:
            return
        transition = (current_state, new_state)
        if transition not in ALLOWED_TRANSITIONS:
            raise ValueError(f"Transition from {current_state} to {new_state} is not allowed.")

    def update_node_state(
        self, goal_id: str, new_state: str
    ) -> Tuple[GoalNode, List[Tuple[str, str, str]]]:
        """
        Transitions a node's state, enforcing the state machine.
        Returns the updated node and a list of (goal_id, old_state, new_state) transitions.
        """
        with self._lock:
            node = self._nodes.get(goal_id)
            if not node:
                raise ValueError(f"Goal ID {goal_id} not found.")

            old_state = node.state
            if old_state == new_state:
                return node, []

            self.validate_transition(old_state, new_state)
            node.state = new_state
            node.updated_at = datetime.utcnow()

            state_changes = [(goal_id, old_state, new_state)]

            if new_state == "COMPLETED":
                node.completed_at = datetime.utcnow()
                node.progress_percent = 100.0
            else:
                node.completed_at = None

            # Propagate progress changes and check cascading state completions
            self._rollup_progress_from(node.parent_goal_id, state_changes)

            return node, state_changes

    def update_node_progress(
        self, goal_id: str, progress_percent: float
    ) -> Tuple[GoalNode, float, List[Tuple[str, str, str]]]:
        """
        Updates progress for a leaf goal and propagates it upwards.
        Returns the updated node, the progress delta, and a list of cascading state changes.
        """
        with self._lock:
            node = self._nodes.get(goal_id)
            if not node:
                raise ValueError(f"Goal ID {goal_id} not found.")

            has_children = len(self._children.get(goal_id, [])) > 0
            if has_children:
                raise ValueError("Direct progress updates are not allowed on parent goals with children.")

            clamped_progress = max(0.0, min(100.0, progress_percent))
            old_progress = node.progress_percent
            delta = clamped_progress - old_progress

            node.progress_percent = clamped_progress
            node.updated_at = datetime.utcnow()

            state_changes = []
            if clamped_progress >= 100.0 and node.state == "ACTIVE":
                old_state = node.state
                node.state = "COMPLETED"
                node.completed_at = datetime.utcnow()
                state_changes.append((goal_id, old_state, "COMPLETED"))

            self._rollup_progress_from(node.parent_goal_id, state_changes)

            return node, delta, state_changes

    def _rollup_progress_from(self, parent_id: Optional[str], state_changes: List[Tuple[str, str, str]]) -> None:
        """Recursively recalculates progress rollups for parent nodes."""
        if not parent_id:
            return

        with self._lock:
            parent_node = self._nodes.get(parent_id)
            if not parent_node:
                return

            children_nodes = self.get_children(parent_id)
            if not children_nodes:
                return

            total_progress = sum(child.progress_percent for child in children_nodes)
            avg_progress = total_progress / len(children_nodes)

            parent_node.progress_percent = round(avg_progress, 2)
            parent_node.updated_at = datetime.utcnow()

            if parent_node.progress_percent >= 100.0 and parent_node.state == "ACTIVE":
                old_state = parent_node.state
                parent_node.state = "COMPLETED"
                parent_node.completed_at = datetime.utcnow()
                state_changes.append((parent_id, old_state, "COMPLETED"))

            self._rollup_progress_from(parent_node.parent_goal_id, state_changes)

    def serialize_hierarchy(self) -> List[dict]:
        """Serializes the entire tree into a list of node dictionaries."""
        with self._lock:
            return [node.to_dict() for node in self._nodes.values()]
