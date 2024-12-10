from flask import Flask, request, jsonify
from flask import send_from_directory, redirect, url_for
import asyncio
import os

app = Flask(__name__)

@app.route('/')
def home():
    return send_from_directory('static/pages', 'home.html')

@app.route('/choose')
def choose():
    return send_from_directory('static/pages', 'choose.html')

@app.route('/chat/<chat_id>')
def chat(chat_id):
    return redirect(url_for('chat_page', chat_id=chat_id))

@app.route('/chat_page')
def chat_page():
    return send_from_directory('static/pages', 'chat.html')

@app.route('/api/get_chats')
async def get_chats():
    server_ip = "localhost"
    server_port = 5001
    reader, writer = await asyncio.open_connection(server_ip, server_port)
    user = os.getlogin()
    writer.write(f"req:{user}\n".encode())
    await writer.drain()
    response = await reader.readuntil(separator=b"~~~END~~~")
    server_message = response.decode()
    possible_chats = server_message.split("~~~END~~~")[0]
    writer.write("aexit".encode())
    writer.close()
    possible_chats = possible_chats.split(",")
    possible_chats = ["0"] + possible_chats
    json = {"chats": possible_chats}
    return json

@app.route('/api/get_chat/<chat_id>')
async def get_chat(chat_id):
    server_ip = "localhost"
    server_port = 5001
    reader, writer = await asyncio.open_connection(server_ip, server_port)
    user = os.getlogin()
    writer.write(f"req:{user}\n".encode())
    await writer.drain()
    response = await reader.readuntil(separator=b"~~~END~~~")
    server_message = response.decode()
    possible_chats = server_message.split("~~~END~~~")[0]
    chat_id = int(chat_id)
    writer.write(f"ch:{chat_id}\n".encode())
    await writer.drain()
    response = await reader.readuntil(separator=b"~~~END~~~")
    server_message = response.decode()
    server_message = server_message.split("~~~END~~~")[0]
    writer.write("aexit".encode())
    server_message = server_message[5:]
    server_message = server_message.split("\n")
    return {'message': server_message}

@app.route('/api/chat/<chat_id>', methods=['POST'])
async def chat_api(chat_id):
    data = request.get_json()
    message = data.get('message')
    server_ip = "localhost"
    server_port = 5001
    reader, writer = await asyncio.open_connection(server_ip, server_port)
    user = os.getlogin()
    writer.write(f"req:{user}\n".encode())
    await writer.drain()
    response = await reader.readuntil(separator=b"~~~END~~~")
    server_message = response.decode()
    possible_chats = server_message.split("~~~END~~~")[0]
    chat_id = int(chat_id)
    writer.write(f"ch:{chat_id}\n".encode())
    await writer.drain()
    response = await reader.readuntil(separator=b"~~~END~~~")
    server_message = response.decode()
    server_message = server_message.split("~~~END~~~")[0]
    writer.write(f"{message}\n".encode())
    await writer.drain()
    response = await reader.readuntil(separator=b"~~~END~~~")
    server_message = response.decode()
    server_message = server_message.split("~~~END~~~")[0]
    writer.write("exit".encode())
    return jsonify({"response": server_message})



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1488)