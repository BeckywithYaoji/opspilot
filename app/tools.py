"""Exactly four tools. Their order is chosen by the model, never this module."""
from typing import Annotated, Any

from langchain_core.tools import tool
from pydantic import Field

from app.environment import MockEnvironment


NonEmpty = Annotated[str, Field(min_length=1)]


def build_tools(environment: MockEnvironment) -> dict:
    @tool
    def check_port(host: NonEmpty, port: Annotated[int, Field(ge=1, le=65535)]) -> dict[str, Any]:
        """Check a TCP port on a mock host; reports open, closed or unreachable."""
        return environment.check_port(host, port)

    @tool
    def check_service(host: NonEmpty, service: NonEmpty) -> dict[str, Any]:
        """Inspect a mock service's current status (for example sshd)."""
        return environment.check_service(host, service)

    @tool
    def restart_service(host: NonEmpty, service: NonEmpty) -> dict[str, Any]:
        """Attempt a mock service restart. Can fail with permission denied."""
        return environment.restart_service(host, service)

    @tool
    def create_ticket(title: NonEmpty, description: NonEmpty) -> dict[str, Any]:
        """Create a simulated human operations ticket with findings and remaining work."""
        return environment.create_ticket(title, description)

    return {item.name: item for item in (check_port, check_service, restart_service, create_ticket)}
