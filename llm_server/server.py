import time
import asyncio
import json
import mysql.connector
from llms import LLM

class Server:
    def __init__(self, llm: LLM, safety_evaluator):
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
        self.connection = self.connect_to_db()
        self.delimiter = "~~~END~~~"

    def connect_to_db(self):
        conn = mysql.connector.connect(**self.db_config)
        if conn.is_connected():
            print("Connected to the database!")
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    chat_id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    chat_history JSON NOT NULL
                );
            """)
            conn.commit()
            cursor.close()
        return conn

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info('peername')
        print(f"Connected to {addr}")

        data = await reader.readline()
        message = data.decode().strip()
        user = ""
        if message.startswith("req:"):
            user = message[4:]
            cursor = self.connection.cursor()
            cursor.execute("SELECT chat_id FROM chat_sessions WHERE user_id = %s;", (user,))
            chat_ids = cursor.fetchall()
            chat_ids = [str(row[0]) for row in chat_ids]
            cursor.close()
            max_chat_id = max(chat_ids) if chat_ids else 0
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
                    cursor = self.connection.cursor()
                    cursor.execute("SELECT chat_history FROM chat_sessions WHERE chat_id = %s AND user_id = %s;", (chat_id, user))
                    result = cursor.fetchone()
                    cursor.close()
                    if result:
                        #print(result[0])
                        chat_history = result[0]
                        formatted_history = '\n'.join([f"{i['role']}: {i['content']}" for i in json.loads(chat_history)[1:]])
                        writer.write(f"load:{formatted_history}{self.delimiter}".encode())
                        self.llm.load_chat_context(json.loads(chat_history))
                        await writer.drain()
                        continue
            elif message.lower() == "exit":
                print("Closing the connection")
                cursor = self.connection.cursor()
                chat_context = json.dumps(self.llm.get_chat_context(), default=str)
                cursor.execute("""
                    INSERT INTO chat_sessions (user_id, chat_history)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE chat_history = %s;
                """, (user, chat_context, chat_context))
                self.connection.commit()
                cursor.close()
                writer.close()
                await writer.wait_closed()
                break
            else:
                print(f"Received {message} from {addr}")
                start = time.time()
                cursor = self.connection.cursor()
                cursor.execute("SELECT chat_history FROM chat_sessions WHERE user_id = %s AND chat_history LIKE %s;", (user, f"%{message}%"))
                similar_sessions = cursor.fetchall()
                cursor.close()
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
                writer.write(f"{llm_response}\nSafety of code: {safety}{self.delimiter}".encode())
                end = time.time()
                print(f"Response time: {end - start:.2f} seconds")
                await writer.drain()
        print(f"Connection with {addr} closed")

    async def run(self, host: str, port: int):
        server = await asyncio.start_server(self.handle_client, host, port)
        print(f"Serving on {host}:{port}...")
        async with server:
            await server.serve_forever()