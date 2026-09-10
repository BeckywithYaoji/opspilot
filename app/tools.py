"""Exactly four tools. Their order is chosen by the model, never this module."""
from typing import Annotated, Any

from langchain_core.tools import tool
from pydantic import Field

from app.environment import MockEnvironment


NonEmpty = Annotated[str, Field(min_length=1)]


def build_tools(environment: MockEnvironment) -> dict:
    @tool
    def check_port(host: NonEmpty, port: Annotated[int, Field(ge=1, le=65535)]) -> dict[str, Any]:
        """Inspect whether a specific TCP port is open or closed. Use when port state is relevant; do not inspect unrelated services for a simple port check."""
        return environment.check_port(host, port)

    @tool
    def check_service(host: NonEmpty, service: NonEmpty) -> dict[str, Any]:
        """Inspect a named service when its status is relevant to diagnosis or verification. Do not expand a simple request into unrelated diagnostics."""
        return environment.check_service(host, service)

    @tool
    def restart_service(host: NonEmpty, service: NonEmpty) -> dict[str, Any]:
        """Restart a service only when observations support it. Never assume success; verify only what is needed for the user's goal."""
        return environment.restart_service(host, service)

    @tool
    def create_ticket(title: NonEmpty, description: NonEmpty) -> dict[str, Any]:
        """Create a ticket only when automatic resolution cannot proceed, manual intervention or permission is required, or the user explicitly asks. Do not ticket an already resolved issue."""
        return environment.create_ticket(title, description)

    return {item.name: item for item in (check_port, check_service, restart_service, create_ticket)}
