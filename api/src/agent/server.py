from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

INSTRUCTIONS = """\
Meelu agent server: direct SQL over the user's data plus deterministic analytics.

Workflow:
1. The tables you can query, with their columns, arrive in your task prompt.
   Anything not listed there is discoverable with run_sql over
   information_schema.columns.
2. Before designing SQL for a non-trivial question, call find_plans — the plan
   library holds vetted step-by-step plans for common questions. If a question
   matches, get_plan and adapt it instead of inventing the approach.
3. Read anything with run_sql. Canonical tables are read-only and already
   filtered to this user; your workspace schema is fully writable — materialize
   filtered or joined tables there (CREATE TABLE ... AS SELECT ...) before
   running analytics on them.
4. Analytics tools take a table name and return {method, summary, trust,
   declined, values, metadata}. Trust the chosen method. When `declined` is
   true the data cannot support the question — report the reason, never
   substitute a number. Always convey the trust level and caveats.
5. Saving results the user should keep goes through the explicit write tools,
   never through workspace tables.
"""

mcp = FastMCP(
    "meelu-agent",
    instructions=INSTRUCTIONS,
    stateless_http=True,
    streamable_http_path="/",
)


ToolFn = Callable[..., Any]

READ_TOOLS: set[ToolFn] = set()
WRITE_TOOLS: set[ToolFn] = set()
TOOL_DESKS: dict[ToolFn, str] = {}


def tool(*, writes: bool = False, desk: str | None = None) -> Callable[[ToolFn], ToolFn]:
    def register(fn: ToolFn) -> ToolFn:
        meta = {"meelu/writes": writes, **({"meelu/desk": desk} if desk else {})}
        mcp.tool(meta=meta)(fn)
        (WRITE_TOOLS if writes else READ_TOOLS).add(fn)
        if desk is not None:
            TOOL_DESKS[fn] = desk
        return fn

    return register
