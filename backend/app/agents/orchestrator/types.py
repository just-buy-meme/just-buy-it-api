from typing import Literal
from typing_extensions import TypedDict
from langgraph.graph import MessagesState


TEAM_MEMBERS = ["account_info_agent", "stock_info_agent", "trade_not_auto_agent", "trade_auto_agent"]
# Define routing options
OPTIONS = TEAM_MEMBERS + ["FINISH"]


class Router(TypedDict):
    """Worker to route to next. If no workers needed, route to FINISH."""

    next: Literal[*OPTIONS]


class State(MessagesState):
    """State for the agent system, extends MessagesState with next field."""

    # Constants
    TEAM_MEMBERS: list[str]

    # Runtime Variables
    next: str
    full_plan: str
