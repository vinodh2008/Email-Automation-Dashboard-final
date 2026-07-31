from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.services.prompt_builder_service import PromptBuilderService
from app.core.responses import success_response

router = APIRouter(prefix="/prompt-builder", tags=["prompt-builder"], dependencies=[Depends(get_current_user)])


class BuildRequest(BaseModel):
    prompt_content: str
    variable_values: dict = {}
    provider_type: Optional[str] = None
    model: Optional[str] = None


class DetectVariablesRequest(BaseModel):
    prompt_content: str


class EstimateCostRequest(BaseModel):
    text: str
    provider_type: Optional[str] = None
    model: Optional[str] = None


@router.post("/build")
def build_prompt(payload: BuildRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = PromptBuilderService(db)
    result = service.build(
        prompt_content=payload.prompt_content,
        variable_values=payload.variable_values,
        provider_type=payload.provider_type,
        model=payload.model,
    )
    return success_response(data=result)


@router.post("/detect-variables")
def detect_variables(payload: DetectVariablesRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = PromptBuilderService(db)
    variables = service.detect_variables(payload.prompt_content)
    return success_response(data={'variables': variables})


@router.post("/estimate-cost")
def estimate_cost(payload: EstimateCostRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = PromptBuilderService(db)
    result = service.estimate_cost(payload.text, payload.provider_type, payload.model)
    return success_response(data=result)
