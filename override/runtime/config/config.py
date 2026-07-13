from override.runtime.config.schema import RuntimeConfigurationSchema
from override.runtime.config.loader import ConfigurationLoader

class ConfigurationManager:
    """
    Configuration Manager service.
    Exposes a read-only view of the loaded runtime settings.
    """

    def __init__(self, file_path: str = "config/settings.json"):
        self._schema = ConfigurationLoader.load(file_path)

    @property
    def schema(self) -> RuntimeConfigurationSchema:
        """Returns the read-only RuntimeConfigurationSchema instance."""
        return self._schema

    @property
    def logging(self):
        return self._schema.logging

    @property
    def model(self):
        return self._schema.model

    @property
    def dashboard(self):
        return self._schema.dashboard

    @property
    def safety_confirmations_required(self) -> bool:
        return self._schema.safety_confirmations_required

    @property
    def planner(self):
        return self._schema.planner

    @property
    def execution(self):
        return self._schema.execution
