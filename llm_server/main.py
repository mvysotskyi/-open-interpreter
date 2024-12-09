import asyncio

from dotenv import dotenv_values

from server import Server
from llms import OpenAILLM, SafetyEvaluator, QwenLLM, ResourcesEvalutor


if __name__ == '__main__':
    config = dotenv_values(".env")

    llm_openai = OpenAILLM(api_key=config["OPENAI_API_KEY"], model=config["OPENAI_MODEL"])
    #llm_qwen = QwenLLM()
    safety_evaluator = SafetyEvaluator(config["OPENAI_API_KEY"])
    resources_evaluator = ResourcesEvalutor(config["OPENAI_API_KEY"])
    server = Server(llm_openai, safety_evaluator, resources_evaluator)

    asyncio.run(server.run(host="localhost", port=5001))
