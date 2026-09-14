from datetime import UTC

import pytest
from pydantic import ValidationError

from src.agent_plans.schemas import (
    AgentPlanCreateRequest,
    AgentPlanDeleteResponse,
    AgentPlanListItemResponse,
    AgentPlanMatchResponse,
    AgentPlanPlanResponse,
    AgentPlanResponse,
    AgentPlanUpdateRequest,
)


class TestAgentPlanCreateRequest:
    def test_valid_create_request(self):
        plan = AgentPlanCreateRequest(
            slug="test-plan", question="What is this?", plan="Do this step by step"
        )
        assert plan.slug == "test-plan"
        assert plan.question == "What is this?"
        assert plan.plan == "Do this step by step"

    def test_slug_must_be_lowercase_with_hyphens(self):
        with pytest.raises(ValidationError):
            AgentPlanCreateRequest(slug="Invalid_Plan", question="What is this?", plan="Do this")

    def test_slug_cannot_start_or_end_with_hyphen(self):
        with pytest.raises(ValidationError):
            AgentPlanCreateRequest(slug="-invalid", question="What is this?", plan="Do this")

    def test_slug_length_enforced(self):
        with pytest.raises(ValidationError):
            AgentPlanCreateRequest(slug="a" * 65, question="What is this?", plan="Do this")

    def test_slug_max_length_allowed(self):
        slug = "valid-slug-" + "a" * (64 - len("valid-slug-"))
        plan = AgentPlanCreateRequest(slug=slug, question="What is this?", plan="Do this")
        assert plan.slug == slug

    def test_question_is_required(self):
        with pytest.raises(ValidationError):
            AgentPlanCreateRequest(slug="test-plan", question="", plan="Do this")

    def test_question_length_enforced(self):
        with pytest.raises(ValidationError):
            AgentPlanCreateRequest(slug="test-plan", question="x" * 301, plan="Do this")

    def test_question_max_length_allowed(self):
        question = "x" * 300
        plan = AgentPlanCreateRequest(slug="test-plan", question=question, plan="Do this")
        assert plan.question == question

    def test_plan_is_required(self):
        with pytest.raises(ValidationError):
            AgentPlanCreateRequest(slug="test-plan", question="What is this?", plan="")

    def test_plan_length_enforced(self):
        with pytest.raises(ValidationError):
            AgentPlanCreateRequest(slug="test-plan", question="What is this?", plan="x" * 8001)

    def test_plan_max_length_allowed(self):
        plan_text = "x" * 8000
        plan = AgentPlanCreateRequest(slug="test-plan", question="What is this?", plan=plan_text)
        assert plan.plan == plan_text

    def test_whitespace_is_stripped(self):
        plan = AgentPlanCreateRequest(
            slug="  test-plan  ", question="  What is this?  ", plan="  Do this  "
        )
        assert plan.slug == "test-plan"
        assert plan.question == "What is this?"
        assert plan.plan == "Do this"

    def test_slug_converted_to_lowercase(self):
        plan = AgentPlanCreateRequest(slug="Test-Plan", question="What is this?", plan="Do this")
        assert plan.slug == "test-plan"


class TestAgentPlanUpdateRequest:
    def test_all_fields_optional(self):
        plan = AgentPlanUpdateRequest()
        assert plan.slug is None
        assert plan.question is None
        assert plan.plan is None

    def test_partial_update(self):
        plan = AgentPlanUpdateRequest(slug="new-slug")
        assert plan.slug == "new-slug"
        assert plan.question is None
        assert plan.plan is None

    def test_changes_returns_non_none_fields(self):
        plan = AgentPlanUpdateRequest(slug="new-slug", question="New question")
        changes = plan.changes()
        assert changes == {"slug": "new-slug", "question": "New question"}

    def test_changes_excludes_none_fields(self):
        plan = AgentPlanUpdateRequest(slug="new-slug")
        changes = plan.changes()
        assert "question" not in changes
        assert "plan" not in changes

    def test_slug_validation_applied(self):
        with pytest.raises(ValidationError):
            AgentPlanUpdateRequest(slug="Invalid_Plan")

    def test_question_validation_applied(self):
        with pytest.raises(ValidationError):
            AgentPlanUpdateRequest(question="x" * 301)

    def test_plan_validation_applied(self):
        with pytest.raises(ValidationError):
            AgentPlanUpdateRequest(plan="x" * 8001)

    def test_none_slug_allowed(self):
        plan = AgentPlanUpdateRequest(slug=None)
        assert plan.slug is None

    def test_whitespace_stripped(self):
        plan = AgentPlanUpdateRequest(slug="  new-slug  ", question="  Updated question  ")
        assert plan.slug == "new-slug"
        assert plan.question == "Updated question"


class TestResponseModels:
    def test_agent_plan_response_model(self):
        from datetime import datetime

        now = datetime.now(UTC)

        response = AgentPlanResponse(
            id="plan_123",
            slug="test-plan",
            question="What is this?",
            plan="Do this",
            builtin=False,
            created_at=now,
            updated_at=now,
        )
        assert response.id == "plan_123"
        assert response.slug == "test-plan"
        assert response.builtin is False

    def test_agent_plan_list_item_response(self):
        from datetime import datetime

        now = datetime.now(UTC)

        response = AgentPlanListItemResponse(
            id="plan_123",
            slug="test-plan",
            question="What is this?",
            builtin=False,
            created_at=now,
            updated_at=now,
        )
        assert response.id == "plan_123"
        assert response.slug == "test-plan"

    def test_agent_plan_delete_response(self):
        response = AgentPlanDeleteResponse(id="plan_123")
        assert response.id == "plan_123"
        assert response.deleted is True

    def test_agent_plan_delete_response_deleted_default(self):
        response = AgentPlanDeleteResponse(id="plan_123")
        assert response.deleted is True

    def test_agent_plan_match_response(self):
        response = AgentPlanMatchResponse(slug="test-plan", question="What is this?")
        assert response.slug == "test-plan"
        assert response.question == "What is this?"

    def test_agent_plan_plan_response(self):
        response = AgentPlanPlanResponse(
            slug="test-plan", question="What is this?", plan="Do this step by step"
        )
        assert response.slug == "test-plan"
        assert response.question == "What is this?"
        assert response.plan == "Do this step by step"
