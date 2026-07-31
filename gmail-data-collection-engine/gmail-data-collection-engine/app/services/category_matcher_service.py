"""
CategoryMatcherService — Rule-based email classification into business categories.
Phase 2B: Assigns each email to the best-matching business category.
"""
import logging
import re
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

logger = logging.getLogger("category_matcher_service")


class CategoryMatcherService:
    def __init__(self, db: Session):
        self.db = db

    def classify(self, email_id: str) -> Optional[Dict[str, Any]]:
        """
        Classify an email into a business category.
        Returns dict with category_id, confidence, matching_method, matching_details.
        """
        try:
            from app.models.email import Email
            from app.models.business_category import BusinessCategory
            
            email = self.db.query(Email).filter(Email.id == email_id).first()
            if not email:
                logger.warning(f"[CATEGORY_MATCHER] Email {email_id} not found")
                return None
            
            categories = self.db.query(BusinessCategory).filter(
                BusinessCategory.is_active == True,
                BusinessCategory.status == "active"
            ).order_by(BusinessCategory.priority.desc()).all()
            
            if not categories:
                logger.info("[CATEGORY_MATCHER] No active categories found")
                return None
            
            best_match = None
            best_confidence = 0.0
            
            for category in categories:
                confidence, method, details = self._evaluate_category(email, category)
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = {
                        "category_id": str(category.id),
                        "category_code": category.code,
                        "category_name": category.name,
                        "confidence": confidence,
                        "matching_method": method,
                        "matching_details": details,
                    }
            
            if not best_match or best_confidence < 0.3:
                default_cat = self.db.query(BusinessCategory).filter(
                    BusinessCategory.is_default == True,
                    BusinessCategory.is_active == True
                ).first()
                if default_cat:
                    best_match = {
                        "category_id": str(default_cat.id),
                        "category_code": default_cat.code,
                        "category_name": default_cat.name,
                        "confidence": 0.1,
                        "matching_method": "default",
                        "matching_details": {"reason": "No specific category matched; assigned default"},
                    }
            
            if best_match:
                self._record_classification(email_id, best_match)
            
            return best_match
            
        except Exception as e:
            logger.error(f"[CATEGORY_MATCHER] Failed to classify email {email_id}: {e}")
            return None

    def _evaluate_category(self, email, category) -> tuple:
        """Evaluate an email against a category. Returns (confidence, method, details)."""
        scores = []
        
        subject_score, subject_matches = self._match_subject(email.subject or "", category.code)
        if subject_score > 0:
            scores.append(("keyword", subject_score, {"matched_keywords": subject_matches}))
        
        sender_score, sender_matches = self._match_sender(email.sender_email or "", category.code)
        if sender_score > 0:
            scores.append(("sender_domain", sender_score, {"matched_domains": sender_matches}))
        
        body = (email.body_text or "") + " " + (email.snippet or "")
        body_score, body_matches = self._match_body(body, category.code)
        if body_score > 0:
            scores.append(("body_content", body_score, {"matched_patterns": body_matches}))
        
        if not scores:
            return 0.0, "none", {}
        
        weights = {"keyword": 0.5, "sender_domain": 0.3, "body_content": 0.2}
        total_score = 0.0
        total_weight = 0.0
        all_details = {}
        best_method = "keyword"
        
        for method, score, details in scores:
            w = weights.get(method, 0.1)
            total_score += score * w
            total_weight += w
            all_details[method] = details
            if score > total_score:
                best_method = method
        
        confidence = total_score / total_weight if total_weight > 0 else 0.0
        confidence = min(confidence, 1.0)
        
        return confidence, best_method, all_details

    def _match_subject(self, subject: str, category_code: str) -> tuple:
        """Match subject line against category keywords."""
        subject_lower = subject.lower()
        keywords = self._get_category_keywords(category_code)
        
        matched = [kw for kw in keywords if kw in subject_lower]
        if matched:
            score = min(len(matched) / 2.0, 1.0)
            return score, matched
        return 0.0, []

    def _match_sender(self, sender_email: str, category_code: str) -> tuple:
        """Match sender email against category patterns."""
        sender_lower = sender_email.lower()
        patterns = self._get_sender_patterns(category_code)
        
        matched = [p for p in patterns if p in sender_lower]
        if matched:
            return 0.8, matched
        return 0.0, []

    def _match_body(self, body: str, category_code: str) -> tuple:
        """Match body content against category patterns."""
        body_lower = body.lower()
        keywords = self._get_category_keywords(category_code)
        
        matched = [kw for kw in keywords if kw in body_lower]
        if matched:
            score = min(len(matched) / 3.0, 1.0)
            return score, matched
        return 0.0, []

    def _get_category_keywords(self, category_code: str) -> List[str]:
        """Get keywords for a category. In Phase 2B, these are hardcoded defaults."""
        keyword_map = {
            "REFUND": ["refund", "money back", "return", "reimburse", "credit back"],
            "TECH_SUPPORT": ["technical", "bug", "error", "not working", "issue", "problem", "help"],
            "BILLING": ["invoice", "bill", "payment", "charge", "subscription", "pricing"],
            "GENERAL": ["inquiry", "question", "information", "help", "support"],
            "SALES": ["purchase", "buy", "order", "pricing", "demo", "trial"],
        }
        return keyword_map.get(category_code, ["support", "help", "inquiry"])

    def _get_sender_patterns(self, category_code: str) -> List[str]:
        """Get sender domain patterns for a category."""
        pattern_map = {
            "REFUND": ["refund", "returns"],
            "TECH_SUPPORT": ["support", "tech", "engineering"],
            "BILLING": ["billing", "finance", "invoice"],
            "SALES": ["sales", "marketing"],
        }
        return pattern_map.get(category_code, [])

    def _record_classification(self, email_id: str, match_result: Dict[str, Any]):
        """Save classification result to email_classifications table."""
        try:
            from app.models.email_classification import EmailClassification
            import uuid
            
            classification = EmailClassification(
                email_id=uuid.UUID(email_id),
                business_category_id=uuid.UUID(match_result["category_id"]),
                confidence=match_result["confidence"],
                matching_method=match_result["matching_method"],
                matching_details=match_result["matching_details"],
            )
            self.db.add(classification)
            self.db.flush()
        except Exception as e:
            logger.error(f"[CATEGORY_MATCHER] Failed to record classification: {e}")

    def get_classification(self, email_id: str) -> Optional[Dict[str, Any]]:
        """Get existing classification for an email."""
        try:
            from app.models.email_classification import EmailClassification
            classification = self.db.query(EmailClassification).filter(
                EmailClassification.email_id == email_id
            ).order_by(EmailClassification.classified_at.desc()).first()
            
            if not classification:
                return None
            
            return {
                "id": str(classification.id),
                "email_id": str(classification.email_id),
                "business_category_id": str(classification.business_category_id) if classification.business_category_id else None,
                "confidence": classification.confidence,
                "matching_method": classification.matching_method,
                "matching_details": classification.matching_details,
                "classified_at": classification.classified_at.isoformat() if classification.classified_at else None,
            }
        except Exception as e:
            logger.error(f"[CATEGORY_MATCHER] Failed to get classification: {e}")
            return None