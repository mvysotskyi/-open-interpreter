import time
import asyncio
import json
import mysql.connector
from llms import LLM, ResourcesEvalutor

class Server:
    def __init__(self, llm: LLM, safety_evaluator, resource_evaluator: ResourcesEvalutor):
        host = "127.0.0.1"
        port = "3306"
        dbname = "os"
        user = "root"
        password = "12345678"
        self.llm = llm
        self.db_config = {
            'host': host,
            'port': port,
            'database': dbname,
            'user': user,
            'password': password
        }
        self.safety_evaluator = safety_evaluator
        self.resource_evaluator = resource_evaluator
        self.db_lock = asyncio.Lock()
        self.delimiter = "~~~END~~~"

    def connect_db_safe(self):
        return mysql.connector.connect(**self.db_config)

    def query_db_sync(self, connection, query, params=None):
        cursor = connection.cursor()
        cursor.execute(query, params or ())
        result = cursor.fetchall()
        cursor.close()
        return result

    def execute_db_sync(self, connection, query, params=None):
        cursor = connection.cursor()
        cursor.execute(query, params or ())
        connection.commit()
        cursor.close()

    async def query_db(self, query, params=None):
        async with self.db_lock:
            connection = self.connect_db_safe()
            try:
                result = await asyncio.to_thread(self.query_db_sync, connection, query, params)
            finally:
                connection.close()
        return result

    async def execute_db(self, query, params=None):
        async with self.db_lock:
            connection = self.connect_db_safe()
            try:
                await asyncio.to_thread(self.execute_db_sync, connection, query, params)
            finally:
                connection.close()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info('peername')
        print(f"Connected to {addr}")

        data = await reader.readline()
        message = data.decode().strip()
        user = ""
        max_chat_id = 0
        if message.startswith("req:"):
            user = message[4:]
            create_table_query = """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    chat_id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    chat_history JSON NOT NULL
                );
            """
            await self.execute_db(create_table_query)
            select_query = "SELECT chat_id FROM chat_sessions WHERE user_id = %s;"
            params = (user,)
            result = await self.query_db(select_query, params)
            chat_ids = [str(row[0]) for row in result]
            if chat_ids:
                max_chat_id = max(int(cid) for cid in chat_ids)
            writer.write((",".join(chat_ids) + self.delimiter).encode())
            await writer.drain()

        while True:
            data = await reader.readline()
            if not data:
                break
            message = data.decode().strip()

            if message.startswith("ch:"):
                chat_id = message[3:]
                if chat_id == '0':
                    chat_id = max_chat_id
                    writer.write(("load:New chat" + self.delimiter).encode())
                    await writer.drain()
                else:
                    select_query = "SELECT chat_history FROM chat_sessions WHERE chat_id = %s AND user_id = %s;"
                    params = (chat_id, user)
                    result = await self.query_db(select_query, params)
                    if result:
                        chat_history = result[0][0]
                        formatted_history = '\n'.join([f"{i['role']}: {i['content']}" for i in json.loads(chat_history)[1:]])
                        writer.write(f"load:{formatted_history}{self.delimiter}".encode())
                        self.llm.load_chat_context(json.loads(chat_history))
                        await writer.drain()
                        continue
            elif message.lower() == "exit":
                print("Closing the connection")
                if chat_id == max_chat_id:
                    chat_context = json.dumps(self.llm.get_chat_context(), default=str)
                    insert_query = """
                        INSERT INTO chat_sessions (user_id, chat_history)
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE chat_history = %s;
                    """
                    params = (user, chat_context, chat_context)
                    await self.execute_db(insert_query, params)
                    writer.close()
                    await writer.wait_closed()
                    break
                else:
                    chat_context = json.dumps(self.llm.get_chat_context(), default=str)
                    upd_query = """
                    UPDATE chat_sessions
                    SET chat_history = %s
                    WHERE chat_id = %s AND user_id = %s;
                    """
                    params = (chat_context, chat_id, user)
                    await self.execute_db(upd_query, params)
                    writer.close()
                    await writer.wait_closed()
                    break
            elif message.lower() == "aexit":
                print("Closing the connection")
                writer.close()
                await writer.wait_closed()
                break
            else:
                print(f"Received {message} from {addr}")
                start = time.time()
                search_query = "SELECT chat_history FROM chat_sessions WHERE user_id = %s AND chat_history LIKE %s;"
                params = (user, f"%{message}%")
                similar_sessions = await self.query_db(search_query, params)
                if similar_sessions:
                    session = json.loads(similar_sessions[0][0])
                    llm_response = ""
                    for it, ans in enumerate(session):
                        if ans['role'] == 'user' and ans['content'].lower() == message.lower():
                            llm_response = session[it + 1]['content']
                            break
                else:
                    llm_response = self.llm.get_response(message)
                print(f"Sending {llm_response} to {addr}")
                safety = self.safety_evaluator.evaluate(str(message))
                resouces = self.resource_evaluator.evaluate(str(message))
                writer.write(f"{llm_response}\nSafety of code: {safety}\nResources needed: {resouces}{self.delimiter}".encode())
                end = time.time()
                print(f"Response time: {end - start:.2f} seconds")
                await writer.drain()
        print(f"Connection with {addr} closed")

    async def run(self, host: str, port: int):
        server = await asyncio.start_server(self.handle_client, host, port)
        print(f"Serving on {host}:{port}...")
        async with server:
            await server.serve_forever()
