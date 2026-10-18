from dataclasses import dataclass, field

from src.core.schemas import EntityModel


class PostEmbeddingInput(EntityModel):
    id: str
    title: str | None = None
    text: str | None = None


@dataclass
class CollectedPosts:
    vendor_ids: list[str] = field(default_factory=list)
    database_by_keyword: dict[str, list[str]] = field(default_factory=dict)
    failed_keywords: list[str] = field(default_factory=list)
    vendor_keywords: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def database_ids(self) -> list[str]:
        return [i for ids in self.database_by_keyword.values() for i in ids]

    @property
    def post_ids(self) -> list[str]:
        return list(dict.fromkeys([*self.vendor_ids, *self.database_ids]))
