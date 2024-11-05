from abc import ABC, abstractmethod
from openai import OpenAI


class LLM(ABC):
    @abstractmethod
    def get_response(self, message):
        ...
    
    @abstractmethod
    def get_completion(self, message):
        ...


class OpenAILLM(LLM):
    message_template = lambda x: [
        {"role": "user", "content": f"Write only shell code without comments to answer this: {x}"}
    ]

    def __init__(self, api_key, model="gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model_name = model
    
    def get_response(self, message):
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=__class__.message_template(message)
        )

        return '\n'.join(completion.choices[0].message.content.split('\n')[1:-1])
    
    def get_completion(self, message):
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=__class__.message_template(message)
        )

        return completion.choices[0].message.content