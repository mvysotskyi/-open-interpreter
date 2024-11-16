import psycopg2
import json

host = "127.0.0.1"
port = "3306"
dbname = "os"
user = "root"
password = "12345678"

import mysql.connector

try:
    conn = mysql.connector.connect(
        host=host,
        port=port,
        database=dbname,
        user=user,
        password=password
    )
    print("Connected to the database!")
    cur = conn.cursor()
    chat_history = []

    # cur.execute("""CREATE TABLE IF NOT EXISTS chat_sessions (
    #         chat_id INT AUTO_INCREMENT PRIMARY KEY,
    #         chat_history JSON NOT NULL
    #     );
    # """)

    cur.execute("INSERT INTO chat_sessions (chat_history) VALUES (%s);", (json.dumps(chat_history),))
    chat_id = cur.lastrowid
    print(f"New chat session started with chat_id: {chat_id}")

    while True:
        user_input = input()

        if user_input.lower() == 'exit':
            break

        response = f"Response to: {user_input}"

        # Add the prompt and response to the chat history
        chat_history.append({
            "prompt": user_input,
            "response": response
        })

        cur.execute("""
            UPDATE chat_sessions
            SET chat_history = %s
            WHERE chat_id = %s;
        """, (json.dumps(chat_history), chat_id))

        conn.commit()  # Commit the transaction

        print(f"Prompt: {user_input}")
        print(f"Response: {response}")

        # Optionally, fetch and display the chat history
        cur.execute("SELECT chat_history FROM chat_sessions WHERE chat_id = %s;", (chat_id,))
        result = cur.fetchone()
        #print("\nCurrent Chat History:")
        #for entry in result[0]:
        #    print(f"Prompt: {entry['prompt']}, Response: {entry['response']}")
    cur.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")