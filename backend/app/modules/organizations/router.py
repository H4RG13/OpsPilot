from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import AuthContext, get_current_context
from app.modules.organizations.models import Organization
from app.modules.organizations.schemas import OrganizationResponse
from app.shared.exceptions import NotFoundError

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/current", response_model=OrganizationResponse)
async def get_current_organization(
    context: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    organization = await db.get(Organization, context.organization_id)
    if organization is None:
        raise NotFoundError("Organization was not found.", code="ORGANIZATION_NOT_FOUND")
    return OrganizationResponse.model_validate(organization)
