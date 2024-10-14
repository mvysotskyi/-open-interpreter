#include <iostream>
#include <string>
#include <boost/asio.hpp>
#include <cstdlib> // for system()

using boost::asio::ip::tcp;


class AsyncTCPClient {
public:
    AsyncTCPClient(boost::asio::io_context& io_context, const std::string& host, const std::string& port, const std::string& input)
            : resolver_(io_context), socket_(io_context) {
        resolver_.async_resolve(host, port,
                                std::bind(&AsyncTCPClient::on_resolve, this, std::placeholders::_1, std::placeholders::_2, input));
    }
    std::string get_output(){
        return llm;
    }
private:
    tcp::resolver resolver_;
    tcp::socket socket_;
    boost::asio::streambuf response_;
    std::string llm;
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
            std::cerr << "Error while reading: " << err.message() << "\n";
            return;
        }

        const std::size_t block_size = 16;                    // Define the block size
        std::vector<char> buffer(block_size);                   // Buffer to hold each block of data
        std::string response_data;                              // String to accumulate the full response

        boost::system::error_code error;                        // Variable to capture any errors

        while (true) {
            std::size_t bytes_read = socket_.read_some(boost::asio::buffer(buffer), error);

            if (error == boost::asio::error::eof) {
                std::cout << bytes_read<<"Connection closed by server.\n";
                break;
            }
            else if (error) {
                std::cerr << "Error while reading: " << error.message() << "\n";
                break;
            }


            response_data.append(buffer.data(), bytes_read);

            std::cout.write(buffer.data(), bytes_read);

            if (bytes_read < block_size) {
                break;
            }
        }

        llm = response_data;
        socket_.close();
    }
};


int main() {
    std::string input;
    std::string response;
    std::string output;
    while (true) {
        std::cout << "Enter your questions: ";
        std::getline(std::cin, input);
        if (input == "exit"){
            break;
        }
        input += '\n';
        try {
            boost::asio::io_context io_context;
            AsyncTCPClient client(io_context, "localhost", "5000", input);
            io_context.run();
            output = client.get_output();
        } catch (std::exception &e) {
            std::cerr << "Exception: " << e.what() << std::endl;
        }
        std::cout << "Do you approve this code (Yes/No)?";
        while (true){
            getline(std::cin, response);
            if (response=="Yes" | response=="No" | response == "exit")
                break;
            std::cout << "Only Yes, No or exit is approved\n";
            std::cout << "Your response: " << response;
        }
        if (response == "exit"){
            break;
        }
        if (response == "Yes"){
            int result = system(output.c_str());
        }
    }
    return 0;
}
