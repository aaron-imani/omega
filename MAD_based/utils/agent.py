import openai
from tokenizers import Tokenizer

from common.model_loader import model, processed_model_name, raw_model_name, server_type

if server_type == "vllm":
    tokenizer = Tokenizer.from_pretrained(raw_model_name)

from termcolor import colored


class Agent:
    def __init__(self, name: str, temperature: float, verbose: bool) -> None:
        """Create an agent

        Args:
            model_name(str): model name
            name (str): name of this agent
            temperature (float): higher values make the output more random, while lower values make it more focused and deterministic
            sleep_time (float): sleep because of rate limits
        """

        self.model_name = processed_model_name
        self.name = name
        self.temperature = temperature
        self.verbose = verbose
        self.reset()

    def reset(self):
        self.memory_lst = []
        self.used_tokens = 0

    def query(self, messages: "list[dict]", max_tokens: int, temperature: float) -> str:
        """make a query

        Args:
            messages (list[dict]): chat history in turbo format
            max_tokens (int): max token in api call
            temperature (float): sampling temperature

        Raises:
            OutOfQuotaException: the apikey has out of quota
            AccessTerminatedException: the apikey has been ban

        Returns:
            str: the return msg
        """
        try:
            if server_type == "vllm":
                response = model.invoke(
                    messages, temperature=temperature, max_tokens=max_tokens
                )
            else:
                response = model.invoke(
                    messages, temperature=temperature, num_predict=max_tokens
                )

            gen = response.content
            if server_type == "vllm":
                self.used_tokens = response.response_metadata["token_usage"][
                    "total_tokens"
                ]
            else:
                self.used_tokens = (
                    response.response_metadata["prompt_eval_count"]
                    + response.response_metadata["eval_count"]
                )
            return gen

        except openai.BadRequestError as e:
            print("Error:", e.message)
            raise e

    def set_meta_prompt(self, meta_prompt: str):
        """Set the meta_prompt

        Args:
            meta_prompt (str): the meta prompt
        """
        self.used_tokens += self._estimate_tokens(meta_prompt)
        self.memory_lst.append({"role": "system", "content": f"{meta_prompt}"})

    def add_event(self, event: str):
        """Add an new event in the memory

        Args:
            event (str): string that describe the event.
        """
        self.used_tokens += self._estimate_tokens(event)
        self.memory_lst.append({"role": "user", "content": f"{event}"})

    def add_memory(self, memory: str):
        """Monologue in the memory

        Args:
            memory (str): string that generated by the model in the last round.
        """
        self.used_tokens += self._estimate_tokens(memory)
        self.memory_lst.append({"role": "assistant", "content": f"{memory}"})
        if self.verbose:
            print(f"{colored(self.name, 'green')}: {memory}\n")

    def _estimate_tokens(self, message: str) -> int:
        """Estimate the number of tokens in a string

        Args:
            message (str): the message

        Returns:
            int: the number of tokens
        """
        if server_type == "vllm":
            return len(tokenizer.encode(message).tokens)
        words = message.split()
        character_count = sum([len(w) for w in words])
        return round(character_count / 4)

    def ask(self, temperature: float = None):
        """Query for answer

        Args:
        """
        # query
        max_token = 8000 - self.used_tokens
        return self.query(
            self.memory_lst,
            max_token,
            temperature=temperature if temperature else self.temperature,
        )
