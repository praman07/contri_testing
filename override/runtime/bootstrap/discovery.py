import logging
from override.runtime.container.container import ServiceContainer
from override.runtime.registry.registry import ModuleRegistry

logger = logging.getLogger("Override.Bootstrap")

def discover_and_register_modules(container: ServiceContainer) -> None:
    """
    Placeholder scanning routine.
    In future layers, this scans directories or configurations to locate
    and register OverrideModule cognitive layers.
    """
    registry = container.resolve(ModuleRegistry)
    
    # Resolve and register ObservationEngine
    from override.runtime.observation.engine import ObservationEngine
    from override.runtime.registry.metadata import ModuleMetadata

    try:
        observation_engine = container.resolve(ObservationEngine)
        registry.register(
            observation_engine,
            ModuleMetadata(
                module_id="observation_engine",
                version="1.0.0",
                description="Layer 01 — Observation Engine: Collects raw signals from the environment",
                dependencies=[]
            )
        )
        logger.info("Registered ObservationEngine in ModuleRegistry.")
    except Exception as e:
        logger.error(f"Failed to register ObservationEngine: {e}")

    # Resolve and register EnvironmentEngine
    from override.runtime.environment.engine import EnvironmentEngine
    try:
        environment_engine = container.resolve(EnvironmentEngine)
        registry.register(
            environment_engine,
            ModuleMetadata(
                module_id="environment_engine",
                version="1.0.0",
                description="Layer 02 — Environment Engine: Tracks host environment state",
                dependencies=["observation_engine"]
            )
        )
        logger.info("Registered EnvironmentEngine in ModuleRegistry.")
    except Exception as e:
        logger.error(f"Failed to register EnvironmentEngine: {e}")

    # Resolve and register PerceptionEngine
    from override.runtime.perception.engine import PerceptionEngine
    try:
        perception_engine = container.resolve(PerceptionEngine)
        registry.register(
            perception_engine,
            ModuleMetadata(
                module_id="perception_engine",
                version="1.0.0",
                description="Layer 03 — Perception Engine: Transforms observations into structured PerceptionFrames",
                dependencies=["observation_engine", "environment_engine"]
            )
        )
        logger.info("Registered PerceptionEngine in ModuleRegistry.")
    except Exception as e:
        logger.error(f"Failed to register PerceptionEngine: {e}")

    # Resolve and register MemoryEngine
    from override.runtime.interfaces.memory import IMemoryEngine_v1
    try:
        memory_engine = container.resolve(IMemoryEngine_v1)
        registry.register(
            memory_engine,
            ModuleMetadata(
                module_id="memory_engine",
                version="1.0.0",
                description="Layer 04 — Memory Engine: Handles episodic, semantic, and procedural memories",
                dependencies=["perception_engine"]
            )
        )
        logger.info("Registered MemoryEngine in ModuleRegistry.")
    except Exception as e:
        logger.error(f"Failed to register MemoryEngine: {e}")

    # Resolve and register PlannerEngine
    from override.runtime.interfaces.planner import IPlannerEngine
    try:
        planner_engine = container.resolve(IPlannerEngine)
        registry.register(
            planner_engine,
            ModuleMetadata(
                module_id="planner_engine",
                version="1.0.0",
                description="Layer 05 — Planner Engine: Decomposes tasks and generates ExecutionPlans",
                dependencies=["perception_engine", "memory_engine"]
            )
        )
        logger.info("Registered PlannerEngine in ModuleRegistry.")
    except Exception as e:
        logger.error(f"Failed to register PlannerEngine: {e}")

    # Resolve and register ExecutionEngine
    from override.runtime.interfaces.execution import IExecutionEngine
    try:
        execution_engine = container.resolve(IExecutionEngine)
        registry.register(
            execution_engine,
            ModuleMetadata(
                module_id="execution_engine",
                version="1.0.0",
                description="Layer 06 — Execution Engine: Orchestrates and schedules PlanStep execution using capability providers",
                dependencies=["planner_engine"]
            )
        )
        logger.info("Registered ExecutionEngine in ModuleRegistry.")
    except Exception as e:
        logger.error(f"Failed to register ExecutionEngine: {e}")

    # Resolve and register VerificationEngine
    from override.runtime.interfaces.verification import IVerificationEngine
    try:
        verification_engine = container.resolve(IVerificationEngine)
        registry.register(
            verification_engine,
            ModuleMetadata(
                module_id="verification_engine",
                version="1.0.0",
                description="Layer 07 — Verification Engine: Subscribes to execution outcomes, evaluates verification rules, and reports results",
                dependencies=["execution_engine"]
            )
        )
        logger.info("Registered VerificationEngine in ModuleRegistry.")
    except Exception as e:
        logger.error(f"Failed to register VerificationEngine: {e}")

    # Resolve and register KnowledgeEngine (Layer 08)
    from override.runtime.interfaces.knowledge import IKnowledgeEngine
    try:
        knowledge_engine = container.resolve(IKnowledgeEngine)
        registry.register(
            knowledge_engine,
            ModuleMetadata(
                module_id="knowledge_engine",
                version="1.0.0",
                description="Layer 08 — Memory Consolidation & Knowledge Engine: Consolidates execution outcomes, learns patterns, and supports hybrid queries",
                dependencies=["verification_engine"]
            )
        )
        logger.info("Registered KnowledgeEngine in ModuleRegistry.")
    except Exception as e:
        logger.error(f"Failed to register KnowledgeEngine: {e}")

    # Resolve and register ContextEngine (Layer 09)
    from override.runtime.interfaces.context import IContextEngine
    try:
        context_engine = container.resolve(IContextEngine)
        registry.register(
            context_engine,
            ModuleMetadata(
                module_id="context_engine",
                version="1.0.0",
                description="Layer 09 — Context / World Model Engine: Aggregates environmental, perception, and memory signals into a coherent world model",
                dependencies=["perception_engine", "memory_engine"]
            )
        )
        logger.info("Registered ContextEngine in ModuleRegistry.")
    except Exception as e:
        logger.error(f"Failed to register ContextEngine: {e}")

    # Resolve and register GoalEngine (Layer 10)
    from override.runtime.interfaces.goal import IGoalEngine
    try:
        goal_engine = container.resolve(IGoalEngine)
        registry.register(
            goal_engine,
            ModuleMetadata(
                module_id="goal_engine",
                version="1.0.0",
                description="Layer 10 — Goal Engine: Tracks long-term user objectives and manages goal hierarchies",
                dependencies=["context_engine", "planner_engine"]
            )
        )
        logger.info("Registered GoalEngine in ModuleRegistry.")
    except Exception as e:
        logger.error(f"Failed to register GoalEngine: {e}")

    logger.info("Module discovery complete.")



