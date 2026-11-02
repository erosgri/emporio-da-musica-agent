from __future__ import annotations

from dataclasses import dataclass

from emporio_agent.config import Settings, get_settings
from emporio_agent.database import initialize_database
from emporio_agent.policy import PolicyRetriever, load_or_build_policy_index
from emporio_agent.repositories import OrderRepository, ProductRepository
from emporio_agent.services import CommerceService
from emporio_agent.tools import ToolRegistry


@dataclass(frozen=True)
class Application:
    settings: Settings
    tools: ToolRegistry


def build_application(
    settings: Settings | None = None, *, force_ingestion: bool = False
) -> Application:
    settings = settings or get_settings()
    database_path = initialize_database(settings, force=force_ingestion)
    chunks = load_or_build_policy_index(settings.policy_pdf_path, settings.policy_index_path)

    products = ProductRepository(database_path)
    orders = OrderRepository(database_path)
    commerce = CommerceService(products)
    policies = PolicyRetriever(chunks)
    tools = ToolRegistry(products, orders, commerce, policies)
    return Application(settings=settings, tools=tools)
