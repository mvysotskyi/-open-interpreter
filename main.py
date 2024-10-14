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

    # end a response back to the client

    completion = openai.client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {"role":"user", "content":f"Write only shell code without comments to answer this: {message}"}
        ]
    )
    gg = '\n'.join(completion.choices[0].message.content.split('\n')[1:-1])
    response = 8*'m\n' + f"{gg}\n"
    #print(completion.choices[0].message.content)
    #response = 8*'m\n' +"mkdir build\n"
    chunk_size = 16 # 1KB per chunk
    for i in range(0, len(response), chunk_size):
        print(response[i:i+chunk_size])
        writer.write(response[i:i+chunk_size].encode())
        await writer.drain()

    #await writer.drain()

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
