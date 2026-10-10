import asyncio
import pytest
from app.config import Settings
from app.llm import LLMError, call_tool
from app.query_parser import QueryParserError, parse_query
from app.resumes import ResumeExtraction

def test_paid_models_are_rejected_before_any_network_call():
    settings=Settings(openrouter_api_key='fixture',openrouter_model='paid/model')
    with pytest.raises(QueryParserError,match='Only free'):
        asyncio.run(parse_query('java jobs',settings=settings))
    with pytest.raises(LLMError,match='Only free'):
        asyncio.run(call_tool(ResumeExtraction,system='Extract',data={},settings=settings))
