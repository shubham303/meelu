from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent_plans.repository import (
    create_plan,
    delete_plan,
    get_plan,
    get_plan_by_slug,
    list_plans,
    prune_builtins,
    search_plans,
    update_plan,
    upsert_builtin,
)
from src.core.pagination import PaginatedApiResponse, PaginationParams


@pytest.fixture
def db():
    return AsyncMock()


@pytest.fixture
def mock_plan_row():
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


class TestGetPlan:
    @pytest.mark.asyncio
    async def test_get_plan_found(self, db, mock_plan_row):
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_plan_row

        db.execute.return_value = mock_result

        result = await get_plan(db, "user_123", "plan_123")

        assert result is not None
        assert result.id == "plan_123"
        db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_plan_not_found(self, db):
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None

        db.execute.return_value = mock_result

        result = await get_plan(db, "user_123", "plan_123")

        assert result is None


class TestGetPlanBySlug:
    @pytest.mark.asyncio
    async def test_get_plan_by_slug_found(self, db, mock_plan_row):
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_plan_row

        db.execute.return_value = mock_result

        result = await get_plan_by_slug(db, "user_123", "test-plan")

        assert result is not None
        assert result.slug == "test-plan"
        db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_plan_by_slug_prefers_user_plan_over_builtin(self, db):
        now = datetime.now(UTC)
        user_plan = MagicMock(
            id="user_plan",
            user_id="user_123",
            slug="test-plan",
            question="User version",
            plan="User plan",
            created_at=now,
            updated_at=now,
        )

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = user_plan

        db.execute.return_value = mock_result

        result = await get_plan_by_slug(db, "user_123", "test-plan")

        assert result.user_id == "user_123"

    @pytest.mark.asyncio
    async def test_get_plan_by_slug_returns_builtin_if_no_user_plan(self, db):
        now = datetime.now(UTC)
        builtin_plan = MagicMock(
            id="builtin_plan",
            user_id=None,
            slug="test-plan",
            question="Builtin version",
            plan="Builtin plan",
            created_at=now,
            updated_at=now,
        )

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = builtin_plan

        db.execute.return_value = mock_result

        result = await get_plan_by_slug(db, "user_123", "test-plan")

        assert result.user_id is None


class TestListPlans:
    @pytest.mark.asyncio
    async def test_list_plans_returns_paginated_response(self, db, mock_plan_row):
        paging = PaginationParams(page=1, page_size=10)

        with patch("src.agent_plans.repository.PaginationService") as mock_service:
            mock_paginated = PaginatedApiResponse(data=[], pagination=MagicMock())
            mock_service.paginate_query = AsyncMock(return_value=mock_paginated)

            result = await list_plans(db, "user_123", paging)

            assert isinstance(result, PaginatedApiResponse)
            mock_service.paginate_query.assert_called_once()


class TestSearchPlans:
    @pytest.mark.asyncio
    async def test_search_plans_returns_paginated_response(self, db):
        paging = PaginationParams(page=1, page_size=10)
        tsquery = MagicMock()

        with patch("src.agent_plans.repository.PaginationService") as mock_service:
            mock_paginated = PaginatedApiResponse(data=[], pagination=MagicMock())
            mock_service.paginate_query = AsyncMock(return_value=mock_paginated)

            result = await search_plans(db, "user_123", tsquery, paging)

            assert isinstance(result, PaginatedApiResponse)
            mock_service.paginate_query.assert_called_once()


class TestCreatePlan:
    @pytest.mark.asyncio
    async def test_create_plan_adds_and_flushes(self, db):
        with patch("src.agent_plans.repository.uid") as mock_uid:
            mock_uid.return_value = "plan_new"
            db.add = MagicMock()
            db.flush = AsyncMock()

            now = datetime.now(UTC)
            result = await create_plan(db, "user_123", "test-plan", "What is this?", "Do this")

            assert result.id == "plan_new"
            assert result.slug == "test-plan"
            assert result.user_id == "user_123"
            db.add.assert_called_once()
            db.flush.assert_called_once()


class TestUpdatePlan:
    @pytest.mark.asyncio
    async def test_update_plan_updates_and_returns(self, db):
        now = datetime.now(UTC)
        updated_row = MagicMock(
            id="plan_123",
            user_id="user_123",
            slug="new-slug",
            question="Updated",
            plan="Updated plan",
            created_at=now,
            updated_at=now,
        )

        mock_result = AsyncMock()
        mock_result.scalar_one.return_value = updated_row
        db.execute.return_value = mock_result

        result = await update_plan(db, "plan_123", {"slug": "new-slug"})

        assert result.slug == "new-slug"
        db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_plan_includes_updated_at(self, db):
        now = datetime.now(UTC)
        updated_row = MagicMock(
            id="plan_123",
            user_id="user_123",
            slug="test-plan",
            question="Updated",
            plan="Updated plan",
            created_at=now,
            updated_at=now,
        )

        mock_result = AsyncMock()
        mock_result.scalar_one.return_value = updated_row
        db.execute.return_value = mock_result

        result = await update_plan(db, "plan_123", {"question": "New question"})

        assert result is not None
        db.execute.assert_called_once()


class TestDeletePlan:
    @pytest.mark.asyncio
    async def test_delete_plan_executes_and_flushes(self, db):
        db.execute = AsyncMock()
        db.flush = AsyncMock()

        await delete_plan(db, "plan_123")

        db.execute.assert_called_once()
        db.flush.assert_called_once()


class TestUpsertBuiltin:
    @pytest.mark.asyncio
    async def test_upsert_builtin_inserts_or_updates(self, db):
        db.execute = AsyncMock()
        db.flush = AsyncMock()

        with patch("src.agent_plans.repository.uid") as mock_uid:
            mock_uid.return_value = "plan_builtin"

            await upsert_builtin(db, "test-plan", "What is this?", "Do this")

            db.execute.assert_called_once()
            db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_builtin_with_none_user_id(self, db):
        db.execute = AsyncMock()
        db.flush = AsyncMock()

        with patch("src.agent_plans.repository.uid") as mock_uid:
            mock_uid.return_value = "plan_builtin"

            await upsert_builtin(db, "builtin-slug", "Builtin question", "Builtin plan")

            db.execute.assert_called_once()


class TestPruneBuiltins:
    @pytest.mark.asyncio
    async def test_prune_builtins_removes_unlisted(self, db):
        mock_result = AsyncMock()
        mock_result.rowcount = 3
        db.execute.return_value = mock_result
        db.flush = AsyncMock()

        result = await prune_builtins(db, ["kept-plan-1", "kept-plan-2"])

        assert result == 3
        db.execute.assert_called_once()
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_prune_builtins_keeps_listed_plans(self, db):
        mock_result = AsyncMock()
        mock_result.rowcount = 0
        db.execute.return_value = mock_result
        db.flush = AsyncMock()

        result = await prune_builtins(db, ["all-plans"])

        assert result == 0
