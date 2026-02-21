"""Claude API client wrappers with retry logic, sync and async."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import AsyncIterator, Iterator

from data_clients.exceptions import LLMError

logger = logging.getLogger(__name__)


class LLMClient:
    """Synchronous wrapper around the Anthropic SDK."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-haiku-4-5-20251001",
        max_retries: int = 3,
    ):
        if not api_key:
            raise LLMError(
                "Anthropic API key is required. "
                "Pass it directly or set ANTHROPIC_API_KEY in your environment."
            )
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic is required for LLMClient. "
                "Install with: pip install data-clients[llm]"
            )
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_retries = max_retries

    def generate(
        self,
        system_prompt: str,
        user_content: str,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> dict:
        """Send a message to Claude and return the response with usage info.

        Returns:
            dict with keys: text, input_tokens, output_tokens, model
        """
        from anthropic import APIError, APITimeoutError, RateLimitError

        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_content}],
                )
                return {
                    "text": response.content[0].text,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "model": self.model,
                }
            except RateLimitError:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Rate limited, retrying in {wait}s (attempt {attempt + 1})")
                time.sleep(wait)
            except APITimeoutError:
                wait = 2 ** attempt
                logger.warning(f"API timeout, retrying in {wait}s (attempt {attempt + 1})")
                time.sleep(wait)
            except APIError as e:
                raise LLMError(f"Claude API error: {e}") from e

        raise LLMError(f"Failed after {self.max_retries} retries")

    def generate_with_tools(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ):
        """Multi-turn message call with tool definitions.

        Returns the raw Anthropic response object.
        """
        from anthropic import APIError, APITimeoutError, RateLimitError

        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=messages,
                    tools=tools,
                )
                return response
            except RateLimitError:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Rate limited, retrying in {wait}s (attempt {attempt + 1})")
                time.sleep(wait)
            except APITimeoutError:
                wait = 2 ** attempt
                logger.warning(f"API timeout, retrying in {wait}s (attempt {attempt + 1})")
                time.sleep(wait)
            except APIError as e:
                raise LLMError(f"Claude API error: {e}") from e

        raise LLMError(f"Failed after {self.max_retries} retries")

    def stream(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> Iterator[str]:
        """Stream a response, yielding text chunks."""
        from anthropic import APIError, APITimeoutError, RateLimitError

        for attempt in range(self.max_retries):
            try:
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=messages,
                ) as stream:
                    for text in stream.text_stream:
                        yield text
                return
            except RateLimitError:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Rate limited, retrying in {wait}s (attempt {attempt + 1})")
                time.sleep(wait)
            except APITimeoutError:
                wait = 2 ** attempt
                logger.warning(f"API timeout, retrying in {wait}s (attempt {attempt + 1})")
                time.sleep(wait)
            except APIError as e:
                raise LLMError(f"Claude API error: {e}") from e

        raise LLMError(f"Failed after {self.max_retries} retries")


class AsyncLLMClient:
    """Asynchronous wrapper around the Anthropic SDK."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-haiku-4-5-20251001",
        max_retries: int = 3,
    ):
        if not api_key:
            raise LLMError(
                "Anthropic API key is required. "
                "Pass it directly or set ANTHROPIC_API_KEY in your environment."
            )
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            raise ImportError(
                "anthropic is required for AsyncLLMClient. "
                "Install with: pip install data-clients[llm]"
            )
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self.max_retries = max_retries

    async def generate(
        self,
        system_prompt: str,
        user_content: str,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> dict:
        """Send a message to Claude and return the response with usage info."""
        from anthropic import APIError, APITimeoutError, RateLimitError

        for attempt in range(self.max_retries):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_content}],
                )
                return {
                    "text": response.content[0].text,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "model": self.model,
                }
            except RateLimitError:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Rate limited, retrying in {wait}s (attempt {attempt + 1})")
                await asyncio.sleep(wait)
            except APITimeoutError:
                wait = 2 ** attempt
                logger.warning(f"API timeout, retrying in {wait}s (attempt {attempt + 1})")
                await asyncio.sleep(wait)
            except APIError as e:
                raise LLMError(f"Claude API error: {e}") from e

        raise LLMError(f"Failed after {self.max_retries} retries")

    async def generate_with_tools(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ):
        """Multi-turn message call with tool definitions."""
        from anthropic import APIError, APITimeoutError, RateLimitError

        for attempt in range(self.max_retries):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=messages,
                    tools=tools,
                )
                return response
            except RateLimitError:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Rate limited, retrying in {wait}s (attempt {attempt + 1})")
                await asyncio.sleep(wait)
            except APITimeoutError:
                wait = 2 ** attempt
                logger.warning(f"API timeout, retrying in {wait}s (attempt {attempt + 1})")
                await asyncio.sleep(wait)
            except APIError as e:
                raise LLMError(f"Claude API error: {e}") from e

        raise LLMError(f"Failed after {self.max_retries} retries")

    async def stream(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> AsyncIterator[str]:
        """Stream a response, yielding text chunks."""
        from anthropic import APIError, APITimeoutError, RateLimitError

        for attempt in range(self.max_retries):
            try:
                async with self.client.messages.stream(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=messages,
                ) as stream:
                    async for text in stream.text_stream:
                        yield text
                return
            except RateLimitError:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Rate limited, retrying in {wait}s (attempt {attempt + 1})")
                await asyncio.sleep(wait)
            except APITimeoutError:
                wait = 2 ** attempt
                logger.warning(f"API timeout, retrying in {wait}s (attempt {attempt + 1})")
                await asyncio.sleep(wait)
            except APIError as e:
                raise LLMError(f"Claude API error: {e}") from e

        raise LLMError(f"Failed after {self.max_retries} retries")
