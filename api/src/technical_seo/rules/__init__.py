from src.sites.schemas import SiteRecord
from src.technical_seo.rules.ai_crawlers import ai_permission_rules
from src.technical_seo.rules.content import CONTENT_PAGE_RULES
from src.technical_seo.rules.host_variants import host_variant_rules
from src.technical_seo.rules.links import LINK_PAGE_RULES
from src.technical_seo.rules.page import PAGE_RULES as CORE_PAGE_RULES
from src.technical_seo.rules.render import RENDER_PAGE_RULES, RenderCounts, render_site_rules
from src.technical_seo.rules.types import PageRule, SiteRule
from src.technical_seo.rules.well_known import well_known_rules

PAGE_RULES: list[PageRule] = [
    *CORE_PAGE_RULES,
    *CONTENT_PAGE_RULES,
    *LINK_PAGE_RULES,
    *RENDER_PAGE_RULES,
]


def site_rules(site: SiteRecord, renders: RenderCounts) -> list[SiteRule]:
    return [
        *well_known_rules(site),
        *ai_permission_rules(site),
        *host_variant_rules(site),
        *render_site_rules(renders),
    ]
