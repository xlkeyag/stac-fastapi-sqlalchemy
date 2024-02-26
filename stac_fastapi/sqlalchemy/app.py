"""FastAPI application."""
import os
import jwt

from fastapi import Depends
from stac_fastapi.api.app import StacApi
from stac_fastapi.api.models import create_get_request_model, create_post_request_model
from stac_fastapi.extensions.core import (
    ContextExtension,
    FieldsExtension,
    SortExtension,
    TokenPaginationExtension,
    TransactionExtension,
)
from stac_fastapi.extensions.third_party import BulkTransactionExtension

from stac_fastapi.sqlalchemy.config import SqlalchemySettings
from stac_fastapi.sqlalchemy.core import CoreCrudClient
from stac_fastapi.sqlalchemy.extensions import QueryExtension
from stac_fastapi.sqlalchemy.session import Session
from stac_fastapi.sqlalchemy.transactions import (
    BulkTransactionsClient,
    TransactionsClient,
)

from fastapi import HTTPException, Request, status
from typing import Dict


def validate_jwt(request: Request) -> Dict:
    """Validate JWT token."""
    try:
        token = request.headers["Authorization"].split("Bearer ")[1]
        return jwt.decode(token, key="our-secret-key", algorithms=["HS256"], options={"verify_signature": False})
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


settings = SqlalchemySettings()
session = Session.create_from_settings(settings)
extensions = [
    TransactionExtension(client=TransactionsClient(
        session=session), settings=settings),
    BulkTransactionExtension(client=BulkTransactionsClient(session=session)),
    FieldsExtension(),
    QueryExtension(),
    SortExtension(),
    TokenPaginationExtension(),
    ContextExtension(),
]

post_request_model = create_post_request_model(extensions)

api = StacApi(
    settings=settings,
    extensions=extensions,
    client=CoreCrudClient(
        session=session, extensions=extensions, post_request_model=post_request_model
    ),
    search_get_request_model=create_get_request_model(extensions),
    search_post_request_model=post_request_model,
    # Add route dependencies to all routes
    route_dependencies=[
        (
            [
                {"path": "/collections", "method": "GET"},
                {"path": "/collections", "method": "POST"},
                {"path": "/collections", "method": "PUT"},
                {"path": "/collections/{collectionId}", "method": "GET"},
                {"path": "/collections/{collectionId}", "method": "DELETE"},
                {"path": "/collections/{collectionId}/items", "method": "GET"},
                {"path": "/collections/{collectionId}/items", "method": "POST"},
                {"path": "/collections/{collectionId}/items", "method": "PUT"},
                {"path": "/collections/{collectionId}/items/{itemId}", "method": "GET"},
                {"path": "/collections/{collectionId}/items/{itemId}",
                    "method": "DELETE"},
            ],
            [Depends(validate_jwt)]
        ),
    ]
)
app = api.app


def run():
    """Run app from command line using uvicorn if available."""
    try:
        import uvicorn

        uvicorn.run(
            "stac_fastapi.sqlalchemy.app:app",
            host=settings.app_host,
            port=settings.app_port,
            log_level="info",
            reload=settings.reload,
            root_path=os.getenv("UVICORN_ROOT_PATH", ""),
        )
    except ImportError:
        raise RuntimeError("Uvicorn must be installed in order to use command")


if __name__ == "__main__":
    run()


def create_handler(app):
    """Create a handler to use with AWS Lambda if mangum available."""
    try:
        from mangum import Mangum

        return Mangum(app)
    except ImportError:
        return None


handler = create_handler(app)
