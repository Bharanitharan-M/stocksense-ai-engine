import requests
import urllib.parse
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from typing import Dict, Any

from src.config.settings import settings
from src.models.schemas import RelevanceOutput, GenerationOutput, ValidationOutput, AIAnalysisResponse, DiscoveryOutput
import logging

logger = logging.getLogger(__name__)

# Initialize Gemini Clients for Rotation
clients = []
active_client_index = 0

for i, k in enumerate(settings.GEMINI_API_KEYS):
    try:
        clients.append(genai.Client(api_key=k))
    except Exception as e:
        logger.error(f"Failed to initialize Gemini client for key index {i}: {e}")

# Fallback to default client if clients list is empty
if not clients:
    try:
        clients.append(genai.Client())
    except Exception as e:
        logger.error(f"Fallback Gemini client initialization failed. Error: {e}")

def get_client() -> genai.Client:
    global active_client_index
    if not clients:
        raise ValueError("No Gemini clients initialized.")
    return clients[active_client_index]

def rotate_client():
    global active_client_index
    if not clients:
        return
    old_index = active_client_index
    active_client_index = (active_client_index + 1) % len(clients)
    logger.info(f"Rotated Gemini API Key: index {old_index} -> index {active_client_index}")

def generate_content(contents: str, response_schema: Any, temperature: float = 0.1) -> Any:
    """
    Generates content using the active client and handles key rotation automatically on 429 quota exhaustion.
    """
    global active_client_index
    attempts = 0
    max_attempts = len(clients)
    
    while attempts < max_attempts:
        client = get_client()
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=temperature
                ),
            )
            return response
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower() or "503" in err_msg or "UNAVAILABLE" in err_msg:
                logger.warning(f"Gemini client at index {active_client_index} exhausted or unavailable ({err_msg}). Rotating key...")
                rotate_client()
                attempts += 1
            else:
                logger.error(f"Gemini generation failed: {e}")
                raise e
                
    raise ValueError("All configured Gemini API Keys are exhausted.")

def evaluate_relevance(source_headline: str, source_content: str) -> RelevanceOutput:
    """
    Module 6: Relevance Evaluator.
    Determines if the raw news is a factual financial disclosure and passes legal checks.
    """
    if not clients:
        raise ValueError("Gemini clients are not initialized.")
        
    prompt = f"""
    You are a strict financial compliance AI for StockSense AI.
    Evaluate the following financial news item to determine if it is relevant and safe.
    
    Headline: {source_headline}
    Content: {source_content}
    
    Rules:
    1. is_relevant: Must be True ONLY IF the text is a factual financial disclosure, corporate action, or verified market event. False if it is a rumor, opinion piece, or political news.
    2. legal_pass: Must be True ONLY IF the text contains no direct investment advice (e.g., "Buy this stock now").
    3. algorithmic_pass: Must be True ONLY IF specific companies or broad macroeconomic data are mentioned.
    4. relevance_outcome: "RELEVANT" if all three above are True. Otherwise "NOT_RELEVANT".
    """
    
    response = generate_content(
        contents=prompt,
        response_schema=RelevanceOutput,
        temperature=0.1
    )
    
    result = RelevanceOutput.model_validate_json(response.text)
    logger.info(f"Relevance outcome: {result.relevance_outcome} | Legal Pass: {result.legal_pass}")
    return result

def generate_insights(source_headline: str, source_content: str) -> GenerationOutput:
    """
    Module 7: Generation Engine.
    Extracts the 3-tier structure (5-sec summary and 30-sec breakdown).
    """
    if not clients:
        raise ValueError("Gemini clients are not initialized.")
        
    prompt = f"""
    You are an expert financial analyst AI for StockSense AI.
    Create a highly scannable, noise-free summary of the following financial event.
    
    Headline: {source_headline}
    Content: {source_content}
    
    Rules:
    1. summary_5_sec: A bold, highly scannable headline summarizing the most critical impact of the event (max 150 chars).
    2. breakdown_30_sec: A descriptive paragraph explaining the core details, financial metrics, and immediate market context (max 500 chars).
    3. ticker: The uppercase stock symbol/ticker of the main company mentioned (NSE India ticker preferred if applicable, e.g. RELIANCE, TCS, HDFCBANK, TATAMOTORS, INFY). If it is a general macroeconomic news or broad market event without a single main company, output 'GENERAL'.
    4. sector: The industry sector of the main company (e.g. Energy, IT, Financial Services, Automobile, Consumer Goods, Telecom, Metal). If ticker is 'GENERAL', output 'Macro'.
    5. DO NOT include any stock price predictions or investment advice.
    """
    
    response = generate_content(
        contents=prompt,
        response_schema=GenerationOutput,
        temperature=0.3
    )
    
    result = GenerationOutput.model_validate_json(response.text)
    logger.info("Insight generation complete.")
    return result

