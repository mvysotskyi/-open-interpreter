#include <iostream>
#include <string>
#include <boost/asio.hpp>

using boost::asio::ip::tcp;

class AsyncTCPClient {
public:
    AsyncTCPClient(boost::asio::io_context& io_context, const std::string& host, const std::string& port, const std::string& input)
            : resolver_(io_context), socket_(io_context) {
        resolver_.async_resolve(host, port,
                                std::bind(&AsyncTCPClient::on_resolve, this, std::placeholders::_1, std::placeholders::_2, input));
    }

private:
    tcp::resolver resolver_;
    tcp::socket socket_;
    boost::asio::streambuf response_;

    void on_resolve(const boost::system::error_code& err, tcp::resolver::results_type results, const std::string& input) {
        if (err) {
            std::cerr << "Resolve error: " << err.message() << std::endl;
            return;
        }
        boost::asio::async_connect(socket_, results,
                                   std::bind(&AsyncTCPClient::on_connect, this, std::placeholders::_1, std::placeholders::_2, input));
    }

    void on_connect(const boost::system::error_code& err, const tcp::endpoint& endpoint, const std::string& input) {
        if (err) {
            std::cerr << "Connect error: " << err.message() << std::endl;
            return;
        }

        boost::asio::async_write(socket_, boost::asio::buffer(input),
                                 std::bind(&AsyncTCPClient::on_write, this, std::placeholders::_1));
    }

    void on_write(const boost::system::error_code& err) {
        if (err) {
            std::cerr << "Write error: " << err.message() << std::endl;
            return;
        }

        boost::asio::async_read_until(socket_, response_, "\n",
                                      std::bind(&AsyncTCPClient::on_read, this, std::placeholders::_1));
    }

    void on_read(const boost::system::error_code& err) {
        if (err) {
            std::cerr << "Read error: " << err.message() << std::endl;
            return;
        }

        std::istream response_stream(&response_);
        std::string response_data((std::istreambuf_iterator<char>(response_stream)), std::istreambuf_iterator<char>());
        std::cout << "Response from server: " << response_data << std::endl;

        // Close the socket
        socket_.close();
    }
};

int main() {
    std::string input;
    std::cout << "Enter your input: ";
    std::getline(std::cin, input);
    input += '\n';

    try {
        boost::asio::io_context io_context;
        AsyncTCPClient client(io_context, "localhost", "5000", input);
        io_context.run();
    } catch (std::exception& e) {
        std::cerr << "Exception: " << e.what() << std::endl;
    }

    return 0;
}
