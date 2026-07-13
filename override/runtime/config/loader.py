import os
import json
from typing import Dict, Any
from override.runtime.config.schema import RuntimeConfigurationSchema, LoggingConfig, ModelConfig, DashboardConfig, PlannerConfig, ExecutionConfig
from override.runtime.config.validator import ConfigurationValidator

class ConfigurationLoader:
    """
    Loads runtime configuration from JSON files, overrides values
    with environment variables, and instantiates the validated schema.
    """

    @staticmethod
    def load(file_path: str = "config/settings.json") -> RuntimeConfigurationSchema:
        raw_data: Dict[str, Any] = {}

        # 1. Attempt to load from settings file
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
            except Exception as e:
                # Fall back to empty dictionary and let env vars / defaults take over
                pass

        # 2. Extract nested sections or fall back to defaults
        log_raw = raw_data.get("logging", {})
        model_raw = raw_data.get("model", {})
        dash_raw = raw_data.get("dashboard", {})
        plan_raw = raw_data.get("planner", {})
        exec_raw = raw_data.get("execution", {})

        # 3. Apply Environment Variable Overrides
        log_level = os.getenv("OVERRIDE_LOG_LEVEL", log_raw.get("level", "INFO"))
        log_file = os.getenv("OVERRIDE_LOG_FILE", log_raw.get("file_path", "logs/override.log"))
        
        model_prov = os.getenv("OVERRIDE_MODEL_PROVIDER", model_raw.get("provider", "gemini"))
        model_name = os.getenv("OVERRIDE_MODEL_NAME", model_raw.get("model_name", "gemini-2.5-flash"))
        model_temp = float(os.getenv("OVERRIDE_MODEL_TEMP", model_raw.get("temperature", 0.0)))

        dash_host = os.getenv("OVERRIDE_DASHBOARD_HOST", dash_raw.get("host", "127.0.0.1"))
        dash_port = int(os.getenv("OVERRIDE_DASHBOARD_PORT", dash_raw.get("port", 8000)))
        dash_secure = os.getenv("OVERRIDE_DASHBOARD_SECURE", str(dash_raw.get("secure", True))).lower() == "true"

        plan_val = os.getenv("OVERRIDE_PLANNER_VALIDATION", str(plan_raw.get("plan_validation_enabled", True))).lower() == "true"
        plan_max = int(os.getenv("OVERRIDE_PLANNER_MAX_STEPS", plan_raw.get("max_steps_per_plan", 20)))
        plan_parallel = os.getenv("OVERRIDE_PLANNER_ALLOW_PARALLEL", str(plan_raw.get("allow_parallel_execution", True))).lower() == "true"

        exec_timeout = int(os.getenv("OVERRIDE_EXECUTION_TIMEOUT", exec_raw.get("timeout_seconds", 30)))
        exec_retry = int(os.getenv("OVERRIDE_EXECUTION_RETRY", exec_raw.get("retry_count", 3)))
        exec_limit = int(os.getenv("OVERRIDE_EXECUTION_CONCURRENT_LIMIT", exec_raw.get("concurrent_steps_limit", 4)))
        exec_queue = int(os.getenv("OVERRIDE_EXECUTION_QUEUE_SIZE", exec_raw.get("execution_queue_size", 100)))

        # 4. Construct final dataclass instances
        log_config = LoggingConfig(
            level=log_level,
            file_path=log_file,
            max_bytes=int(log_raw.get("max_bytes", 10485760)),
            backup_count=int(log_raw.get("backup_count", 5))
        )

        model_config = ModelConfig(
            provider=model_prov,
            model_name=model_name,
            temperature=model_temp,
            api_key_env_var=model_raw.get("api_key_env_var", "GEMINI_API_KEY")
        )

        dash_config = DashboardConfig(
            host=dash_host,
            port=dash_port,
            secure=dash_secure
        )

        planner_config = PlannerConfig(
            plan_validation_enabled=plan_val,
            max_steps_per_plan=plan_max,
            allow_parallel_execution=plan_parallel
        )

        exec_config = ExecutionConfig(
            timeout_seconds=exec_timeout,
            retry_count=exec_retry,
            concurrent_steps_limit=exec_limit,
            execution_queue_size=exec_queue
        )

        schema_instance = RuntimeConfigurationSchema(
            logging=log_config,
            model=model_config,
            dashboard=dash_config,
            planner=planner_config,
            execution=exec_config,
            safety_confirmations_required=raw_data.get("safety_confirmations_required", True),
            custom_settings=raw_data.get("custom_settings", {})
        )

        # 5. Enforce strict validation before return
        ConfigurationValidator.validate(schema_instance)

        return schema_instance
