from abc import ABC, abstractmethod
import openai
from openai import OpenAI
import os
from transformers import AutoModelForCausalLM, AutoTokenizer


class LLM(ABC):
    @abstractmethod
    def get_response(self, message):
        ...
    
    @abstractmethod
    def get_completion(self, message):
        ...


class QwenLLM(LLM):
    def __init__(self): 
        model_id = "Qwen/Qwen2.5-Coder-0.5B-Instruct"
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype="auto",
            device_map="auto"
        )
        self.chat_context = [
            {
                "role": "system", 
                "content": f"You are an AI assistant, that only writes code. You are here {os.getcwd()}. Code only should be either Python or Shell. Return only code as response."
            },
        ]
        
    def add_system_context(self, message):
        self.chat_context.append({"role": "system", "content": message})
    
    def load_chat_context(self, context):
        if context == []:
            self.chat_context = [
                {
                    "role": "system", 
                    "content": f"You are an AI assistant, that only writes code. You are here {os.getcwd()}. Code only should be either Python or Shell. Return only code as response."
                },
            ]
        self.chat_context = context

    def add_context(self, message, role):
        self.chat_context.append({"role": role, "content": message})
    
    def get_response(self, message, add_context=False):        
        inputs = self.tokenizer.apply_chat_template(
            self.chat_context + [{"role": "user","content":message}],
            add_generation_prompt=True,
            tokenize=False)

        inputs = self.tokenizer([inputs], return_tensors = "pt")
        inputs.to(self.model.device)
        generated_ids = self.model.generate(inputs.input_ids, max_new_tokens=1000)

        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(inputs.input_ids, generated_ids)
        ]

        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

        if add_context:
            self.add_context(message, "user")
            self.add_context(response.text, "assistant")
        return response

    def get_completion(self, message):
        return self.get_response(message, add_context=True)

class OpenAILLM(LLM):
    def __init__(self, api_key, model="gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model_name = model
        self.chat_context = [
            {
                "role": "system", 
                "content": f"You are an AI assistant, that only writes code. You are here {os.getcwd()}. Code only should be either Python or Shell. You should not write any other language code."
            },
        ]

    def get_chat_context(self):
        return self.chat_context
    
    def load_chat_context(self, context):
        if context == []:
            self.chat_context = [
            {"role": "system", "content": f"You are an AI assistant, that only writes code. You are here {os.getcwd()}. Code only should be either Python or Shell. You should not write any other language code."},
            ]
        else:
            self.chat_context = context
    
    # def unload_chat_context(self):
    #     cache = self.chat_context.copy()
    #     self.chat_context = [
    #     {"role": "system", "content": f"You are an AI assistant, that only writes code. Code only should be either Python or Shell. You should not write any other language code."},
    #     ]
    #     return cache
         
    def get_response(self, message):
        self.chat_context.append({"role": "user", "content": message})
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.chat_context
        )
        self.chat_context.append({"role": "assistant", "content": completion.choices[0].message.content})

        return '\n'.join(completion.choices[0].message.content.split('\n'))
    
    def get_completion(self, message):
        self.chat_context.append({"role": "user", "content": message})
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.chat_context
        )
        self.chat_context.append({"role": "assistant", "content": completion.choices[0].message.content})

        return completion.choices[0].message.content



class SafetyEvaluator:
    def __init__(self, api_key, model="gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model_name = model

        self.chat_context = [
            {
                "role": "system", 
                "content": f"You are a safety analyst in software company. You need to evaluate how damaging given code could possibly be."
            },
        ]

        # Unsafe Commands: These commands can cause system damage or data loss if executed improperly
        self.unsafe_commands = {
            "rm",          # Remove files or directories
            "dd",          # Low-level copying and writing to devices
            "mkfs",        # Formatting disks
            "chmod",       # Change file permissions
            "sudo",        # Run commands with superuser privileges
            "su",          # Switch user to superuser
            "shutdown",    # Shut down the system
            "reboot",      # Reboot the system
            "kill",        # Terminate processes (can cause system instability)
            "mktemp",      # Create temporary files (can be unsafe in some cases)
            "tar",         # Extract files (can overwrite important files)
            "wget",         # Download files (can download malicious scripts)
            "curl"         # Download files (can download malicious scripts)
        }

        self.unsafe_scripts = {
            "os.remove",                # Deletes a file
            "os.rmdir",                 # Removes a directory
            "shutil.rmtree",            # Recursively delete a directory and its contents
            "subprocess.call",          # Executes a system command (could run harmful commands)
            "subprocess.Popen",         # Executes system commands in new processes
            "os.system",                # Executes system commands
            "eval",                     # Executes dynamically generated Python code (can run arbitrary code)
            "exec",                     # Executes Python code dynamically (can run arbitrary code)
            "builtins.open",            # Open files (could be used for unauthorized file access)
            "builtins.input",           # Accepts user input (can be used to get sensitive information)
            "socket.socket",            # Can be used for network communication (potential security risk)
            "os.environ",               # Can access environment variables, potentially sensitive information
            "os.chmod",                 # Change file permissions (can alter system files)
            "os.setuid",                # Change user ID, could be used to escalate privileges
            "os.setgid",                # Change group ID, could be used to escalate privileges
            "multiprocessing.Process",  # Running multiple processes that could be potentially dangerous
        }
    
    def evaluate(self, message):
        for command in self.unsafe_commands:
            if command in message:
                return "harmful"
        for script in self.unsafe_scripts:
            if script in message:
                return "harmful"
                
        self.chat_context.append({
            "role": "user", 
            "content": "Answer only as  one of those options [very safe, safe, potentially harmful, harmful] : " + message
        })

        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.chat_context
        )
        
        options = ["very safe", "safe", "potentially harmful", "harmful"][::-1]
        response  = '\n'.join(completion.choices[0].message.content.split('\n'))
        for option in options:
            if option in response.lower():
                return option
        return response


class ResourcesEvalutor:
    def __init__(self, api_key, model="gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model_name = model

        self.chat_context = [
            {
                "role": "system", 
                "content": f"You are a code analyst specialist in software company. You need to evaluate how much given code could use RAM and how long it could take to execute."
            },
        ]

    def evaluate(self, message):
        self.chat_context.append({
            "role": "user", 
            "content": "Give answer strictly in format: 'N MB/KB/GB of memory, M seconds'. Write only summary: " + message
        })

        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=self.chat_context
        )
        
        response  = '\n'.join(completion.choices[0].message.content.split('\n'))
        print(response, "miwa")
        return response