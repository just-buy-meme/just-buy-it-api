from langgraph.graph import StateGraph, START

from app.agents.orchestrator.types import State
from app.agents.orchestrator.node import (
    supervisor_node,
    coordinator_node,
    planner_node,
    stock_info_node,
    account_info_node,
    trade_not_auto_node,
    market_monitoring_node,
)


def build_graph():
    """Build and return the agent workflow graph."""
    builder = StateGraph(State)
    builder.add_edge(START, "coordinator")
    builder.add_node("coordinator", coordinator_node)
    builder.add_node("planner", planner_node)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("stock_info_agent", stock_info_node)
    builder.add_node("account_info_agent", account_info_node)
    builder.add_node("trade_not_auto_agent", trade_not_auto_node)
    builder.add_node("market_monitoring_agent", market_monitoring_node)
    return builder.compile()


if __name__ == "__main__":
    graph = build_graph()
    graph.draw_mermaid_png(output_file_path="orchestrator.png")
