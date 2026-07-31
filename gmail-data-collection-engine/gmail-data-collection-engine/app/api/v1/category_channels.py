from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import uuid

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.core.responses import success_response

router = APIRouter(prefix="/category-channels", tags=["category-channels"], dependencies=[Depends(get_current_user)])


class ChannelConfigCreate(BaseModel):
    business_category_id: str
    channel: str
    is_enabled: Optional[bool] = False
    workflow_id: Optional[str] = None
    prompt_template_id: Optional[str] = None
    channel_config: Optional[dict] = {}


class ChannelConfigUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    workflow_id: Optional[str] = None
    prompt_template_id: Optional[str] = None
    channel_config: Optional[dict] = None


@router.get("/")
def list_channel_configs(category_id: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        from app.models.category_channel_config import CategoryChannelConfig
        query = db.query(CategoryChannelConfig)
        if category_id:
            query = query.filter(CategoryChannelConfig.business_category_id == uuid.UUID(category_id))
        configs = query.all()
        return success_response(data=[{
            "id": str(c.id),
            "business_category_id": str(c.business_category_id),
            "channel": c.channel,
            "is_enabled": c.is_enabled,
            "workflow_id": str(c.workflow_id) if c.workflow_id else None,
            "prompt_template_id": str(c.prompt_template_id) if c.prompt_template_id else None,
            "channel_config": c.channel_config,
        } for c in configs])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/")
def create_channel_config(config_data: ChannelConfigCreate, db: Session = Depends(get_db)):
    try:
        from app.models.category_channel_config import CategoryChannelConfig
        config = CategoryChannelConfig(
            business_category_id=uuid.UUID(config_data.business_category_id),
            channel=config_data.channel,
            is_enabled=config_data.is_enabled,
            workflow_id=uuid.UUID(config_data.workflow_id) if config_data.workflow_id else None,
            prompt_template_id=uuid.UUID(config_data.prompt_template_id) if config_data.prompt_template_id else None,
            channel_config=config_data.channel_config,
        )
        db.add(config)
        db.commit()
        return success_response(data={"id": str(config.id), "status": "created"})
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{config_id}")
def update_channel_config(config_id: str, config_data: ChannelConfigUpdate, db: Session = Depends(get_db)):
    try:
        from app.models.category_channel_config import CategoryChannelConfig
        config = db.query(CategoryChannelConfig).filter(CategoryChannelConfig.id == uuid.UUID(config_id)).first()
        if not config:
            raise HTTPException(status_code=404, detail="Channel config not found")
        for key, val in config_data.model_dump(exclude_unset=True).items():
            if val is not None:
                if key in ("workflow_id", "prompt_template_id") and val:
                    val = uuid.UUID(val)
                setattr(config, key, val)
        db.commit()
        return success_response(data={"status": "updated"})
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{config_id}")
def delete_channel_config(config_id: str, db: Session = Depends(get_db)):
    try:
        from app.models.category_channel_config import CategoryChannelConfig
        config = db.query(CategoryChannelConfig).filter(CategoryChannelConfig.id == uuid.UUID(config_id)).first()
        if not config:
            raise HTTPException(status_code=404, detail="Channel config not found")
        db.delete(config)
        db.commit()
        return success_response(data={"status": "deleted"})
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
