from src.agent_scope.social_listening.ask import scope as ask_social_listening
from src.agent_scope.social_listening.setup import scope as social_listening_setup

ACTIONS = {
    "social-listening-setup": social_listening_setup,
    "ask-social-listening": ask_social_listening,
}
