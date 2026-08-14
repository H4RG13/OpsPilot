import uuid
from collections.abc import Callable

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import AuthContext, require_role
from app.modules.imports import service
from app.modules.imports.dependencies import get_import_dispatcher
from app.modules.imports.models import ImportType
from app.modules.imports.schemas import ImportJobResponse, import_job_to_response
from app.shared.permissions import Role

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/csv", response_model=ImportJobResponse, status_code=status.HTTP_201_CREATED)
async def upload_csv(
    import_type: ImportType = Form(...),
    file: UploadFile = File(...),
    context: AuthContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
    dispatch: Callable[[uuid.UUID], None] = Depends(get_import_dispatcher),
) -> ImportJobResponse:
    raw_bytes = await file.read()
    raw_content = raw_bytes.decode("utf-8-sig")
    job = await service.create_import_job(
        db,
        context.organization_id,
        context.user.id,
        import_type,
        file.filename or "upload.csv",
        raw_content,
    )
    dispatch(job.id)
    return import_job_to_response(job)


@router.get("/{job_id}", response_model=ImportJobResponse)
async def get_import(
    job_id: uuid.UUID,
    context: AuthContext = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> ImportJobResponse:
    job = await service.get_import_job(db, context.organization_id, job_id)
    return import_job_to_response(job)
