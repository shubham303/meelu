from src.agent_scope.analytics.analytics_ask import scope as analytics_ask
from src.agent_scope.analytics.analyze_data import scope as analyze_data
from src.agent_scope.analytics.analyze_report import scope as analyze_report

ACTIONS = {
    "analytics-ask": analytics_ask,
    "analyze-data": analyze_data,
    "analyze-report": analyze_report,
}
