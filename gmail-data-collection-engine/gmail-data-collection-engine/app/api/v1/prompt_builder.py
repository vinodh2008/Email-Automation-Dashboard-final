from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.services.prompt_builder_service import PromptBuilderService
from app.core.responses import success_response

router = APIRouter(prefix="/prompt-builder", tags=["prompt-builder"], dependencies=[Depends(get_current_user)])


class BuildRequest(BaseModel):
    prompt_content: str
    variable_values: dict = {}


class DetectVariablesRequest(BaseModel):
    prompt_content: str


@router.post("/build")
def build_prompt(payload: BuildRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = PromptBuilderService(db)
    result = service.build(
        prompt_content=payload.prompt_content,
        variable_values=payload.variable_values,
    )
    return success_response(data=result)


@router.post("/detect-variables")
def detect_variables(payload: DetectVariablesRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = PromptBuilderService(db)
    variables = service.detect_variables(payload.prompt_content)
    return success_response(data={'variables': variables})