def validate_confidence(generation_output: GenerationOutput) -> ValidationOutput:
    """
    Module 9: Safety & Confidence Validator.
    Acts as a guardrail to review the generated output.
    """
    if not clients:
        raise ValueError("Gemini clients are not initialized.")
        
    prompt = f"""
    You are a strict compliance auditor AI for StockSense AI.
    Review the following generated financial summary.
    
    5-Second Summary: {generation_output.summary_5_sec}
    30-Second Breakdown: {generation_output.breakdown_30_sec}
    
    Rules:
    1. safety_status: Output "FAIL" if the text predicts future stock prices, tells users to buy/sell, or sounds like financial advice. Otherwise output "PASS".
    2. confidence_score: Assign a score from 0 to 100 representing how factual, objective, and well-written the summary is.
    3. status: Output "APPROVED" if confidence_score >= 85 and safety_status is "PASS". Output "LOW_CONFIDENCE" if confidence_score < 85. Output "REJECTED" if safety_status is "FAIL".
    """
    
    response = generate_content(
        contents=prompt,
        response_schema=ValidationOutput,
        temperature=0.1
    )
    
    result = ValidationOutput.model_validate_json(response.text)
    logger.info(f"Validation complete. Status: {result.status} | Confidence: {result.confidence_score} | Safety: {result.safety_status}")
    return result

def run_full_pipeline(transaction_id: str, source_headline: str, source_content: str) -> AIAnalysisResponse:
    """
    Executes the full pipeline: Relevance -> (if relevant) Generation -> Validation.
    """
    logger.info(f"Starting full pipeline for transaction: {transaction_id}")
    
    # 1. Check Relevance
    relevance_result = evaluate_relevance(source_headline, source_content)
    
    if relevance_result.relevance_outcome == "NOT_RELEVANT":
        logger.warning(f"Transaction {transaction_id} rejected during relevance check.")
        return AIAnalysisResponse(
            transaction_id=transaction_id,
            relevance_outcome="NOT_RELEVANT",
            relevance_metrics=relevance_result
        )
        
    # 2. Generate Insights
    generation_result = generate_insights(source_headline, source_content)
    
    # 3. Validate Confidence
    validation_result = validate_confidence(generation_result)
    
    logger.info(f"Full pipeline successful for transaction: {transaction_id}")
    
    return AIAnalysisResponse(
        transaction_id=transaction_id,
        relevance_outcome="RELEVANT",
        relevance_metrics=relevance_result,
        ai_analysis=generation_result,
        metrics=validation_result
    )

def run_discovery_pipeline(transaction_id: str, query: str) -> DiscoveryOutput:
    """
    On-Demand Search Grounding.
    Searches the web via DuckDuckGo HTML search for live, recent, factual financial news about `query`.
    Then uses Gemini to generate structured DiscoveryOutput.
    """
    if not clients:
        raise ValueError("Gemini clients are not initialized.")

    logger.info(f"Starting discovery pipeline for query: '{query}' [Transaction: {transaction_id}]")

    # 1. Fetch live web search results from Google News RSS
    search_context = ""
    try:
        import urllib.request
        import xml.etree.ElementTree as ET
        
        search_query = query if "news" in query.lower() or "stock" in query.lower() else f"{query} stock news"
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(search_query)}"
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            items = root.findall('.//item')
            search_items = []
            for item in items[:6]:
                title = item.find('title').text if item.find('title') is not None else "No Title"
                link = item.find('link').text if item.find('link') is not None else ""
                date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                search_items.append(f"Title: {title}\nDate: {date}\nLink: {link}\n")
            search_context = "\n---\n".join(search_items)
    except Exception as e:
        logger.error(f"Failed to fetch Google News RSS: {e}")

    if not search_context.strip():
        logger.warning(f"No search results retrieved for query: '{query}'")
        return DiscoveryOutput(relevance_outcome="NOT_RELEVANT")

    # 2. Query Gemini model using the search context
    prompt = f"""
    You are an expert financial analyst AI for StockSense AI.
    We searched the web for "{query}" and retrieved the following live search results:
    
    {search_context}
    
    Analyze the search results. Verify if there is any recent, factual financial news, corporate earnings disclosures, or market events matching the query.
    
    If there is no recent, factual financial news, corporate disclosures, or market events for this query, set relevance_outcome to "NOT_RELEVANT".
    
    Otherwise, if relevant factual financial news is found:
    1. headline: Formulate a clean, factual headline of the main event (max 200 chars).
    2. summary_5_sec: A bold, highly scannable headline summarizing the most critical impact of the event (max 150 chars).
    3. breakdown_30_sec: A descriptive paragraph explaining the core details, financial metrics, and immediate market context (max 500 chars).
    4. ticker: The uppercase stock symbol/ticker of the main company mentioned (NSE India ticker preferred if applicable, e.g. RELIANCE, TCS, HDFCBANK, TATASTEEL). If it is a general macroeconomic news or market-wide event, use 'GENERAL'.
    5. sector: The industry sector of the main company (e.g. Energy, IT, Financial Services, Automobile, Consumer Goods, Telecom, Metal). If ticker is 'GENERAL', use 'Macro'.
    6. source_url: The exact link URL of the specific search result that you used to extract this information (from the Link fields in the results context).
    7. relevance_outcome: Set to "RELEVANT".
    """

    response = generate_content(
        contents=prompt,
        response_schema=DiscoveryOutput,
        temperature=0.2
    )

    result = DiscoveryOutput.model_validate_json(response.text)
    logger.info(f"Discovery outcome: {result.relevance_outcome} | Ticker: {result.ticker} | Sector: {result.sector}")
    return result
