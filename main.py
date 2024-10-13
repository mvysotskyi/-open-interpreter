import asyncio
from openai import OpenAI
import os
class Server:
    def __init__(self):
        self.client = OpenAI(api_key="key")

async def handle_client(reader, writer):
    # Read the data sent from the client
    data = await reader.read(100)
    message = data.decode()

    # Log the received message
    print(f"Received input: {message}")

    # Send a response back to the client
    completion = openai.client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {"role":"user", "content":message}
        ]
    )
    response = f"Response: {completion.choices[0].message.content}"
    print(completion.choices[0].message.content)
    writer.write(response.encode())
    await writer.drain()

    print("Closing the connection")
    writer.close()
    await writer.wait_closed()

async def main():
    server = await asyncio.start_server(handle_client, 'localhost', 5000)
    print("Serving on port 5000...")

    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    openai = Server()
    asyncio.run(main())
