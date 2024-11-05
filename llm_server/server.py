import time
import asyncio

from llms import LLM


class Server:
    def __init__(self, llm: LLM):
        self.llm = llm

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info('peername')
        print(f"Connected to {addr}")

        while True:
            data = await reader.readline()
            message = data.decode().strip()
            
            if message.lower() == "exit":
                print("Closing the connection")

                await writer.drain()
                writer.close()
                await writer.wait_closed()
                break

            print(f"Received {message} from {addr}")

            start = time.time()

            llm_response = self.llm.get_response(message)
            print(f"Sending {llm_response} to {addr}")

            writer.write(f"{llm_response}\n".encode())
            end = time.time()

            print(f"Response time: {end - start:.2f} seconds")

            await writer.drain()

        print(f"Connection with {addr} closed")

    async def run(self, host: str, port: int):
        server = await asyncio.start_server(self.handle_client, host, port)
        print(f"Serving on {host}:{port}...")

        async with server:
            await server.serve_forever()
