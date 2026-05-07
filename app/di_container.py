"""Dependency injection container configuration for onboarding service."""
import logging
from injector import Injector, Module, provider, singleton
from fastapi import FastAPI
from fastapi_injector import attach_injector

# Infrastructure interfaces - HEL-276
from app.interfaces.asset_repository_interface import IAssetRepository
from app.interfaces.s3_client_interface import IS3Client
from app.interfaces.web_search_interface import IWebSearchClient
from app.interfaces.ragie_client_interface import IRagieClient
from app.interfaces.anthropic_client_interface import IAnthropicClient
from app.interfaces.document_search_service_interface import IDocumentSearchService
from app.interfaces.document_processing_service_interface import IDocumentProcessingService
from app.interfaces.ssm_client_interface import ISSMClient

# Infrastructure interfaces - from origin/main
from app.interfaces.dynamo_client_interface import IDynamoClient
from app.interfaces.date_provider_interface import IDateProvider
from app.interfaces.memory_cache_interface import IMemoryCache
from app.interfaces.private_documents_repository_interface import IPrivateDocumentsRepository
from app.interfaces.cdn_repository_interface import ICDNRepository

# Infrastructure implementations - HEL-276
from app.infrastructure.clients.tavily_search_client import TavilySearchClient
from app.infrastructure.clients.ragie import RagieClient
from app.infrastructure.clients.bedrock import BedrockClient

# Infrastructure implementations - from origin/main
from app.infrastructure.clients.ddb import DynamoClient
from app.infrastructure.clients.s3 import S3Client
from app.infrastructure.clients.ssm import SSMClient
from app.utils.system_date_provider import SystemDateProvider
from app.infrastructure.repositories.asset_repository import AssetRepository
from app.infrastructure.repositories.private_documents_repository import PrivateDocumentsRepository
from app.infrastructure.repositories.cdn_repository import CDNRepository
from app.utils.memory_cache import CacheOutMemoryCache

# Services
from app.services.asset_onboarding_service import AssetOnboardingService
from app.services.document_processing_service import DocumentProcessingService
from app.services.document_search_service import DocumentSearchService

# Service interfaces
from app.interfaces.asset_onboarding_service_interface import IAssetOnboardingService

logger = logging.getLogger(__name__)


class InfrastructureModule(Module):
    """Provides infrastructure dependencies with proper lifecycle management."""
    
    @singleton
    @provider
    def provide_dynamo_client(self, memory_cache: IMemoryCache) -> IDynamoClient:
        return DynamoClient(memory_cache)
    
    @singleton
    @provider
    def provide_s3_client(self) -> IS3Client:
        return S3Client()
    
    @singleton
    @provider
    def provide_ssm_client(self) -> ISSMClient:
        return SSMClient()


class RepositoryModule(Module):
    """Provides repository dependencies."""
    
    @provider
    def provide_asset_repository(self, dynamo_client: IDynamoClient) -> IAssetRepository:
        return AssetRepository(dynamo_client)
    
    @provider
    def provide_private_documents_repository(self, s3_client: IS3Client) -> IPrivateDocumentsRepository:
        return PrivateDocumentsRepository(s3_client)
    
    @provider
    def provide_cdn_repository(self, s3_client: IS3Client, ssm_client: ISSMClient, memory_cache: IMemoryCache) -> ICDNRepository:
        return CDNRepository(s3_client, ssm_client, memory_cache)
    


class ServiceModule(Module):
    """Provides service dependencies."""
    
    @singleton
    @provider
    def provide_memory_cache(self) -> IMemoryCache:
        return CacheOutMemoryCache(maxsize=1000)

    @provider
    def provide_date_provider(self) -> IDateProvider:
        return SystemDateProvider()
    
    @singleton
    @provider
    def provide_web_search_client(self) -> IWebSearchClient:
        return TavilySearchClient()
    
    @singleton
    @provider
    def provide_ragie_client(self) -> IRagieClient:
        return RagieClient()
    
    @singleton
    @provider
    def provide_anthropic_client(self) -> IAnthropicClient:
        return BedrockClient()
    
    @singleton
    @provider
    def provide_document_search_service(
        self,
        web_search_client: IWebSearchClient,
        ragie_client: IRagieClient,
        cdn_repository: ICDNRepository
    ) -> IDocumentSearchService:
        return DocumentSearchService(
            web_search_client=web_search_client,
            ragie_client=ragie_client,
            cdn_repository=cdn_repository
        )
    
    @provider
    def provide_asset_onboarding_service(
        self,
        asset_repository: IAssetRepository,
        document_search_service: IDocumentSearchService,
        private_documents_repository: IPrivateDocumentsRepository,
        web_search_client: IWebSearchClient,
        date_provider: IDateProvider,
        document_processing_service: IDocumentProcessingService
    ) -> IAssetOnboardingService:
        return AssetOnboardingService(
            asset_repository=asset_repository,
            document_search_service=document_search_service,
            document_storage=private_documents_repository,
            web_search_client=web_search_client,
            date_provider=date_provider,
            document_processing_service=document_processing_service
        )
    
    @provider
    def provide_document_processing_service(
        self,
        asset_repository: IAssetRepository,
        private_documents_repository: IPrivateDocumentsRepository,
        cdn_repository: ICDNRepository,
        ragie_client: IRagieClient,
        date_provider: IDateProvider
    ) -> IDocumentProcessingService:
        return DocumentProcessingService(
            asset_repository=asset_repository,
            document_storage=private_documents_repository,
            cdn_repository=cdn_repository,
            ragie_client=ragie_client,
            date_provider=date_provider
        )


def create_injector() -> Injector:
    """Creates and configures the injector with all modules."""
    return Injector([
        InfrastructureModule,
        RepositoryModule,
        ServiceModule
    ])


def configure_dependencies(app: FastAPI) -> None:
    """Configure dependency injection for the FastAPI application."""
    injector = create_injector()
    attach_injector(app, injector)
    logger.info("Dependency injection configured for onboarding service")
