"""AWS Bedrock API client implementation."""
import os
import json
import logging
from typing import List, Dict, Any, Optional
import aioboto3
from injector import inject

from app.interfaces.anthropic_client_interface import IAnthropicClient

logger = logging.getLogger(__name__)


class BedrockClient(IAnthropicClient):
    """AWS Bedrock API client implementation using Claude models."""
    
    @inject
    def __init__(self):
        """Initialize Bedrock client."""
        self.region = os.getenv("AWS_REGION", "us-west-2")
        self.model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
        
        try:
            # Initialize aioboto3 session for async AWS operations
            self.session = aioboto3.Session()
            logger.info(f"Bedrock client initialized with model: {self.model_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            raise ValueError(f"Failed to initialize Bedrock client: {e}")
    
    async def generate_response(
        self, 
        prompt: str, 
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """Generate a response using AWS Bedrock Claude model."""
        try:
            # Prepare the request body for Claude
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            # Use async context manager to get client and invoke the model
            async with self.session.client('bedrock-runtime', region_name=self.region) as client:
                response = await client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(request_body)
                )
                
                # Parse response
                response_body = json.loads(response['body'].read())
            
            # Extract text from Claude response
            if 'content' in response_body and len(response_body['content']) > 0:
                return response_body['content'][0]['text']
            
            return ""
            
        except Exception as e:
            logger.error(f"Failed to generate response with Bedrock: {e}")
            raise
    
    async def analyze_document(
        self, 
        document_content: str, 
        analysis_type: str = "summary"
    ) -> Dict[str, Any]:
        """Analyze document content using Bedrock Claude model."""
        try:
            prompt = f"""Analyze the following document and provide a {analysis_type}:

{document_content}

Please provide a structured analysis."""
            
            response_text = await self.generate_response(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.3
            )
            
            return {
                "analysis_type": analysis_type,
                "result": response_text
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze document with Bedrock: {e}")
            raise
    
    async def extract_information(
        self, 
        text: str, 
        extraction_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract structured information from text using Bedrock."""
        try:
            schema_str = json.dumps(extraction_schema, indent=2)
            prompt = f"""Extract information from the following text according to this schema:

Schema:
{schema_str}

Text:
{text}

Please return the extracted information as JSON matching the schema."""
            
            response_text = await self.generate_response(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.1
            )
            
            # Try to parse as JSON
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                return {"raw_response": response_text}
            
        except Exception as e:
            logger.error(f"Failed to extract information with Bedrock: {e}")
            raise
    
    async def search_web_with_tools(
        self, 
        query: str, 
        max_searches: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Perform web search using Bedrock (placeholder - Bedrock doesn't have built-in web search).
        
        Note: This method is not implemented as Bedrock doesn't have native web search tools.
        Use Tavily or other search services instead.
        """
        return []

