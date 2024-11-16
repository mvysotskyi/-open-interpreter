import asyncio

from dotenv import dotenv_values

from server import Server
from llms import OpenAILLM, SafetyEvaluator


if __name__ == '__main__':
    config = dotenv_values(".env")

    llm_openai = OpenAILLM(api_key=config["OPENAI_API_KEY"], model=config["OPENAI_MODEL"])
    safety_evaluator = SafetyEvaluator(config["OPENAI_API_KEY"])
    server = Server(llm_openai, safety_evaluator)

    asyncio.run(server.run(host="localhost", port=5001))
