from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"
    file_path: str = "logs/override.log"
    max_bytes: int = 10485760  # 10MB
    backup_count: int = 5

@dataclass(frozen=True)
class ModelConfig:
    provider: str = "gemini"
    model_name: str = "gemini-2.5-flash"
    temperature: float = 0.0
    api_key_env_var: str = "GEMINI_API_KEY"

@dataclass(frozen=True)
class DashboardConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    secure: bool = True

@dataclass(frozen=True)
class PlannerConfig:
    plan_validation_enabled: bool = True
    max_steps_per_plan: int = 20
    allow_parallel_execution: bool = True

@dataclass(frozen=True)
class ExecutionConfig:
    timeout_seconds: int = 30
    retry_count: int = 3
    concurrent_steps_limit: int = 4
    execution_queue_size: int = 100

@dataclass(frozen=True)
class RuntimeConfigurationSchema:
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    planner: PlannerConfig = field(default_factory=PlannerConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    safety_confirmations_required: bool = True
    custom_settings: Dict[str, Any] = field(default_factory=dict)
