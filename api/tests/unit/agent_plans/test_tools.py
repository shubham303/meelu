from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent_plans.schemas import (
    AgentPlanFindResponse,
    AgentPlanMatchResponse,
    AgentPlanPlanResponse,
    AgentPlanRecord,
)
from src.agent_plans.tools import find_plans, get_plan
from src.core.pagination import PaginatedApiResponse, PaginationService


@pytest.fixture
def mock_context():
    ctx = MagicMock()
    ctx.user_id = "user_123"
    return ctx


@pytest.fixture
def mock_record():
    now = datetime.now(UTC)
    return AgentPlanRecord(
        id="plan_123",
        user_id="user_123",
        slug="test-plan",
        question="What is this?",
        plan="Do this step by step",
        builtin=False,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def mock_match_records():
    now = datetime.now(UTC)
    return [
        AgentPlanRecord(
            id="plan_1",
            user_id="user_123",
            slug="test-plan-one",
            question="What is the first thing?",
            plan="Do step 1",
            builtin=False,
            created_at=now,
            updated_at=now,
        ),
        AgentPlanRecord(
            id="plan_2",
            user_id="user_123",
            slug="test-plan-two",
            question="What is the second thing?",
            plan="Do step 2",
            builtin=False,
            created_at=now,
            updated_at=now,
        ),
    ]


class TestFindPlans:
    @patch("src.agent_plans.tools.current")
    @patch("src.agent_plans.tools.unit_of_work")
    @patch("src.agent_plans.tools.agent_plan_service.list_plans")
    @pytest.mark.asyncio
    async def test_find_plans_success(
        self, mock_list_plans, mock_unit_of_work, mock_current, mock_context, mock_match_records
    ):
        mock_current.return_value = mock_context
        mock_db = AsyncMock()
        mock_unit_of_work.return_value.__aenter__.return_value = mock_db

        paginated = PaginatedApiResponse(
            data=mock_match_records, pagination=PaginationService.build_pagination_meta(0, 1, 10)
        )
        mock_list_plans.return_value = paginated

        result = await find_plans("test query")

        assert isinstance(result, AgentPlanFindResponse)
        assert len(result.matches) == 2
        assert result.n == 2
        assert all(isinstance(m, AgentPlanMatchResponse) for m in result.matches)
        assert result.matches[0].slug == "test-plan-one"
        assert result.matches[1].slug == "test-plan-two"

    @patch("src.agent_plans.tools.current")
    @patch("src.agent_plans.tools.unit_of_work")
    @patch("src.agent_plans.tools.agent_plan_service.list_plans")
    @pytest.mark.asyncio
    async def test_find_plans_empty(
        self, mock_list_plans, mock_unit_of_work, mock_current, mock_context
    ):
        mock_current.return_value = mock_context
        mock_db = AsyncMock()
        mock_unit_of_work.return_value.__aenter__.return_value = mock_db

        paginated = PaginatedApiResponse(
            data=[], pagination=PaginationService.build_pagination_meta(0, 1, 10)
        )
        mock_list_plans.return_value = paginated

        result = await find_plans("unknown query")

        assert isinstance(result, AgentPlanFindResponse)
        assert len(result.matches) == 0
        assert result.n == 0

    @patch("src.agent_plans.tools.current")
    @patch("src.agent_plans.tools.unit_of_work")
    @patch("src.agent_plans.tools.agent_plan_service.list_plans")
    @pytest.mark.asyncio
    async def test_find_plans_returns_match_responses(
        self, mock_list_plans, mock_unit_of_work, mock_current, mock_context, mock_match_records
    ):
        mock_current.return_value = mock_context
        mock_db = AsyncMock()
        mock_unit_of_work.return_value.__aenter__.return_value = mock_db

        paginated = PaginatedApiResponse(
            data=mock_match_records, pagination=PaginationService.build_pagination_meta(0, 1, 10)
        )
        mock_list_plans.return_value = paginated

        result = await find_plans("test query")

        for match in result.matches:
            assert hasattr(match, "slug")
            assert hasattr(match, "question")
            assert not hasattr(match, "plan")


class TestGetPlan:
    @patch("src.agent_plans.tools.current")
    @patch("src.agent_plans.tools.unit_of_work")
    @patch("src.agent_plans.tools.agent_plan_service.get_plan_by_slug")
    @pytest.mark.asyncio
    async def test_get_plan_success(
        self, mock_get_by_slug, mock_unit_of_work, mock_current, mock_context, mock_record
    ):
        mock_current.return_value = mock_context
        mock_db = AsyncMock()
        mock_unit_of_work.return_value.__aenter__.return_value = mock_db
        mock_get_by_slug.return_value = mock_record

        result = await get_plan("test-plan")

        assert isinstance(result, AgentPlanPlanResponse)
        assert result.slug == "test-plan"
        assert result.question == "What is this?"
        assert result.plan == "Do this step by step"

    @patch("src.agent_plans.tools.current")
    @patch("src.agent_plans.tools.unit_of_work")
    @patch("src.agent_plans.tools.agent_plan_service.get_plan_by_slug")
    @pytest.mark.asyncio
    async def test_get_plan_returns_plan_response(
        self, mock_get_by_slug, mock_unit_of_work, mock_current, mock_context, mock_record
    ):
        mock_current.return_value = mock_context
        mock_db = AsyncMock()
        mock_unit_of_work.return_value.__aenter__.return_value = mock_db
        mock_get_by_slug.return_value = mock_record

        result = await get_plan("test-plan")

        assert hasattr(result, "slug")
        assert hasattr(result, "question")
        assert hasattr(result, "plan")
        assert not hasattr(result, "id")
        assert not hasattr(result, "user_id")
        assert not hasattr(result, "created_at")
