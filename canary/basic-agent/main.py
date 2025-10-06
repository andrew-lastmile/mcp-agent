import asyncio
import os
import time

from mcp_agent.app import MCPApp
from mcp_agent.config import (
    Settings,
    LoggerSettings,
    MCPSettings,
    MCPServerSettings,
    OpenAISettings,
    AnthropicSettings,
)
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm import RequestParams
from mcp_agent.workflows.llm.llm_selector import ModelPreferences
from mcp_agent.workflows.llm.augmented_llm_openai import OpenAIAugmentedLLM
from mcp_agent.tracing.token_counter import TokenSummary

# settings = Settings(
#     execution_engine="asyncio",
#     logger=LoggerSettings(type="file", level="debug"),
#     mcp=MCPSettings(
#         servers={
#             "fetch": MCPServerSettings(
#                 command="uvx",
#                 args=["mcp-server-fetch"],
#             ),
#             "filesystem": MCPServerSettings(
#                 command="npx",
#                 args=["-y", "@modelcontextprotocol/server-filesystem"],
#             ),
#         }
#     ),
#     openai=OpenAISettings(
#         api_key="sk-my-openai-api-key",
#         default_model="gpt-4o-mini",
#     ),
#     anthropic=AnthropicSettings(
#         api_key="sk-my-anthropic-api-key",
#     ),
# )

# Settings can either be specified programmatically,
# or loaded from mcp_agent.config.yaml/mcp_agent.secrets.yaml
app = MCPApp(name="mcp_basic_agent")  # settings=settings)


@app.tool()
async def example_usage() -> str:
    """
    An example function/tool that uses an agent with access to the fetch and filesystem
    mcp servers. The agent will read the contents of mcp_agent.config.yaml, print the
    first 2 paragraphs of the mcp homepage, and summarize the paragraphs into a tweet.
    The example uses both OpenAI, Anthropic, and simulates a multi-turn conversation.
    """
    async with app.run() as agent_app:
        logger = agent_app.logger
        context = agent_app.context
        result = ""

        logger.info("Current config:", data=context.config.model_dump())

        # Add the current directory to the filesystem server's args
        context.config.mcp.servers["filesystem"].args.extend([os.getcwd()])

        finder_agent = Agent(
            name="finder",
            instruction="""You are an agent with access to the filesystem, 
            as well as the ability to fetch URLs. Your job is to identify 
            the closest match to a user's request, make the appropriate tool calls, 
            and return the URI and CONTENTS of the closest match.""",
            server_names=["fetch", "filesystem"],
        )

        async with finder_agent:
            logger.info("finder: Connected to server, calling list_tools...")
            tools_list = await finder_agent.list_tools()
            logger.info("Tools available:", data=tools_list.model_dump())

            llm = await finder_agent.attach_llm(OpenAIAugmentedLLM)
            result += await llm.generate_str(
                message="Print the contents of mcp_agent.config.yaml verbatim",
            )
            logger.info(f"mcp_agent.config.yaml contents: {result}")

    return result

if __name__ == "__main__":
    start = time.time()
    asyncio.run(example_usage())
    end = time.time()
    t = end - start

    print(f"Total run time: {t:.2f}s")