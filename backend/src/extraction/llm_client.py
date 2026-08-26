import os
from typing import Protocol, Type, TypeVar
from pydantic import BaseModel
from google import genai
from google.genai import types

T = TypeVar('T', bound=BaseModel)

class LLMClient(Protocol):
    async def extract_structured(self, system_prompt: str, user_prompt: str, output_schema: Type[T]) -> T: ...
    async def generate_text(self, system_prompt: str, user_prompt: str) -> str: ...

class GeminiClient:
    """Gemini Flash implementation"""
    def __init__(self, api_key: str | None = None, model: str = 'gemini-2.5-flash'):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = model
        self.client = genai.Client(api_key=self.api_key)

    async def extract_structured(self, system_prompt: str, user_prompt: str, output_schema: Type[T]) -> T:
        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=output_schema,
                temperature=0.0
            )
        )
        return output_schema.model_validate_json(response.text)

    async def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.0
            )
        )
        return response.text

class MockLLMClient:
    """For testing — returns deterministic responses"""
    async def extract_structured(self, system_prompt: str, user_prompt: str, output_schema: Type[T]) -> T:
        return output_schema.model_construct(
            evidence_type="ACCESS_PROOF",
            events=[],
            entities=[],
            confidence=1.0,
            extraction_notes="mocked"
        ) # type: ignore

    async def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        return "Mock response"
