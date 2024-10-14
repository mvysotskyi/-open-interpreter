cmake_minimum_required(VERSION 3.15)

set(PROJECT_NAME open_interpreter)
project(${PROJECT_NAME} C CXX)

set(CMAKE_CXX_STANDARD 20)

add_executable(client src/main.cpp)

find_package(Boost 1.71.0 COMPONENTS system REQUIRED)
target_include_directories(client PRIVATE ${Boost_INCLUDE_DIR})
target_link_libraries(client Boost::system)