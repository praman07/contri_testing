import logging
from override.runtime.container.container import ServiceContainer
from override.runtime.container.lifetime import ServiceLifetime
from override.runtime.pal.factory import get_pal
from override.runtime.pal.base import PlatformAbstractionLayer
from override.runtime.config.config import ConfigurationManager
from override.runtime.logging.logger import LoggingService
from override.runtime.event.bus import EventBus
from override.runtime.interfaces.event import IEventBus
from override.runtime.health.monitor import HealthMonitor
from override.runtime.registry.registry import ModuleRegistry
from override.runtime.provider.manager import ProviderManager

def initialize_container() -> ServiceContainer:
    """
    Constructs and registers all foundational services in the Service Container.
    Establishes proper dependency injection paths without global singletons.
    """
    container = ServiceContainer()

    # 1. Register PAL
    container.register(
        PlatformAbstractionLayer,
        lambda container: get_pal(),
        ServiceLifetime.SINGLETON
    )

    # 2. Register Config Manager (reading from defaults)
    container.register(
        ConfigurationManager,
        lambda container: ConfigurationManager(),
        ServiceLifetime.SINGLETON
    )

    # 3. Register Logging Service
    container.register(
        LoggingService,
        lambda container: LoggingService(container.resolve(ConfigurationManager).logging),
        ServiceLifetime.SINGLETON
    )

    # 4. Register Event Bus
    container.register(
        IEventBus,
        lambda container: EventBus(),
        ServiceLifetime.SINGLETON
    )

    # 5. Register Health Monitor
    container.register(
        HealthMonitor,
        lambda container: HealthMonitor(container.resolve(PlatformAbstractionLayer)),
        ServiceLifetime.SINGLETON
    )

    # 6. Register Module Registry
    container.register(
        ModuleRegistry,
        lambda container: ModuleRegistry(),
        ServiceLifetime.SINGLETON
    )

    # 7. Register Provider Manager
    container.register(
        ProviderManager,
        lambda container: ProviderManager(),
        ServiceLifetime.SINGLETON
    )

    # 8. Register Observation Engine
    from override.runtime.observation.engine import ObservationEngine
    container.register(
        ObservationEngine,
        lambda container: ObservationEngine(
            event_bus=container.resolve(IEventBus),
            pal=container.resolve(PlatformAbstractionLayer),
            config=container.resolve(ConfigurationManager)
        ),
        ServiceLifetime.SINGLETON
    )

    # 9. Register Environment Engine
    from override.runtime.environment.engine import EnvironmentEngine
    container.register(
        EnvironmentEngine,
        lambda container: EnvironmentEngine(
            event_bus=container.resolve(IEventBus),
            pal=container.resolve(PlatformAbstractionLayer),
            config=container.resolve(ConfigurationManager)
        ),
        ServiceLifetime.SINGLETON
    )

    # 10. Register Perception Engine
    from override.runtime.perception.engine import PerceptionEngine
    container.register(
        PerceptionEngine,
        lambda container: PerceptionEngine(
            event_bus=container.resolve(IEventBus),
            config=container.resolve(ConfigurationManager)
        ),
        ServiceLifetime.SINGLETON
    )

    # 11. Register Mock/Stub Embedding Service
    from override.runtime.interfaces.memory import IEmbeddingService, IMemoryEngine_v1
    from typing import List

    class MockEmbeddingService(IEmbeddingService):
        """Simple default Mock/Stub Embedding Service returning 128-dimensional mock vectors."""
        async def get_embedding(self, text: str) -> List[float]:
            import hashlib
            h = hashlib.sha256(text.encode("utf-8")).digest()
            vector = []
            for i in range(16):
                val = float(h[i % len(h)]) / 255.0
                vector.append(val)
            return vector * 8

    container.register(
        IEmbeddingService,
        lambda container: MockEmbeddingService(),
        ServiceLifetime.SINGLETON
    )

    # 12. Register Memory Engine
    from override.runtime.memory.engine import MemoryEngine
    container.register(
        IMemoryEngine_v1,
        lambda container: MemoryEngine(
            event_bus=container.resolve(IEventBus),
            config=container.resolve(ConfigurationManager),
            embedding_service=container.resolve(IEmbeddingService),
            db_path=container.resolve(ConfigurationManager).schema.custom_settings.get("db_path", "data/memory.db")
        ),
        ServiceLifetime.SINGLETON
    )

    # 13. Register Planner Engine
    from override.runtime.interfaces.planner import IPlannerEngine
    from override.runtime.planner.engine import PlannerEngine
    container.register(
        IPlannerEngine,
        lambda container: PlannerEngine(
            event_bus=container.resolve(IEventBus),
            config=container.resolve(ConfigurationManager)
        ),
        ServiceLifetime.SINGLETON
    )

    # 14. Register Execution Engine
    from override.runtime.interfaces.execution import IExecutionEngine
    from override.runtime.execution.engine import ExecutionEngine
    container.register(
        IExecutionEngine,
        lambda container: ExecutionEngine(
            event_bus=container.resolve(IEventBus),
            provider_manager=container.resolve(ProviderManager),
            config=container.resolve(ConfigurationManager)
        ),
        ServiceLifetime.SINGLETON
    )

    # 15. Register Verification Engine
    from override.runtime.interfaces.verification import IVerificationEngine
    from override.runtime.verification.engine import VerificationEngine
    container.register(
        IVerificationEngine,
        lambda container: VerificationEngine(
            event_bus=container.resolve(IEventBus),
            config=container.resolve(ConfigurationManager)
        ),
        ServiceLifetime.SINGLETON
    )

    # 16. Register Memory Consolidation & Knowledge Engine (Layer 08)
    from override.runtime.interfaces.knowledge import IKnowledgeEngine
    from override.runtime.knowledge.engine import KnowledgeEngine
    container.register(
        IKnowledgeEngine,
        lambda container: KnowledgeEngine(
            event_bus=container.resolve(IEventBus),
            config=container.resolve(ConfigurationManager),
            embedding_service=container.resolve(IEmbeddingService),
            db_path=container.resolve(ConfigurationManager).schema.custom_settings.get("knowledge_db_path", "data/knowledge.db")
        ),
        ServiceLifetime.SINGLETON
    )

    # 17. Register Context / World Model Engine (Layer 09)
    from override.runtime.interfaces.context import IContextEngine
    from override.runtime.context.engine import ContextEngine
    container.register(
        IContextEngine,
        lambda container: ContextEngine(
            event_bus=container.resolve(IEventBus),
            config=container.resolve(ConfigurationManager)
        ),
        ServiceLifetime.SINGLETON
    )

    # 18. Register Goal Engine (Layer 10)
    from override.runtime.interfaces.goal import IGoalEngine
    from override.runtime.goal.engine import GoalEngine
    container.register(
        IGoalEngine,
        lambda container: GoalEngine(
            event_bus=container.resolve(IEventBus),
            config=container.resolve(ConfigurationManager)
        ),
        ServiceLifetime.SINGLETON
    )

    return container



