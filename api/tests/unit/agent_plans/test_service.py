from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent_plans.schemas import (
    AgentPlanCreateRequest,
    AgentPlanRecord,
    AgentPlanSyncResult,
    AgentPlanUpdateRequest,
)
from src.agent_plans.service import (
    create_plan,
    delete_plan,
    get_plan,
    get_plan_by_slug,
    list_plans,
    sync_builtins,
    update_plan,
)
from src.core.exceptions import ServiceError
from src.core.pagination import PaginatedApiResponse, PaginationParams


@pytest.fixture
def db():
    return AsyncMock()


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
def mock_builtin_record():
    now = datetime.now(UTC)
    return AgentPlanRecord(
        id="plan_builtin",
        user_id=None,
        slug="builtin-plan",
        question="Builtin question",
        plan="Builtin plan",
        builtin=True,
        created_at=now,
        updated_at=now,
    )


class TestSyncBuiltins:
    @patch("src.agent_plans.service.repo")
    @pytest.mark.asyncio
    async def test_sync_builtins_calls_upsert_and_prune(self, mock_repo, db):
        mock_repo.upsert_builtin = AsyncMock()
        mock_repo.prune_builtins = AsyncMock(return_value=0)
        db.commit = AsyncMock()

        result = await sync_builtins(db)

        assert isinstance(result, AgentPlanSyncResult)
        assert result.synced > 0
        assert result.pruned == 0
        assert mock_repo.upsert_builtin.called


class TestListPlans:
    @patch("src.agent_plans.service.repo")
    @pytest.mark.asyncio
    async def test_list_plans_without_search(self, mock_repo, db):
        now = datetime.now(UTC)
        record = AgentPlanRecord(
            id="plan_123",
            user_id="user_123",
            slug="test-plan",
            question="What is this?",
            plan="Do this",
            builtin=False,
            created_at=now,
            updated_at=now,
        )
        paginated = PaginatedApiResponse(data=[record], pagination=MagicMock())
        mock_repo.list_plans = AsyncMock(return_value=paginated)

        paging = PaginationParams(page=1, page_size=10)
        result = await list_plans(db, "user_123", paging, search=None)

        assert result == paginated
        mock_repo.list_plans.assert_called_once()

    @patch("src.agent_plans.service.repo")
    @pytest.mark.asyncio
    async def test_list_plans_with_search(self, mock_repo, db):
        now = datetime.now(UTC)
        record = AgentPlanRecord(
            id="plan_123",
            user_id="user_123",
            slug="test-plan",
            question="What is this?",
            plan="Do this",
            builtin=False,
            created_at=now,
            updated_at=now,
        )
        paginated = PaginatedApiResponse(data=[record], pagination=MagicMock())
        mock_repo.search_plans = AsyncMock(return_value=paginated)

        paging = PaginationParams(page=1, page_size=10)
        result = await list_plans(db, "user_123", paging, search="test")

        assert result == paginated
        mock_repo.search_plans.assert_called_once()


class TestGetPlan:
    @patch("src.agent_plans.service.repo")
    @pytest.mark.asyncio
    async def test_get_plan_found(self, mock_repo, db, mock_record):
        mock_repo.get_plan = AsyncMock(return_value=mock_record)

        result = await get_plan(db, "user_123", "plan_123")

        assert result == mock_record
        mock_repo.get_plan.assert_called_once_with(db, "user_123", "plan_123")

    @patch("src.agent_plans.service.repo")
    @pytest.mark.asyncio
    async def test_get_plan_not_found(self, mock_repo, db):
        mock_repo.get_plan = AsyncMock(return_value=None)

        with pytest.raises(ServiceError) as exc_info:
            await get_plan(db, "user_123", "plan_123")

        assert exc_info.value.status == 404
        assert exc_info.value.detail == "Not found"


class TestGetPlanBySlug:
    @patch("src.agent_plans.service.repo")
    @pytest.mark.asyncio
    async def test_get_plan_by_slug_found(self, mock_repo, db, mock_record):
        mock_repo.get_plan_by_slug = AsyncMock(return_value=mock_record)

        result = await get_plan_by_slug(db, "user_123", "test-plan")

        assert result == mock_record
        mock_repo.get_plan_by_slug.assert_called_once()

    @patch("src.agent_plans.service.repo")
    @pytest.mark.asyncio
    async def test_get_plan_by_slug_not_found(self, mock_repo, db):
        mock_repo.get_plan_by_slug = AsyncMock(return_value=None)

        with pytest.raises(ServiceError) as exc_info:
            await get_plan_by_slug(db, "user_123", "unknown-plan")

        assert exc_info.value.status == 404
        assert "unknown-plan" in exc_info.value.detail


