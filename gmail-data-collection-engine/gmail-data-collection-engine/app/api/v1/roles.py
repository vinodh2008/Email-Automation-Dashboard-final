from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, Field
from app.db.session import get_db
from app.models.user import UserRole, User
from app.auth.dependencies import get_current_user, require_permission
from app.utils.audit import create_audit_log


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    permissions: List[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    permissions: Optional[List[str]] = None


class RoleOut(BaseModel):
    id: UUID
    name: str
    permissions: List[str] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_orm_model(cls, obj):
        return cls(
            id=obj.id,
            name=obj.name,
            permissions=obj.permissions_json or [],
            created_at=str(obj.created_at) if obj.created_at else None,
            updated_at=str(getattr(obj, 'updated_at', None) or ''),
        )


router = APIRouter(prefix="/admin/roles", tags=["admin-roles"], dependencies=[Depends(get_current_user)])

def _get_role_or_404(db: Session, role_id: UUID):
    role = db.query(UserRole).filter(UserRole.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role

@router.get("/", response_model=list[RoleOut])
def list_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("view_roles")),
):
    roles = db.query(UserRole).offset(skip).limit(limit).all()
    return [RoleOut.from_orm_model(r) for r in roles]

@router.post("/", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreate,
    db: Session = Depends(get_db),
    current: dict = Depends(require_permission("create_roles")),
):
    if db.query(UserRole).filter(UserRole.name == payload.name).first():
        raise HTTPException(status_code=400, detail="Role name already exists")
    role = UserRole(name=payload.name, permissions_json=payload.permissions)
    db.add(role)
    db.commit()
    db.refresh(role)
    create_audit_log(
        db,
        actor_id=current["id"],
        action="create_role",
        target="UserRole",
        target_id=role.id,
        before=None,
        after=role,
    )
    return RoleOut.from_orm_model(role)

@router.put("/{role_id}", response_model=RoleOut)
def update_role(
    role_id: UUID,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    current: dict = Depends(require_permission("update_roles")),
    if_match: int = Query(None, alias="If-Match"),
):
    role = _get_role_or_404(db, role_id)
    # optimistic lock
    if if_match and getattr(role, "version", 1) != if_match:
        raise HTTPException(status_code=409, detail="Role has been modified by another admin")
    before = {k: getattr(role, k) for k in payload.dict(exclude_unset=True).keys()}
    for attr, value in payload.dict(exclude_unset=True).items():
        setattr(role, attr, value)
    # increment version if present
    if hasattr(role, "version"):
        role.version += 1
    db.commit()
    db.refresh(role)
    create_audit_log(
        db,
        actor_id=current["id"],
        action="update_role",
        target="UserRole",
        target_id=role.id,
        before=before,
        after={k: getattr(role, k) for k in before.keys()},
    )
    return RoleOut.from_orm_model(role)

@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: UUID,
    db: Session = Depends(get_db),
    current: dict = Depends(require_permission("delete_roles")),
):
    role = _get_role_or_404(db, role_id)
    user_count = db.query(User).filter(User.role_id == role.id).count()
    if user_count > 0:
        raise HTTPException(status_code=409, detail=f"Role is assigned to {user_count} user(s). Reassign them first.")
    db.delete(role)
    db.commit()
    create_audit_log(
        db,
        actor_id=current["id"],
        action="delete_role",
        target="UserRole",
        target_id=role.id,
        before=role,
        after=None,
    )
    return None

@router.post("/{role_id}/clone", response_model=RoleOut)
def clone_role(
    role_id: UUID,
    new_name: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current: dict = Depends(require_permission("create_roles")),
):
    role = _get_role_or_404(db, role_id)
    if db.query(UserRole).filter(UserRole.name == new_name).first():
        raise HTTPException(status_code=400, detail="Role name already exists")
    cloned = UserRole(name=new_name, permissions_json=role.permissions_json)
    db.add(cloned)
    db.commit()
    db.refresh(cloned)
    create_audit_log(
        db,
        actor_id=current["id"],
        action="clone_role",
        target="UserRole",
        target_id=cloned.id,
        before=None,
        after=cloned,
    )
    return RoleOut.from_orm_model(cloned)
