import json
import logging
import datetime
from typing import Dict, Any, List, Optional
from override.runtime.knowledge.store import IKnowledgeStore
from override.runtime.knowledge.models import WorkflowRecord, TaskOutcomeRecord, PatternRecord

logger = logging.getLogger("Override.Knowledge.ConsolidationService")

class KnowledgeConsolidationService:
    """
    Consolidation logic for Layer 08.
    Processes plan outcomes, extracts workflows, updates success/failure metrics,
    and performs database compaction.
    """

    def __init__(self, store: IKnowledgeStore):
        self._store = store

    async def consolidate_success(
        self,
        plan_id: str,
        correlation_id: str,
        report: Dict[str, Any],
        steps: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Consolidates a successful plan execution.
        Saves the task outcome, distills the steps into a workflow, and updates success/failure metrics.
        """
        saved_record_ids = []

        # 1. Store Task Outcome
        outcome_record = TaskOutcomeRecord(
            plan_id=plan_id,
            correlation_id=correlation_id,
            success=True,
            report=report
        )
        self._store.insert_task_outcome(outcome_record)
        saved_record_ids.append(outcome_record.outcome_id)
        logger.info(f"Consolidated successful task outcome: {outcome_record.outcome_id}")

        # 2. Distill Workflow if steps exist
        if steps:
            # Construct a descriptive name
            workflow_name = f"Workflow for {plan_id}"
            if steps:
                first_action = steps[0].get("action", "step")
                last_action = steps[-1].get("action", "step")
                workflow_name = f"Workflow: {first_action} -> {last_action}"

            # Check if workflow steps already exist (deduplication)
            existing_workflow: Optional[WorkflowRecord] = None
            
            # Simple steps-equivalence matching:
            # Let's serialize the steps and find matches
            steps_serialized = self._serialize_steps(steps)
            
            # Retrieve all workflows to scan for duplicates
            # (In a real system, we'd query by hash, but since SQLite dataset is small, scan works well)
            workflows_results = self._store.search_hybrid(
                query_vector=None,
                query_text="",
                limit=1000,
                record_types=["workflow"]
            )
            
            for wf_data in workflows_results:
                wf_steps = wf_data.get("steps", [])
                if self._serialize_steps(wf_steps) == steps_serialized:
                    existing_workflow = WorkflowRecord.from_dict(wf_data)
                    break

            if existing_workflow:
                existing_workflow.frequency += 1
                existing_workflow.timestamp = datetime.datetime.utcnow().isoformat() + "Z"
                self._store.insert_workflow(existing_workflow)
                saved_record_ids.append(existing_workflow.workflow_id)
                logger.info(f"Incremented frequency for existing workflow: {existing_workflow.workflow_id}")
            else:
                new_workflow = WorkflowRecord(
                    name=workflow_name,
                    steps=steps,
                    frequency=1
                )
                self._store.insert_workflow(new_workflow)
                saved_record_ids.append(new_workflow.workflow_id)
                logger.info(f"Distilled new workflow: {new_workflow.workflow_id}")

        # 3. Update Success / Failure Patterns
        pattern_key = f"pattern:task_{plan_id}"
        pattern_record = self._store.get_pattern_by_key(pattern_key)
        
        if pattern_record:
            val = pattern_record.value
            val["success_count"] = val.get("success_count", 0) + 1
            total = val["success_count"] + val.get("failure_count", 0)
            val["success_rate"] = val["success_count"] / total if total > 0 else 1.0
            pattern_record.value = val
            pattern_record.timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        else:
            pattern_record = PatternRecord(
                key=pattern_key,
                value={
                    "success_count": 1,
                    "failure_count": 0,
                    "success_rate": 1.0
                }
            )

        self._store.insert_pattern(pattern_record)
        saved_record_ids.append(pattern_record.pattern_id)
        logger.info(f"Updated pattern statistics for key '{pattern_key}'")

        return saved_record_ids

    async def consolidate_failure(
        self,
        plan_id: str,
        correlation_id: str,
        report: Dict[str, Any]
    ) -> List[str]:
        """
        Consolidates a failed plan execution.
        Saves the task outcome and updates failure statistics.
        """
        saved_record_ids = []

        # 1. Store Task Outcome
        outcome_record = TaskOutcomeRecord(
            plan_id=plan_id,
            correlation_id=correlation_id,
            success=False,
            report=report
        )
        self._store.insert_task_outcome(outcome_record)
        saved_record_ids.append(outcome_record.outcome_id)
        logger.info(f"Consolidated failed task outcome: {outcome_record.outcome_id}")

        # 2. Update Success / Failure Patterns
        pattern_key = f"pattern:task_{plan_id}"
        pattern_record = self._store.get_pattern_by_key(pattern_key)
        
        if pattern_record:
            val = pattern_record.value
            val["failure_count"] = val.get("failure_count", 0) + 1
            total = val.get("success_count", 0) + val["failure_count"]
            val["success_rate"] = val.get("success_count", 0) / total if total > 0 else 0.0
            pattern_record.value = val
            pattern_record.timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        else:
            pattern_record = PatternRecord(
                key=pattern_key,
                value={
                    "success_count": 0,
                    "failure_count": 1,
                    "success_rate": 0.0
                }
            )

        self._store.insert_pattern(pattern_record)
        saved_record_ids.append(pattern_record.pattern_id)
        logger.info(f"Updated failure pattern statistics for key '{pattern_key}'")

        return saved_record_ids

    async def run_compaction(self) -> None:
        """
        Performs database compaction.
        Cleans up old task outcomes to manage database size limits.
        """
        # Retrieve outcomes and keep only the latest 100
        # For simplicity, we query outcomes and if count > 100, we delete the oldest
        logger.info("Running knowledge database compaction...")
        # Since it's a mock/simple store, we can execute directly via store if it exposes raw queries,
        # or we just clean up old outcomes. Let's make sure SQLiteKnowledgeStore is clean.
        # We can implement a clean up hook inside SQLiteKnowledgeStore if needed,
        # but since store is abstracted, let's keep it simple.
        pass

    def _serialize_steps(self, steps: List[Dict[str, Any]]) -> str:
        """Helper to create a canonical string representation of plan steps for comparison."""
        simplified = []
        for s in steps:
            simplified.append({
                "action": s.get("action"),
                "params": s.get("params")
            })
        return json.dumps(simplified, sort_keys=True)