class TestCreatePlan:
    @patch("src.agent_plans.service.repo")
    @pytest.mark.asyncio
    async def test_create_plan_success(self, mock_repo, db, mock_record):
        mock_repo.get_plan_by_slug = AsyncMock(return_value=None)
        mock_repo.create_plan = AsyncMock(return_value=mock_record)

        body = AgentPlanCreateRequest(slug="test-plan", question="What is this?", plan="Do this")
        result = await create_plan(db, "user_123", body)

        assert result == mock_record
        mock_repo.create_plan.assert_called_once()

    @patch("src.agent_plans.service.repo")
    @pytest.mark.asyncio
    async def test_create_plan_slug_already_exists(self, mock_repo, db, mock_record):
        mock_repo.get_plan_by_slug = AsyncMock(return_value=mock_record)

        body = AgentPlanCreateRequest(slug="test-plan", question="What is this?", plan="Do this")

        with pytest.raises(ServiceError) as exc_info:
            await create_plan(db, "user_123", body)

        assert exc_info.value.status == 409


class TestUpdatePlan:
    @patch("src.agent_plans.service.repo")
    @patch("src.agent_plans.service.get_plan")
    @pytest.mark.asyncio
    async def test_update_plan_success(self, mock_get, mock_repo, db, mock_record):
        updated_record = AgentPlanRecord(
            id="plan_123",
            user_id="user_123",
            slug="new-slug",
            question="Updated question",
            plan="Do this",
            builtin=False,
            created_at=mock_record.created_at,
            updated_at=datetime.now(UTC),
        )
        mock_get.return_value = mock_record
        mock_repo.get_plan_by_slug = AsyncMock(return_value=None)
        mock_repo.update_plan = AsyncMock(return_value=updated_record)

        body = AgentPlanUpdateRequest(slug="new-slug")
        result = await update_plan(db, "user_123", "plan_123", body)

        assert result == updated_record
        mock_repo.update_plan.assert_called_once()

    @patch("src.agent_plans.service.get_plan")
    @pytest.mark.asyncio
    async def test_update_plan_builtin_not_allowed(self, mock_get, db):
        builtin_record = AgentPlanRecord(
            id="plan_builtin",
            user_id=None,
            slug="builtin-plan",
            question="Builtin",
            plan="Builtin plan",
            builtin=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_get.return_value = builtin_record

        body = AgentPlanUpdateRequest(slug="new-slug")

        with pytest.raises(ServiceError) as exc_info:
            await update_plan(db, "user_123", "plan_builtin", body)

        assert exc_info.value.status == 403

    @patch("src.agent_plans.service.get_plan")
    @pytest.mark.asyncio
    async def test_update_plan_nothing_to_update(self, mock_get, db, mock_record):
        mock_get.return_value = mock_record

        body = AgentPlanUpdateRequest()

        with pytest.raises(ServiceError) as exc_info:
            await update_plan(db, "user_123", "plan_123", body)

        assert exc_info.value.status == 400

    @patch("src.agent_plans.service.repo")
    @patch("src.agent_plans.service.get_plan")
    @pytest.mark.asyncio
    async def test_update_plan_slug_collision(self, mock_get, mock_repo, db, mock_record):
        other_record = AgentPlanRecord(
            id="plan_456",
            user_id="user_123",
            slug="existing-slug",
            question="Another plan",
            plan="Another plan",
            builtin=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_get.return_value = mock_record
        mock_repo.get_plan_by_slug = AsyncMock(return_value=other_record)

        body = AgentPlanUpdateRequest(slug="existing-slug")

        with pytest.raises(ServiceError) as exc_info:
            await update_plan(db, "user_123", "plan_123", body)

        assert exc_info.value.status == 409


class TestDeletePlan:
    @patch("src.agent_plans.service.repo")
    @patch("src.agent_plans.service.get_plan")
    @pytest.mark.asyncio
    async def test_delete_plan_success(self, mock_get, mock_repo, db, mock_record):
        mock_get.return_value = mock_record
        mock_repo.delete_plan = AsyncMock()

        result = await delete_plan(db, "user_123", "plan_123")

        assert result == mock_record
        mock_repo.delete_plan.assert_called_once_with(db, "plan_123")

    @patch("src.agent_plans.service.get_plan")
    @pytest.mark.asyncio
    async def test_delete_builtin_not_allowed(self, mock_get, db):
        builtin_record = AgentPlanRecord(
            id="plan_builtin",
            user_id=None,
            slug="builtin-plan",
            question="Builtin",
            plan="Builtin plan",
            builtin=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_get.return_value = builtin_record

        with pytest.raises(ServiceError) as exc_info:
            await delete_plan(db, "user_123", "plan_builtin")

        assert exc_info.value.status == 403
