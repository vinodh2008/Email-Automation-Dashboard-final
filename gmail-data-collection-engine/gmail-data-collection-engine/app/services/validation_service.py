"""
ValidationService — Email validation before processing pipeline.
Phase 2B: Basic format, sender, spam, and required field checks.
"""
import logging
import re
from typing import Dict, Any, List
from sqlalchemy.orm import Session

logger = logging.getLogger("validation_service")

SPAM_KEYWORDS = ["unsubscribe", "free money", "click here", "act now", "limited time", "congratulations"]
SUSPICIOUS_DOMAINS = ["tempmail.com", "throwaway.email", "guerrillamail.com"]


class ValidationService:
    def __init__(self, db: Session):
        self.db = db

    def validate(self, email_id: str) -> Dict[str, Any]:
        """
        Validate an email. Returns score 0-100 and reasons.
        Score < 50 = reject, >= 50 = continue processing.
        """
        try:
            from app.models.email import Email
            email = self.db.query(Email).filter(Email.id == email_id).first()
            if not email:
                return {"score": 0, "status": "invalid", "reasons": ["Email not found"]}
            
            reasons = []
            score = 100
            
            if not email.subject and not email.body_text:
                score -= 30
                reasons.append("Missing subject and body")
            elif not email.subject:
                score -= 10
                reasons.append("Missing subject")
            
            sender = email.sender_email or ""
            if not sender or "@" not in sender:
                score -= 20
                reasons.append("Invalid sender address")
            
            sender_domain = sender.split("@")[-1].lower() if "@" in sender else ""
            if sender_domain in SUSPICIOUS_DOMAINS:
                score -= 25
                reasons.append(f"Suspicious domain: {sender_domain}")
            
            body = (email.body_text or "").lower() + " " + (email.subject or "").lower()
            spam_hits = [kw for kw in SPAM_KEYWORDS if kw in body]
            if spam_hits:
                score -= len(spam_hits) * 5
                reasons.append(f"Spam keywords detected: {', '.join(spam_hits)}")
            
            if sender.startswith("mailer-daemon") or sender.startswith("postmaster"):
                score -= 40
                reasons.append("Bounce message detected")
            
            score = max(0, min(100, score))
            status = "valid" if score >= 50 else "rejected"
            
            return {
                "score": score,
                "status": status,
                "reasons": reasons,
                "email_id": email_id,
            }
            
        except Exception as e:
            logger.error(f"[VALIDATION] Failed to validate email {email_id}: {e}")
            return {"score": 0, "status": "error", "reasons": [str(e)]}

    def get_rules(self) -> Dict[str, Any]:
        """Return current validation rules."""
        return {
            "spam_keywords": SPAM_KEYWORDS,
            "suspicious_domains": SUSPICIOUS_DOMAINS,
            "min_score": 50,
            "checks": [
                "required_fields",
                "sender_legitimacy",
                "domain_reputation",
                "spam_detection",
                "bounce_detection",
            ]
        }