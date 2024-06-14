if __name__ == "__main__":
    import sys

    sys.path.append("../..")

import colorlog
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from termcolor import colored

from common.model_loader import make_chat_model
from common.model_loader import model as llm
from MAD_based.utils.log_config import handler, log_level


class Player:
    def __init__(
        self,
        system_prompt,
        name,
        chat_memory_retriever,
        model_kwargs=None,
        temperature=0.0,
    ):
        self.model = llm if not model_kwargs else make_chat_model(**model_kwargs)

        self.name = name
        self.logger = colorlog.getLogger(name)
        self.logger.setLevel(log_level)
        self.logger.addHandler(handler)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        self.history = chat_memory_retriever(name)
        self.session_retriever = chat_memory_retriever
        self.temperature = temperature
        chain = self.prompt | self.model.bind(temperature=temperature)
        self.chain = RunnableWithMessageHistory(
            chain,
            self.session_retriever,
            input_messages_key="input",
            history_messages_key="chat_history",
        )

    def reset_history(self):
        self.history.clear()

    def switch_temperature(self):
        self.temperature = 1 - self.temperature
        chain = self.prompt | self.model.bind(temperature=self.temperature)
        self.chain.bind(runnable=chain)

    def reset_system_prompt(self, new_value):
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", new_value),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

        chain = self.prompt | self.model.bind(self.temperature)
        self.chain = RunnableWithMessageHistory(
            chain,
            self.session_retriever,
            input_messages_key="input",
            history_messages_key="chat_history",
        )

    def add_artificial_memory(self, user_message, player_answer):
        self.history.add_user_message(user_message)
        self.history.add_ai_message(player_answer)

    def ask(self, input_message):
        self.logger.debug(colored(input_message, "light_yellow"))
        response = self.chain.invoke(
            {"input": input_message}, {"configurable": {"session_id": self.name}}
        ).content
        self.logger.info(colored(response, "light_blue"))
        return response


if __name__ == "__main__":
    player = Player("You are a helpful assistant", "Player")
    query = input("Ask a question: ")
    while query != "q":
        print(player.ask(query))
        query = input("Ask a question: ")
