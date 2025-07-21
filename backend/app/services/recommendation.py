import logging
import uuid

from app.agents.stock_recommender.stock_recom import create_stock_recommender_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Default level is INFO
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

def enable_debug_logging():
    """Enable debug level logging for more detailed execution information."""
    logging.getLogger("src").setLevel(logging.DEBUG)


logger = logging.getLogger(__name__)

recommend_graph = create_stock_recommender_agent()

async def run_stock_recommender_workflow(user_input_messages: list,
    debug: bool = False,
):
    """Run the agent workflow with the given user input.

    Args:
        user_input_messages: The user request messages
        debug: If True, enables debug level logging

    Returns:
        The final state after the workflow completes
    """
    if not user_input_messages:
        raise ValueError("Input could not be empty")

    if debug:
        enable_debug_logging()

    logger.info(f"Starting workflow with user input: {user_input_messages}")

    workflow_id = str(uuid.uuid4())
    agent_name = "stock_recommender_agent"
    agent_id = f"{workflow_id}_{agent_name}_1"

    # 워크플로우 시작 이벤트
    yield {
        "event": "start_of_workflow",
        "data": {"workflow_id": workflow_id, "input": user_input_messages},
    }

    # 에이전트 시작 이벤트
    yield {
        "event": "start_of_agent",
        "data": {"agent_name": agent_name, "agent_id": agent_id},
    }

    # LLM 시작 이벤트
    yield {
        "event": "start_of_llm",
        "data": {"agent_name": agent_name},
    }
    yield {
        "event": "message",
        "data": {
            "message_id": str(uuid.uuid4()),
            "delta": {"content": "추천할 주식을 찾고 있습니다. 잠시만 기다려주세요.\n\n"},
        },
    }
    # LangGraph 실행
    state = await recommend_graph.ainvoke({"content": user_input_messages[0]["content"]})

    # LLM 응답 message 이벤트
    yield {
        "event": "message",
        "data": {
            "message_id": str(uuid.uuid4()),
            "delta": {"content": state["content"]},
        },
    }

    # LLM 종료 이벤트
    yield {
        "event": "end_of_llm",
        "data": {"agent_name": agent_name},
    }

    # 에이전트 종료 이벤트
    yield {
        "event": "end_of_agent",
        "data": {"agent_name": agent_name, "agent_id": agent_id},
    }

    # 워크플로우 종료 이벤트
    yield {
        "event": "end_of_workflow",
        "data": {
            "workflow_id": workflow_id,
            "messages": user_input_messages + [{"role": "assistant", "content": state["content"]}],
        },
    }