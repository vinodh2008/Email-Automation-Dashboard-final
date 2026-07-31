"""
DecisionService — Auto-approval vs escalation logic.
Phase 2B: Rule-based decision engine with configurable thresholds.
"""
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

logger = logging.getLogger("decision_service")

RISK_LEVELS = {"low": 0, "medium": 1, "high": 2}


class DecisionService:
    def __init__(self, db: Session):
        self.db = db

    def decide(self, email_id: str, ai_output: Dict[str, Any], category_id: str) -> Dict[str, Any]:
        """
        Decide whether to auto-approve, escalate, or reject.
        Returns: {"action": "auto_approve"|"escalate"|"reject", "rule_id": ..., "confidence": ...}
        """
        try:
            rules = self.get_rules(category_id)
            
            confidence = ai_output.get("confidence", 0.0)
            risk_level = ai_output.get("risk_level", "medium")
            email_value = ai_output.get("email_value", 0)
            sender_email = ai_output.get("sender_email", "")
            
            for rule in rules:
                if not rule["is_enabled"]:
                    continue
                
                if confidence < rule["min_confidence"]:
                    continue
                if RISK_LEVELS.get(risk_level, 1) > RISK_LEVELS.get(rule["max_risk_level"], 1):
                    continue
                if rule["max_email_value"] and email_value > rule["max_email_value"]:
                    continue
                if rule["sender_whitelist"] and sender_email not in rule["sender_whitelist"]:
                    continue
                
                logger.info(f"[DECISION] Rule '{rule['name']}' matched for email {email_id}: action={rule['action']}")
                return {
                    "action": rule["action"],
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "confidence": confidence,
                }
            
            logger.info(f"[DECISION] No rule matched for email {email_id}. Defaulting to escalate.")
            return {
                "action": "escalate",
                "rule_id": None,
                "rule_name": "default",
                "confidence": confidence,
            }
            
        except Exception as e:
            logger.error(f"[DECISION] Failed to decide for email {email_id}: {e}")
            return {"action": "escalate", "rule_id": None, "confidence": 0, "error": str(e)}

    def get_rules(self, category_id: str) -> List[Dict[str, Any]]:
        """Get decision rules for a category, ordered by priority."""
        try:
            from app.models.decision_rule import DecisionRule
            rules = self.db.query(DecisionRule).filter(
                DecisionRule.business_category_id == category_id
            ).order_by(DecisionRule.priority.desc()).all()
            
            return [{
                "id": str(r.id),
                "name": r.name,
                "description": r.description,
                "is_enabled": r.is_enabled,
                "priority": r.priority,
                "min_confidence": r.min_confidence,
                "max_risk_level": r.max_risk_level,
                "max_email_value": r.max_email_value,
                "sender_whitelist": r.sender_whitelist or [],
                "category_codes": r.category_codes or [],
                "action": r.action,
                "approval_chain": r.approval_chain or [],
            } for r in rules]
        except Exception as e:
            logger.error(f"[DECISION] Failed to get rules: {e}")
            return []

    def create_rule(self, category_id: str, rule_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a decision rule."""
        try:
            from app.models.decision_rule import DecisionRule
            import uuid
            
            rule = DecisionRule(
                business_category_id=uuid.UUID(category_id),
                name=rule_data["name"],
                description=rule_data.get("description"),
                is_enabled=rule_data.get("is_enabled", True),
                priority=rule_data.get("priority", 0),
                min_confidence=rule_data.get("min_confidence", 0.9),
                max_risk_level=rule_data.get("max_risk_level", "low"),
                max_email_value=rule_data.get("max_email_value"),
                sender_whitelist=rule_data.get("sender_whitelist", []),
                category_codes=rule_data.get("category_codes", []),
                action=rule_data.get("action", "escalate"),
                approval_chain=rule_data.get("approval_chain", []),
            )
            self.db.add(rule)
            self.db.commit()
            return {"id": str(rule.id), "status": "created"}
        except Exception as e:
            self.db.rollback()
            logger.error(f"[DECISION] Failed to create rule: {e}")
            return None

    def update_rule(self, rule_id: str, rule_data: Dict[str, Any]) -> bool:
        """Update a decision rule."""
        try:
            from app.models.decision_rule import DecisionRule
            rule = self.db.query(DecisionRule).filter(DecisionRule.id == rule_id).first()
            if not rule:
                return False
            for key, val in rule_data.items():
                if hasattr(rule, key) and val is not None:
                    setattr(rule, key, val)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"[DECISION] Failed to update rule {rule_id}: {e}")
            return False

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a decision rule."""
        try:
            from app.models.decision_rule import DecisionRule
            rule = self.db.query(DecisionRule).filter(DecisionRule.id == rule_id).first()
            if not rule:
                return False
            self.db.delete(rule)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"[DECISION] Failed to delete rule {rule_id}: {e}")
            return False