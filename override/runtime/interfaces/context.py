from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from override.runtime.interfaces.engine import ICognitiveEngine

class IContextEngine(ICognitiveEngine):
    """
    Versioned public interface for the Layer 09 Context / World Model Engine.
    Maintains the runtime cognitive understanding of the user's active environment,
    active window, running applications, clipboard, system states, and perceived intent.
    """

    @abstractmethod
    async def get_current_state(self) -> Dict[str, Any]:
        """
        Retrieves the unified current state of the world model (context frame).
        
        Returns:
            A dictionary representing the compiled WorldState / ContextFrame.
        """
        pass

    @abstractmethod
    async def get_active_window(self) -> Dict[str, Any]:
        """
        Retrieves the details of the currently focused active window.
        
        Returns:
            A dictionary containing window metadata (title, process name, boundaries).
        """
        pass

    @abstractmethod
    async def get_running_applications(self) -> List[Dict[str, Any]]:
        """
        Retrieves the list of currently running applications.
        
        Returns:
            A list of dictionary summaries of active processes.
        """
        pass

    @abstractmethod
    async def get_clipboard_context(self) -> Optional[str]:
        """
        Retrieves the current parsed/redacted content of the clipboard.
        
        Returns:
            A string containing the clipboard contents, or None.
        """
        pass

    @abstractmethod
    async def get_host_environment_summary(self) -> Dict[str, Any]:
        """
        Retrieves the summary of host environment resources.
        
        Returns:
            A dictionary of host system metrics (CPU, Memory, Disk, Network, Battery).
        """
        pass
