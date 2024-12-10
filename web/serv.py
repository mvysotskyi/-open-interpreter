import asyncio
import os

async def connect_to_server(server_ip, server_port):
    reader, writer = await asyncio.open_connection(server_ip, server_port)
    print(f"Connected to {server_ip}:{server_port}")

    user = os.getlogin()
    writer.write(f"req:{user}\n".encode())
    await writer.drain()

    response = await reader.readuntil(separator=b"~~~END~~~")
    server_message = response.decode()
    possible_chats = server_message.split("~~~END~~~")[0]
    print(f"Possible chats: {possible_chats}")

    chats_number = 0 if not possible_chats else possible_chats.count(',') + 1

    message = input("Choose a chat(0 to create a new chat): ")

    try:
        chat_number = int(message)
        if chat_number < 0 or chat_number > chats_number:
            raise ValueError("Invalid chat number.")
    except ValueError as e:
        print(e)
        writer.close()
        await writer.wait_closed()
        return

    writer.write(f"ch:{message}\n".encode())
    await writer.drain()

    cnt_flag = False
    while True:
        if not cnt_flag:
            response = await reader.readuntil(separator=b"~~~END~~~")
            server_message = response.decode()
            server_message = server_message.split("~~~END~~~")[0]

            if not server_message.startswith("load"):
                print(server_message)
                message = input("Do you want to execute this code? (y/n): ")
                if message == "y":
                    start_tag = "```shell"
                    end_tag = "```"
                    start_pos = server_message.find(start_tag)
                    end_pos = server_message.find(end_tag, start_pos + len(start_tag))

                    if start_pos == -1:
                        start_tag = "```bash"
                        start_pos = server_message.find(start_tag)
                        end_pos = server_message.find(end_tag, start_pos + len(start_tag))

                    if start_pos == -1:
                        start_tag = "```python"
                        start_pos = server_message.find(start_tag)
                        end_pos = server_message.find(end_tag, start_pos + len(start_tag))

                    if start_pos != -1 and end_pos != -1:
                        script = server_message[start_pos + len(start_tag):end_pos].strip()

                        if start_tag == "```python":
                            with open("temp_script.py", "w") as python_file:
                                python_file.write(script)
                            print(f"Executing Python script:\n{script}")
                            return_code = os.system("python3 temp_script.py")
                            if return_code == 0:
                                print("Python script executed successfully.")
                            else:
                                print("Error executing Python script.")
                            os.remove("temp_script.py")
                        else:
                            print(f"Executing shell script:\n{script}")
                            return_code = os.system(script)
                            if return_code == 0:
                                print("Shell script executed successfully.")
                            else:
                                print("Error executing shell script.")
                    else:
                        print("No supported code block (shell/bash/python) found in the message.")
                else:
                    print(server_message[5:])
            else:
                print(server_message[5:])
        message = input("Enter message ('exit' to quit): ")
        if message:
            cnt_flag = False
        else:
            cnt_flag = True
            continue

        writer.write(f"{message}\n".encode())
        await writer.drain()

        if message == "exit":
            print("Exiting...")
            break

    writer.close()
    await writer.wait_closed()

asyncio.run(connect_to_server('localhost', 5001))