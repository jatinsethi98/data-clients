"""Claude API client wrappers with retry logic, sync and async."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import AsyncIterator, Iterator

from data_clients.exceptions import LLMError

logger = logging.getLogger(__name__)


DEFAULT_MODEL = os.environ.get("DEFAULT_LLM_MODEL", "claude-haiku-4-5-20251001")


class LLMClient:
    """Synchronous wrapper around the Anthropic SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        max_retries: int = 3,
    ):
        if not api_key and not os.environ.get("ANTHROPIC_API_KEY"):
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
        self._client = Anthropic(api_key=api_key or None)
        self.model = model
        self.max_retries = max_retries

    @property
    def client(self):
        """Access the underlying Anthropic SDK client for advanced usage."""
        return self._client

    def generate(
        self,
        system_prompt: str,
        user_content: str | list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> dict:
        """Send a message to Claude and return the response with usage info.

        Args:
            user_content: A single string (wrapped as user message) or a list
                of message dicts (``[{"role": ..., "content": ...}, ...]``).

        Returns:
            dict with keys: text, input_tokens, output_tokens, model
        """
        from anthropic import APIError, APITimeoutError, RateLimitError

        use_model = model or self.model
        if isinstance(user_content, str):
            msgs = [{"role": "user", "content": user_content}]
        else:
            msgs = user_content
        for attempt in range(self.max_retries):
            try:
                response = self._client.messages.create(
                    model=use_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=msgs,
                )
                return {
                    "text": response.content[0].text,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "model": use_model,
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
        model: str | None = None,
    ) -> dict:
        """Multi-turn message call with tool definitions.

        Returns:
            dict with keys: text, tool_calls, stop_reason, input_tokens, output_tokens, model
            tool_calls is a list of dicts with keys: name, input, id
        """
        from anthropic import APIError, APITimeoutError, RateLimitError

        use_model = model or self.model
        for attempt in range(self.max_retries):
            try:
                response = self._client.messages.create(
                    model=use_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=messages,
                    tools=tools,
                )
                text_parts = []
                tool_calls = []
                for block in response.content:
                    if block.type == "text":
                        text_parts.append(block.text)
                    elif block.type == "tool_use":
                        tool_calls.append({
                            "name": block.name,
                            "input": block.input,
                            "id": block.id,
                        })
                return {
                    "text": "\n".join(text_parts),
                    "tool_calls": tool_calls,
                    "stop_reason": response.stop_reason,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "model": use_model,
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

    def stream(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> Iterator[str]:
        """Stream a response, yielding text chunks."""
        from anthropic import APIError, APITimeoutError, RateLimitError

        use_model = model or self.model
        for attempt in range(self.max_retries):
            try:
                with self._client.messages.stream(
                    model=use_model,
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
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        max_retries: int = 3,
    ):
        if not api_key and not os.environ.get("ANTHROPIC_API_KEY"):
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
        self._client = AsyncAnthropic(api_key=api_key or None)
        self.model = model
        self.max_retries = max_retries

    @property
    def client(self):
        """Access the underlying AsyncAnthropic SDK client for advanced usage."""
        return self._client

    async def generate(
        self,
        system_prompt: str,
        user_content: str | list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> dict:
        """Send a message to Claude and return the response with usage info.

        Args:
            user_content: A single string (wrapped as user message) or a list
                of message dicts (``[{"role": ..., "content": ...}, ...]``).
        """
        from anthropic import APIError, APITimeoutError, RateLimitError

        use_model = model or self.model
        if isinstance(user_content, str):
            msgs = [{"role": "user", "content": user_content}]
        else:
            msgs = user_content
        for attempt in range(self.max_retries):
            try:
                response = await self._client.messages.create(
                    model=use_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=msgs,
                )
                return {
                    "text": response.content[0].text,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "model": use_model,
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
        model: str | None = None,
    ) -> dict:
        """Multi-turn message call with tool definitions.

        Returns:
            dict with keys: text, tool_calls, stop_reason, input_tokens, output_tokens, model
        """
        from anthropic import APIError, APITimeoutError, RateLimitError

        use_model = model or self.model
        for attempt in range(self.max_retries):
            try:
                response = await self._client.messages.create(
                    model=use_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=messages,
                    tools=tools,
                )
                text_parts = []
                tool_calls = []
                for block in response.content:
                    if block.type == "text":
                        text_parts.append(block.text)
                    elif block.type == "tool_use":
                        tool_calls.append({
                            "name": block.name,
                            "input": block.input,
                            "id": block.id,
                        })
                return {
                    "text": "\n".join(text_parts),
                    "tool_calls": tool_calls,
                    "stop_reason": response.stop_reason,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "model": use_model,
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

    async def stream(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream a response, yielding text chunks."""
        from anthropic import APIError, APITimeoutError, RateLimitError

        use_model = model or self.model
        for attempt in range(self.max_retries):
            try:
                async with self._client.messages.stream(
                    model=use_model,
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
