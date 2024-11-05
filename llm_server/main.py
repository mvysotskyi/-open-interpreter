import asyncio

from dotenv import dotenv_values

from server import Server
from llms import OpenAILLM


if __name__ == '__main__':
    config = dotenv_values(".env")

    llm_openai = OpenAILLM(api_key=config["OPENAI_API_KEY"], model=config["OPENAI_MODEL"])
    server = Server(llm_openai)

    asyncio.run(server.run(host="localhost", port=5001))
