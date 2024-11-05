#include <boost/asio.hpp>
#include <iostream>
#include <string>

using boost::asio::ip::tcp;

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
        while (true) {
            std::cout << "Enter message ('exit' to quit): ";
            std::getline(std::cin, message);

            boost::asio::write(socket, boost::asio::buffer(message + "\n"));

            if (message == "exit") {
                std::cout << "Exiting...\n";
                break;
            }

            boost::asio::streambuf response;
            boost::asio::read_until(socket, response, "\n");

            std::istream response_stream(&response);
            std::string server_message;
            std::getline(response_stream, server_message);
            std::cout << "Server response: " << server_message << '\n';
        }

        socket.close();
    } catch (std::exception& e) {
        std::cerr << "Exception: " << e.what() << "\n";
    }

    return 0;
}
