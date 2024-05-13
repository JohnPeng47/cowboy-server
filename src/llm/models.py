import logging

# from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from dataclasses import dataclass, fields
from openai import BadRequestError, OpenAI, AzureOpenAI
from simple_parsing.helpers import FrozenSerializable, Serializable
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_not_exception_type,
)


# from typing import Optional

from openai import AsyncOpenAI
from src.config import OPENAI_API_KEY

logger = logging.getLogger("test_results")


@dataclass(frozen=True)
class ModelArguments(FrozenSerializable):
    model_name: str
    per_instance_cost_limit: float = 0.0
    total_cost_limit: float = 0.0
    temperature: float = 1.0
    top_p: float = 1.0
    replay_path: str = None
    host_url: str = "localhost:11434"


@dataclass
class APIStats(Serializable):
    total_cost: float = 0
    instance_cost: float = 0
    tokens_sent: int = 0
    tokens_received: int = 0
    api_calls: int = 0

    def __add__(self, other):
        if not isinstance(other, APIStats):
            raise TypeError("Can only add APIStats with APIStats")

        return APIStats(
            **{
                field.name: getattr(self, field.name) + getattr(other, field.name)
                for field in fields(self)
            }
        )

    def replace(self, other):
        if not isinstance(other, APIStats):
            raise TypeError("Can only replace APIStats with APIStats")

        return APIStats(
            **{field.name: getattr(other, field.name) for field in fields(self)}
        )


class ContextWindowExceededError(Exception):
    pass


class CostLimitExceededError(Exception):
    pass


class BaseModel:
    MODELS = {}
    SHORTCUTS = {}

    def __init__(self, args: ModelArguments):
        self.args = args
        self.model_metadata = {}
        self.stats = APIStats()

        # Map `model_name` to API-compatible name `api_model`
        self.api_model = (
            self.SHORTCUTS[self.args.model_name]
            if self.args.model_name in self.SHORTCUTS
            else self.args.model_name
        )

        # Map model name to metadata (cost, context info)
        MODELS = {
            **{dest: self.MODELS[src] for dest, src in self.SHORTCUTS.items()},
            **self.MODELS,
        }
        if args.model_name in MODELS:
            self.model_metadata = MODELS[args.model_name]
        else:
            raise ValueError(
                f"Unregistered model ({args.model_name}). Add model name to MODELS metadata to {self.__class__}"
            )

    def reset_stats(self, other: APIStats = None):
        if other is None:
            self.stats = APIStats(total_cost=self.stats.total_cost)
            logger.info("Resetting model stats")
        else:
            self.stats = other

    def update_stats(self, input_tokens, output_tokens):
        """
        Calculates the cost of a response from the openai API.

        Args:
        input_tokens (int): The number of tokens in the prompt.
        output_tokens (int): The number of tokens in the response.

        Returns:
        float: The cost of the response.
        """
        # Calculate cost and update cost related fields
        cost = (
            self.model_metadata["cost_per_input_token"] * input_tokens
            + self.model_metadata["cost_per_output_token"] * output_tokens
        )
        self.stats.total_cost += cost
        self.stats.instance_cost += cost
        self.stats.tokens_sent += input_tokens
        self.stats.tokens_received += output_tokens
        self.stats.api_calls += 1

        # Log updated cost values to std. out.
        logger.info(
            f"input_tokens={input_tokens:_}, "
            f"output_tokens={output_tokens:_}, "
            f"instance_cost={self.stats.instance_cost:.2f}, "
            f"cost={cost:.2f}"
        )
        logger.info(
            f"total_tokens_sent={self.stats.tokens_sent:_}, "
            f"total_tokens_received={self.stats.tokens_received:_}, "
            f"total_cost={self.stats.total_cost:.2f}, "
            f"total_api_calls={self.stats.api_calls:_}"
        )

        # Check whether total cost or instance cost limits have been exceeded
        # if (
        #     self.args.total_cost_limit > 0
        #     and self.stats.total_cost >= self.args.total_cost_limit
        # ):
        #     logger.warning(
        #         f"Cost {self.stats.total_cost:.2f} exceeds limit {self.args.total_cost_limit:.2f}"
        #     )
        #     raise CostLimitExceededError("Total cost limit exceeded")

        # if (
        #     self.args.per_instance_cost_limit > 0
        #     and self.stats.instance_cost >= self.args.per_instance_cost_limit
        # ):
        #     logger.warning(
        #         f"Cost {self.stats.instance_cost:.2f} exceeds limit {self.args.per_instance_cost_limit:.2f}"
        #     )
        #     raise CostLimitExceededError("Instance cost limit exceeded")
        return cost

    async def query(self, prompt: str) -> str:
        raise NotImplementedError("Use a subclass of BaseModel")


