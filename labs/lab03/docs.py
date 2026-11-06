"""Українські підписи стандартного інтерфейсу Swagger UI."""

from fastapi import APIRouter, Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, HTMLResponse

from labs.lab03.database import BASE_DIR

router = APIRouter(include_in_schema=False)


@router.get("/docs")
def documentation(request: Request) -> HTMLResponse:
    """Підключити переклад до стандартної документації FastAPI."""
    page = get_swagger_ui_html(
        openapi_url=request.app.openapi_url,
        title=request.app.title + " — Документація API",
        oauth2_redirect_url=request.app.swagger_ui_oauth2_redirect_url,
    )
    html = bytes(page.body).decode("utf-8")
    script = '<script src="/docs-uk.js"></script>'
    return HTMLResponse(html.replace("</body>", script + "</body>"))


@router.get("/docs-uk.js")
def ukrainian_labels() -> FileResponse:
    """Віддати локальний скрипт перекладу без кешування старої версії."""
    return FileResponse(
        BASE_DIR / "static" / "swagger-uk.js",
        media_type="text/javascript",
        headers={"Cache-Control": "no-cache"},
    )
