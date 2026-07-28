from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import re

from app.db.session import get_db
from app.models.prompt_template import PromptTemplate
from app.models.workflow import Workflow
from app.auth.dependencies import get_current_user
from app.services.ai_service import AIService

router = APIRouter(prefix="/prompt-templates", tags=["prompt-templates"], dependencies=[Depends(get_current_user)])


class PromptTemplateCreate(BaseModel):
    name: str
    purpose: Optional[str] = None
    description: Optional[str] = None
    prompt_content: str
    variables_json: Optional[str] = "[]"
    status: Optional[str] = "draft"


class PromptTemplateUpdate(BaseModel):
    name: Optional[str] = None
    purpose: Optional[str] = None
    description: Optional[str] = None
    prompt_content: Optional[str] = None
    variables_json: Optional[str] = None
    status: Optional[str] = None


class PromptTemplateTest(BaseModel):
    sample_inputs: dict


class PromptTemplateResponse(BaseModel):
    id: str
    name: str
    purpose: Optional[str] = None
    description: Optional[str] = None
    prompt_content: str
    variables_json: Optional[str] = "[]"
    status: str
    usage_count: int
    is_active: bool
    used_by_workflows: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[PromptTemplateResponse])
def list_prompt_templates(db: Session = Depends(get_db)):
    templates = db.query(PromptTemplate).filter(PromptTemplate.is_active == True).order_by(PromptTemplate.created_at.desc()).all()
    template_ids = [t.id for t in templates]
    usage_counts = _get_usage_counts(template_ids, db)
    return [_to_response(t, db, usage_counts) for t in templates]


@router.post("/", response_model=PromptTemplateResponse)
def create_prompt_template(
    payload: PromptTemplateCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    template = PromptTemplate(
        name=payload.name,
        purpose=payload.purpose,
        description=payload.description,
        prompt_content=payload.prompt_content,
        variables_json=payload.variables_json,
        status=payload.status or "draft",
        user_id=current_user.get("id")
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    usage_counts = _get_usage_counts([template.id], db)
    return _to_response(template, db, usage_counts)


@router.get("/{template_id}", response_model=PromptTemplateResponse)
def get_prompt_template(template_id: str, db: Session = Depends(get_db)):
    template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id, PromptTemplate.is_active == True).first()
    if not template:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    usage_counts = _get_usage_counts([template.id], db)
    return _to_response(template, db, usage_counts)


@router.put("/{template_id}", response_model=PromptTemplateResponse)
def update_prompt_template(template_id: str, payload: PromptTemplateUpdate, db: Session = Depends(get_db)):
    template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id, PromptTemplate.is_active == True).first()
    if not template:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(template, key, value)
    template.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(template)
    usage_counts = _get_usage_counts([template.id], db)
    return _to_response(template, db, usage_counts)


@router.delete("/{template_id}")
def delete_prompt_template(template_id: str, db: Session = Depends(get_db)):
    template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    template.is_active = False
    db.commit()
    return {"success": True, "message": "Prompt template deleted"}


@router.post("/{template_id}/test")
def test_prompt_template(template_id: str, payload: PromptTemplateTest, db: Session = Depends(get_db)):
    template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id, PromptTemplate.is_active == True).first()
    if not template:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    try:
        ai_service = AIService(db=db)
        rendered = ai_service.render_prompt(template.prompt_content, payload.sample_inputs)
        response = ai_service.generate_reply(rendered)
        return {"success": True, "rendered_prompt": rendered, "ai_response": response}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/{template_id}/validate")
def validate_prompt_template(template_id: str, db: Session = Depends(get_db)):
    template = db.query(PromptTemplate).filter(PromptTemplate.id == template_id, PromptTemplate.is_active == True).first()
    if not template:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    issues = []
    variables_in_prompt = set(re.findall(r'\{\{(\w+)\}\}', template.prompt_content))
    try:
        import json
        declared_vars = set(json.loads(template.variables_json or "[]"))
    except:
        declared_vars = set()
    undeclared = variables_in_prompt - declared_vars
    unused = declared_vars - variables_in_prompt
    if undeclared:
        issues.append(f"Variables in prompt but not declared: {', '.join(undeclared)}")
    if unused:
        issues.append(f"Declared variables not used in prompt: {', '.join(unused)}")
    used_by = db.query(Workflow).filter(
        Workflow.is_active == True,
        Workflow.actions_json.op("@>")(f'[{{"prompt_template_id": "{template_id}"}}]')
    ).count()
    if used_by == 0:
        issues.append("Not used by any active workflow")
    return {"valid": len(issues) == 0, "issues": issues, "variables_in_prompt": list(variables_in_prompt), "declared_variables": list(declared_vars)}


def _get_usage_counts(template_ids, db):
    """Batch compute usage counts for multiple templates in one query."""
    import json
    counts = {str(tid): 0 for tid in template_ids}
    workflows = db.query(Workflow).filter(Workflow.is_active == True).all()
    for wf in workflows:
        try:
            actions = wf.actions_json if isinstance(wf.actions_json, list) else json.loads(wf.actions_json or "[]")
            for action in actions:
                if action.get("type") == "generate_ai_reply":
                    tid = action.get("prompt_template_id")
                    if tid in counts:
                        counts[tid] += 1
        except Exception:
            continue
    return counts


def _to_response(t, db, usage_counts=None) -> PromptTemplateResponse:
    return PromptTemplateResponse(
        id=str(t.id),
        name=t.name,
        purpose=t.purpose,
        description=t.description,
        prompt_content=t.prompt_content,
        variables_json=t.variables_json,
        status=t.status,
        usage_count=t.usage_count,
        is_active=t.is_active,
        used_by_workflows=usage_counts.get(str(t.id), 0) if usage_counts else 0,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )
