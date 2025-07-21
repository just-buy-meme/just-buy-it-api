import logging
import json
from copy import deepcopy
from typing import Literal
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command
from langgraph.graph import END
from app.core.deps import llm, thinking_llm, embeddings, kis
from app.agents.account_info.account import create_account_info_agent
from app.agents.trade_executor.trade_executor import create_trade_not_auto_agent
from app.agents.trade_executor.market_monitor import create_market_monitor_agent
from app.agents.stock_info.stock_info_agent import create_stock_info_agent

from app.agents.orchestrator.template import apply_prompt_template
from app.agents.orchestrator.types import State, Router

account_info_agent = create_account_info_agent()
stock_info_agent = create_stock_info_agent()
trade_not_auto_agent = create_trade_not_auto_agent()
market_monitoring_agent = create_market_monitor_agent()

logger = logging.getLogger(__name__)
TEAM_MEMBERS = ["account_info_agent", "stock_info_agent", "trade_not_auto_agent", "market_monitoring_agent"]

RESPONSE_FORMAT = "Response from {}:\n\n<response>\n{}\n</response>\n\n*Please execute the next step.*"


def account_info_node(state: State) -> Command[Literal["supervisor"]]:
    logger.info("Account Info agent starting task")
    result = account_info_agent.invoke(state)
    logger.info("Account Info agent completed task")
    logger.debug(f"Account Info agent response: {result['messages'][-1].content}")
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=RESPONSE_FORMAT.format("account_info_agent", result["messages"][-1].content),
                    name="account_info_agent",
                )
            ]
        },
        goto="supervisor",
    )


def stock_info_node(state: State) -> Command[Literal["supervisor"]]:
    logger.info("Stock Info agent starting task")
    result = stock_info_agent.invoke(state)
    logger.info("Stock Info agent completed task")
    logger.debug(f"Stock Info agent response: {result['messages'][-1].content}")
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=RESPONSE_FORMAT.format("stock_info_agent", result["messages"][-1].content),
                    name="stock_info_agent",
                )
            ]
        },
        goto="supervisor",
    )


def trade_not_auto_node(state: State) -> Command[Literal["supervisor"]]:
    logger.info("Manual Trade agent starting task")
    result = trade_not_auto_agent.invoke(state)
    logger.info("Manual Trade agent completed task")
    logger.debug(f"Manual Trade agent response: {result['messages'][-1].content}")
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=RESPONSE_FORMAT.format("trade_not_auto_agent", result["messages"][-1].content),
                    name="trade_not_auto_agent",
                )
            ]
        },
        goto="supervisor",
    )

def market_monitoring_node(state: State) -> Command[Literal["supervisor"]]:
    logger.info("Market Monitoring agent starting task")
    result = market_monitoring_agent.invoke(state)
    logger.info("Market Monitoring agent completed task")
    logger.debug(f"Market Monitoring agent response: {result['messages'][-1].content}")
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=RESPONSE_FORMAT.format("market_monitoring_agent", result["messages"][-1].content),
                    name="market_monitoring_agent",
                )
            ]
        },
        goto="supervisor",
    )
def supervisor_node(state: State) -> Command[Literal[*TEAM_MEMBERS, "__end__"]]:
    """Supervisor node that decides which agent should act next."""
    logger.info("Supervisor evaluating next action")
    messages = apply_prompt_template("supervisor", state)
    response = (
        llm
        .with_structured_output(Router)
        .invoke(messages)
    )
    goto = response["next"]
    logger.debug(f"Current state messages: {state['messages']}")
    logger.debug(f"Supervisor response: {response}")

    updates = {"next": goto}

    if goto == "FINISH":
        goto = "__end__"
        logger.info("Workflow completed")

        # 마지막 HumanMessage를 찾아서 AIMessage로 변환
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                updates["messages"] = [
                    AIMessage(content=msg.content, name=msg.name)
                ]
                logger.debug(f"Adding AIMessage: {msg.content}")
                break

    else:
        logger.info(f"Supervisor delegating to: {goto}")

    return Command(goto=goto, update=updates)


def planner_node(state: State) -> Command[Literal["supervisor", "__end__"]]:
    """Planner node that generate the full plan."""
    logger.info("Planner generating full plan")
    messages = apply_prompt_template("planner", state)
    # whether to enable deep thinking mode

    stream = thinking_llm.stream(messages)
    full_response = ""
    for chunk in stream:
        full_response += chunk.content
    logger.debug(f"Current state messages: {state['messages']}")
    logger.debug(f"Planner response: {full_response}")

    if full_response.startswith("```json"):
        full_response = full_response.removeprefix("```json")

    if full_response.endswith("```"):
        full_response = full_response.removesuffix("```")

    goto = "supervisor"
    try:
        json.loads(full_response)
    except json.JSONDecodeError:
        logger.warning("Planner response is not a valid JSON")
        goto = "__end__"

    return Command(
        update={
            "messages": [HumanMessage(content=full_response, name="planner")],
            "full_plan": full_response,
        },
        goto=goto,
    )


def coordinator_node(state: State) -> Command[Literal["planner", "__end__"]]:
    """Coordinator node that communicate with customers."""
    logger.info("Coordinator talking.")
    messages = apply_prompt_template("coordinator", state)
    response = llm.invoke(messages)
    logger.debug(f"Current state messages: {state['messages']}")
    logger.debug(f"reporter response: {response}")

    goto = "__end__"
    if "handoff_to_planner" in response.content:
        goto = "planner"

    return Command(
        goto=goto,
    )
