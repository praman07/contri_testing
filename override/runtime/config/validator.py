from override.runtime.config.schema import RuntimeConfigurationSchema

class ConfigurationValidator:
    """
    Validates a loaded RuntimeConfigurationSchema.
    Raises ValueError if configuration constraints are violated.
    """

    VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    VALID_PROVIDERS = {"gemini", "openai", "claude", "ollama"}

    @staticmethod
    def validate(config: RuntimeConfigurationSchema) -> None:
        # Validate logging
        log_cfg = config.logging
        if log_cfg.level.upper() not in ConfigurationValidator.VALID_LOG_LEVELS:
            raise ValueError(
                f"Invalid log level: {log_cfg.level}. Must be one of {ConfigurationValidator.VALID_LOG_LEVELS}"
            )
        if log_cfg.max_bytes <= 0:
            raise ValueError(f"log max_bytes must be positive: {log_cfg.max_bytes}")
        if log_cfg.backup_count < 0:
            raise ValueError(f"log backup_count cannot be negative: {log_cfg.backup_count}")

        # Validate model config
        model_cfg = config.model
        if model_cfg.provider.lower() not in ConfigurationValidator.VALID_PROVIDERS:
            raise ValueError(
                f"Invalid model provider: {model_cfg.provider}. Must be one of {ConfigurationValidator.VALID_PROVIDERS}"
            )
        if not (0.0 <= model_cfg.temperature <= 2.0):
            raise ValueError(f"Model temperature must be between 0.0 and 2.0, got: {model_cfg.temperature}")
        if not model_cfg.api_key_env_var:
            raise ValueError("api_key_env_var name cannot be empty")

        # Validate dashboard config
        dash_cfg = config.dashboard
        if not (1 <= dash_cfg.port <= 65535):
            raise ValueError(f"Dashboard port must be in range [1, 65535], got: {dash_cfg.port}")
        if not dash_cfg.host:
            raise ValueError("Dashboard host string cannot be empty")
