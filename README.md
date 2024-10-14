# open-interpreter

**Team**: Tkhir Nazar, Vysotskyi Mykola, Petro Prokopets, Severyn Shykula

## Project description:
This project aims to create a Secure Terminal Assistant based on a **Large Language Model (LLM)**, either running **locally** or via an **API**. The assistant will be aware of the local computer's system information, enhancing both security and functionality. The model will provide intelligent responses and command execution tailored to the specific machine's environment, helping to manage tasks more securely.

## Installation

Install Boost:
```bash
$ sudo apt install libboost-dev-all
```

Install Python requirements:
```bash
$ python3 -m venv venv
$ source venv/bin/activate
$ pip3 install -r requirements.txt
```

## Build
```bash
$ mkdir build && cd build
$ cmake ..
$ make
```
## Usage

Run Python server:
```bash
$ python3 llm-server/main.py
```
```
Serving on port 5000...
Received input: How to remove folder in Linux?
```

Run client:
```bash
$ ./build/client
```
```
Enter your questions: How to remove folder in Linux?
rm -r folder_name
Do you approve this code (Yes/No)?
```
