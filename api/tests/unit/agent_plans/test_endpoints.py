from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent_plans.schemas import (
    AgentPlanCreateRequest,
    AgentPlanDeleteResponse,
    AgentPlanResponse,
    AgentPlanUpdateRequest,
)
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService


@pytest.fixture
def db():
    return AsyncMock()


@pytest.fixture
def mock_record():
    now = datetime.now(UTC)
    return MagicMock(
        id="plan_123",
        user_id="user_123",
        slug="test-plan",
        question="What is this?",
        plan="Do this step by step",
        created_at=now,
        updated_at=now,
    )


class TestListPlansEndpoint:
    @pytest.mark.asyncio
    async def test_list_plans_returns_paginated_response(self):
        from src.agent_plans.endpoints import list_plans as endpoint_list_plans

        now = datetime.now(UTC)
        record = MagicMock(
            id="plan_123",
            user_id="user_123",
            slug="test-plan",
            question="What is this?",
            plan="Do this",
            created_at=now,
            updated_at=now,
        )

        with patch("src.agent_plans.service.agent_plan_service.list_plans") as mock_service:
            mock_paginated = PaginatedApiResponse(
                data=[record], pagination=PaginationService.build_pagination_meta(1, 1, 10)
            )
            mock_service.return_value = mock_paginated

            db = AsyncMock()
            paging = PaginationParams(page=1, page_size=10)

            result = await endpoint_list_plans(q=None, db=db, user_id="user_123", paging=paging)

            assert isinstance(result, PaginatedApiResponse)
            assert len(result.data) == 1

    @pytest.mark.asyncio
    async def test_list_plans_with_search_query(self):
        from src.agent_plans.endpoints import list_plans as endpoint_list_plans

        now = datetime.now(UTC)
        record = MagicMock(
            id="plan_123",
            user_id="user_123",
            slug="test-plan",
            question="What is this?",
            plan="Do this",
            created_at=now,
            updated_at=now,
        )

        with patch("src.agent_plans.service.agent_plan_service.list_plans") as mock_service:
            mock_paginated = PaginatedApiResponse(
                data=[record], pagination=PaginationService.build_pagination_meta(1, 1, 10)
            )
            mock_service.return_value = mock_paginated

            db = AsyncMock()
            paging = PaginationParams(page=1, page_size=10)

            result = await endpoint_list_plans(q="test", db=db, user_id="user_123", paging=paging)

            assert isinstance(result, PaginatedApiResponse)
            mock_service.assert_called_once()
            # Check that search parameter was passed
            call_kwargs = mock_service.call_args.kwargs
            assert call_kwargs.get("search") == "test"


class TestCreatePlanEndpoint:
    @pytest.mark.asyncio
    async def test_create_plan_returns_response(self):
        from src.agent_plans.endpoints import create_plan as endpoint_create_plan

        now = datetime.now(UTC)
        created_record = MagicMock(
            id="plan_new",
            user_id="user_123",
            slug="test-plan",
            question="What is this?",
            plan="Do this",
            created_at=now,
            updated_at=now,
        )

        with patch("src.agent_plans.service.agent_plan_service.create_plan") as mock_service:
            mock_service.return_value = created_record

            db = AsyncMock()
            body = AgentPlanCreateRequest(
                slug="test-plan", question="What is this?", plan="Do this"
            )

            result = await endpoint_create_plan(body=body, db=db, user_id="user_123")

            assert isinstance(result, AgentPlanResponse)
            assert result.slug == "test-plan"


class TestGetPlanBySlugEndpoint:
    @pytest.mark.asyncio
    async def test_get_plan_by_slug_returns_response(self):
        from src.agent_plans.endpoints import get_plan_by_slug as endpoint_get_by_slug

        now = datetime.now(UTC)
        record = MagicMock(
            id="plan_123",
            user_id="user_123",
            slug="test-plan",
            question="What is this?",
            plan="Do this",
            created_at=now,
            updated_at=now,
        )

        with patch("src.agent_plans.service.agent_plan_service.get_plan_by_slug") as mock_service:
            mock_service.return_value = record

            db = AsyncMock()

            result = await endpoint_get_by_slug(slug="test-plan", db=db, user_id="user_123")

            assert isinstance(result, AgentPlanResponse)
            assert result.slug == "test-plan"


class TestGetPlanEndpoint:
    @pytest.mark.asyncio
    async def test_get_plan_returns_response(self):
        from src.agent_plans.endpoints import get_plan as endpoint_get_plan

        now = datetime.now(UTC)
        record = MagicMock(
            id="plan_123",
            user_id="user_123",
            slug="test-plan",
            question="What is this?",
            plan="Do this",
            created_at=now,
            updated_at=now,
        )

        with patch("src.agent_plans.service.agent_plan_service.get_plan") as mock_service:
            mock_service.return_value = record

            db = AsyncMock()

            result = await endpoint_get_plan(plan_id="plan_123", db=db, user_id="user_123")

            assert isinstance(result, AgentPlanResponse)
            assert result.id == "plan_123"


class TestPatchPlanEndpoint:
    @pytest.mark.asyncio
    async def test_patch_plan_returns_updated_response(self):
        from src.agent_plans.endpoints import patch_plan as endpoint_patch_plan

        now = datetime.now(UTC)
        updated_record = MagicMock(
            id="plan_123",
            user_id="user_123",
            slug="new-slug",
            question="Updated question",
            plan="Do this",
            created_at=now,
            updated_at=now,
        )

        with patch("src.agent_plans.service.agent_plan_service.update_plan") as mock_service:
            mock_service.return_value = updated_record

            db = AsyncMock()
            body = AgentPlanUpdateRequest(slug="new-slug")

            result = await endpoint_patch_plan(
                plan_id="plan_123", body=body, db=db, user_id="user_123"
            )

            assert isinstance(result, AgentPlanResponse)
            assert result.slug == "new-slug"


class TestDeletePlanEndpoint:
    @pytest.mark.asyncio
    async def test_delete_plan_returns_delete_response(self):
        from src.agent_plans.endpoints import delete_plan as endpoint_delete_plan

        now = datetime.now(UTC)
        deleted_record = MagicMock(
            id="plan_123",
            user_id="user_123",
            slug="test-plan",
            question="What is this?",
            plan="Do this",
            created_at=now,
            updated_at=now,
        )

        with patch("src.agent_plans.service.agent_plan_service.delete_plan") as mock_service:
            mock_service.return_value = deleted_record

            db = AsyncMock()

            result = await endpoint_delete_plan(plan_id="plan_123", db=db, user_id="user_123")

            assert isinstance(result, AgentPlanDeleteResponse)
            assert result.id == "plan_123"
            assert result.deleted is True
