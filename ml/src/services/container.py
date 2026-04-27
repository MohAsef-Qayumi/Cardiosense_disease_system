"""Application container assembly for CardioSense."""

from dataclasses import dataclass

from src.core.settings import Settings
from src.repositories.base import RepositoryBundle
from src.repositories.inmemory import build_inmemory_repository_bundle
from src.repositories.mongodb import build_mongodb_repository_bundle
from src.services.analytics_service import AnalyticsService
from src.services.auth_service import AuthService
from src.services.drift import DriftMonitoringService
from src.services.model_registry import ModelRegistryService
from src.services.prediction_service import PredictionService


@dataclass
class ApplicationContainer:
    """Runtime container for service dependencies."""

    settings: Settings
    repositories: RepositoryBundle
    model_registry: ModelRegistryService
    drift_service: DriftMonitoringService
    prediction_service: PredictionService
    analytics_service: AnalyticsService
    auth_service: AuthService

    async def initialize(self) -> None:
        await self.repositories.initialize()

    async def close(self) -> None:
        await self.repositories.close()


def build_container(settings: Settings) -> ApplicationContainer:
    """Create the runtime dependency container."""
    repositories = (
        build_inmemory_repository_bundle()
        if settings.db_backend == "inmemory"
        else build_mongodb_repository_bundle(settings)
    )
    model_registry = ModelRegistryService(repositories.model_versions, settings)
    drift_service = DriftMonitoringService(repositories.drift_snapshots, settings)
    prediction_service = PredictionService(repositories, settings, model_registry, drift_service)
    analytics_service = AnalyticsService(repositories.predictions)
    auth_service = AuthService(repositories.users, settings)
    return ApplicationContainer(
        settings=settings,
        repositories=repositories,
        model_registry=model_registry,
        drift_service=drift_service,
        prediction_service=prediction_service,
        analytics_service=analytics_service,
        auth_service=auth_service,
    )
