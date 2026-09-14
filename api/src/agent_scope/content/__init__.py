from src.agent_scope.content.ask_content import scope as ask_content
from src.agent_scope.content.content_channel_rules import scope as content_channel_rules
from src.agent_scope.content.content_draft import scope as content_draft
from src.agent_scope.content.content_piece import scope as content_piece

ACTIONS = {
    "content-draft": content_draft,
    "content-piece": content_piece,
    "ask-content": ask_content,
    "content-channel-rules": content_channel_rules,
}
