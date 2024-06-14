from MAD_based.utils.agent import Agent


class DebatePlayer(Agent):
    def __init__(self, name: str, temperature: float, verbose: bool) -> None:
        """Create a player in the debate

        Args:
            model_name(str): model name
            name (str): name of this player
            temperature (float): higher values make the output more random, while lower values make it more focused and deterministic
            openai_api_key (str): As the parameter name suggests
            sleep_time (float): sleep because of rate limits
        """
        super(DebatePlayer, self).__init__(name, temperature, verbose)
