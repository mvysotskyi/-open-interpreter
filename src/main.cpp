#include <boost/asio.hpp>
#include <iostream>
#include <string>
#include <sstream>
#include <fstream>

#include <readline/readline.h>
#include <readline/history.h>


using boost::asio::ip::tcp;

int count_chars(const std::string& str, char c) {
    int count = 0;
    for (char ch : str) {
        if (ch == c) {
            count++;
        }
    }
    return count;
}

int main(int argc, char* argv[]) {
    if (argc != 3) {
        std::cerr << "Usage: client <server_ip> <server_port>\n";
        return 1;
    }

    std::string server_ip = argv[1];
    int server_port = std::stoi(argv[2]);

    boost::asio::io_context io_context;

    try {
        tcp::socket socket(io_context);

        tcp::resolver resolver(io_context);
        auto endpoints = resolver.resolve(server_ip, std::to_string(server_port));

        boost::asio::connect(socket, endpoints);

        std::string message;
        char user[1024];
        getlogin_r(user, 1024);

        boost::asio::write(socket, boost::asio::buffer("req:" + (std::string)user + "\n"));

        boost::asio::streambuf response;

        // Read and print the initial chat options
        boost::asio::read_until(socket, response, "~~~END~~~");
        std::istream response_stream(&response);
        std::string server_message;

        std::getline(response_stream, server_message, '\0'); // Read the response until EOF
        response.consume(response.size()); // Clear the streambuf

        std::string possible_chats = server_message.substr(0, server_message.find("~~~END~~~"));
        std::cout << "Possible chats: " << possible_chats << std::endl;

        int chats_number = possible_chats.empty() ? 0 : count_chars(possible_chats, ',') + 1;

        char* buf;
        buf = readline("Choose a chat(0 to create a new chat): ");
        
        message = buf;
        free(buf);

        try {
            int chat_number = std::stoi(message);

            if (chat_number < 0 || chat_number > chats_number) {
                throw std::exception();
            }
        } catch (std::exception& e) {
            std::cerr << "Invalid chat number." << std::endl;
            return 1;
        }

        boost::asio::write(socket, boost::asio::buffer("ch:" + message + "\n"));

        bool cnt_flag = false;
        while (true) {
            if(!cnt_flag) {
                boost::asio::streambuf response;
                boost::asio::read_until(socket, response, "~~~END~~~");

                std::istream response_stream(&response);
                std::ostringstream ss;

                ss << response_stream.rdbuf();
                server_message = ss.str();
                server_message = server_message.substr(0, server_message.find("~~~END~~~")); // Remove delimiter



                if (server_message.compare(0, 4, "load") != 0){
                    std::cout << server_message << '\n';
                    buf = readline("Do you want to execute this code? (y/n):");
                    message = buf;
                    free(buf);

                    if (message == "y") {
                        std::string start_tag = "```shell";
                        std::string end_tag = "```";

                        // Check if it's a shell script
                        size_t start_pos = server_message.find(start_tag);
                        size_t end_pos = server_message.find(end_tag, start_pos + start_tag.length());

                        // Check for bash if shell script is not found
                        if (start_pos == std::string::npos) {
                            start_tag = "```bash";
                            start_pos = server_message.find(start_tag);
                            end_pos = server_message.find(end_tag, start_pos + start_tag.length());
                        }

                        // Check if it's Python code
                        if (start_pos == std::string::npos) {
                            start_tag = "```python";
                            start_pos = server_message.find(start_tag);
                            end_pos = server_message.find(end_tag, start_pos + start_tag.length());
                        }

                        // Execute shell or Python script based on detection
                        if (start_pos != std::string::npos && end_pos != std::string::npos) {
                            std::string script = server_message.substr(start_pos + start_tag.length(), end_pos - (start_pos + start_tag.length()));

                            if (start_tag == "```python") {
                                // Write Python code to a file and execute it
                                std::ofstream python_file("temp_script.py");
                                if (python_file.is_open()) {
                                    python_file << script;
                                    python_file.close();
                                    std::cout << "Executing Python script:\n" << script << std::endl;

                                    int return_code = system("python3 temp_script.py");

                                    if (return_code == 0) {
                                        std::cout << "Python script executed successfully." << std::endl;
                                    } else {
                                        std::cerr << "Error executing Python script." << std::endl;
                                    }

                                    // Optionally, delete the Python script after execution
                                    std::remove("temp_script.py");
                                } else {
                                    std::cerr << "Failed to write Python script to file." << std::endl;
                                }
                            } else {
                                // Execute shell commands
                                std::string command = script;
                                std::cout << "Executing shell script:\n" << command << std::endl;
                                int return_code = system(command.c_str());

                                if (return_code == 0) {
                                    std::cout << "Shell script executed successfully." << std::endl;
                                } else {
                                    std::cerr << "Error executing shell script." << std::endl;
                                }
                            }
                        } else {
                            std::cerr << "No supported code block (shell/bash/python) found in the message." << std::endl;
                        }
                    }
                } else {
                    std::cout << server_message.substr(5) << '\n';
                }
            }


            buf = readline("Enter message ('exit' to quit): ");
            if (buf[0] != '\0') {
                add_history(buf);
                cnt_flag = false;
            } else {
                cnt_flag = true;
                continue;
            }

            message = buf;
            free(buf);

            boost::asio::write(socket, boost::asio::buffer(message + "\n"));

            if (message == "exit") {
                std::cout << "Exiting...\n";
                break;
            }
        }

        socket.close();
    } catch (std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    return 0;
}