class OpenAIModel(BaseModel):
    MODELS = {
        "gpt-3.5-turbo-0125": {
            "max_context": 16_385,
            "cost_per_input_token": 5e-07,
            "cost_per_output_token": 1.5e-06,
        },
        "gpt-3.5-turbo-1106": {
            "max_context": 16_385,
            "cost_per_input_token": 1.5e-06,
            "cost_per_output_token": 2e-06,
        },
        "gpt-3.5-turbo-16k-0613": {
            "max_context": 16_385,
            "cost_per_input_token": 1.5e-06,
            "cost_per_output_token": 2e-06,
        },
        "gpt-4-32k-0613": {
            "max_context": 32_768,
            "cost_per_input_token": 6e-05,
            "cost_per_output_token": 0.00012,
        },
        "gpt-4-0613": {
            "max_context": 8_192,
            "cost_per_input_token": 3e-05,
            "cost_per_output_token": 6e-05,
        },
        "gpt-4-1106-preview": {
            "max_context": 128_000,
            "cost_per_input_token": 1e-05,
            "cost_per_output_token": 3e-05,
        },
        "gpt-4-0125-preview": {
            "max_context": 128_000,
            "cost_per_input_token": 1e-05,
            "cost_per_output_token": 3e-05,
        },
    }

    SHORTCUTS = {
        "gpt3": "gpt-3.5-turbo-1106",
        "gpt3-legacy": "gpt-3.5-turbo-16k-0613",
        "gpt4": "gpt-4-1106-preview",
        "gpt4-legacy": "gpt-4-0613",
        "gpt4-0125": "gpt-4-0125-preview",
        "gpt3-0125": "gpt-3.5-turbo-0125",
    }

    def __init__(self, args: ModelArguments):
        super().__init__(args)

        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    def history_to_messages(
        self, history: list[dict[str, str]], is_demonstration: bool = False
    ) -> list[dict[str, str]]:
        """
        Create `messages` by filtering out all keys except for role/content per `history` turn
        """
        # Remove system messages if it is a demonstration
        if is_demonstration:
            history = [entry for entry in history if entry["role"] != "system"]
            return "\n".join([entry["content"] for entry in history])
        # Return history components with just role, content fields
        return [
            {k: v for k, v in entry.items() if k in ["role", "content"]}
            for entry in history
        ]

    @retry(
        wait=wait_random_exponential(min=1, max=15),
        reraise=True,
        stop=stop_after_attempt(3),
        retry=retry_if_not_exception_type((CostLimitExceededError, RuntimeError)),
    )
    async def query(self, prompt: str) -> str:
        """
        Query the OpenAI API with the given `history` and return the response.
        """

        print("Querying MDOEL ....")
        try:
            # Perform OpenAI API call
            response = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.api_model,
            )

            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            self.update_stats(input_tokens, output_tokens)
            return response.choices[0].message.content

        except BadRequestError as e:
            raise CostLimitExceededError(
                f"Context window ({self.model_metadata['max_context']} tokens) exceeded"
            )
