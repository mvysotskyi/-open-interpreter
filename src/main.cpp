#include <boost/asio.hpp>
#include <iostream>
#include <string>
#include <sstream>
#include <fstream>
#include <readline/readline.h>
#include <readline/history.h>
#include <sys/types.h>
#include <unistd.h>
#include <cstdlib>
#include <sys/wait.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <cstring>
using boost::asio::ip::tcp;


bool is_cgroup_v2() {
    std::ifstream mounts("/proc/mounts");
    std::string line;
    while (std::getline(mounts, line)) {
        if (line.find("cgroup2") != std::string::npos) {
            return true;
        }
    }
    return false;
}

void execute_as_root(const std::string& command) {
    std::string sudo_command = "sudo " + command;
    int ret = system(sudo_command.c_str());
    if (ret != 0) {
        std::cerr << "Command failed: " << sudo_command << std::endl;
        exit(EXIT_FAILURE);
    }
}

void set_memory_limit(const std::string& group_name, int memory_limit_mb, pid_t pid) {
    bool cgroup_v2 = is_cgroup_v2();
    std::ostringstream cgroup_path;

    if (cgroup_v2) {
        cgroup_path << "/sys/fs/cgroup/" << group_name;
    } else {
        cgroup_path << "/sys/fs/cgroup/memory/" << group_name;
    }

    // Create the cgroup
    std::ostringstream mkdir_cmd;
    mkdir_cmd << "mkdir -p " << cgroup_path.str();
    execute_as_root(mkdir_cmd.str());

    // Join cgroup
    std::ostringstream join_cmd;
    join_cmd << "echo " << pid << " | sudo tee " << cgroup_path.str() << (cgroup_v2 ? "/cgroup.procs" : "/tasks") << " > /dev/null";
    execute_as_root(join_cmd.str());

    // Set memory limit
    std::ostringstream mem_cmd;
    mem_cmd << "echo " << (memory_limit_mb * 1024 * 1024) << " | sudo tee " 
            << cgroup_path.str() << (cgroup_v2 ? "/memory.max" : "/memory.limit_in_bytes") << " > /dev/null";
    execute_as_root(mem_cmd.str());
}
int safe_exec(const char* command, int memory_limit_mb, int cpu_core) {

    pid_t pid = fork();

    if (pid == 0) {
        execlp("/bin/sh", "sh", "-c", command, nullptr);
        perror("execlp");
        exit(EXIT_FAILURE);
    } else if (pid > 0) {
        std::string group_name = "cpp_group";


        //set_cpu_affinity(pid, cpu_core);

        set_memory_limit(group_name, memory_limit_mb, pid);
        waitpid(pid, nullptr, 0);
    } else {
        perror("fork");
        exit(EXIT_FAILURE);
    }

    return 0;
}

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

                                    int return_code = safe_exec("python3 temp_script.py", 1, 1);

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
                                int return_code = safe_exec(command.c_str(), 1,1);

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
