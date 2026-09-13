import os
import json
import logging
from typing import Union, Dict, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types

from schema import WardBudgetData

load_dotenv()

logger = logging.getLogger(__name__)

# Primary and fallback Gemini models (using active supported endpoints)
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3.7-flash", "gemini-flash-latest", "gemini-3.1-flash-lite", "gemini-3.6-flash"]

def get_genai_client() -> genai.Client:
    """Initialize and return standard google-genai Client."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Please configure .env file.")
    return genai.Client(api_key=api_key)

def extract_ward_data(file_path: str, model_name: str = DEFAULT_MODEL) -> WardBudgetData:
    """
    Uploads a PDF file using the Gemini Files API and extracts structured data 
    matching the WardBudgetData Pydantic schema using Gemini Structured Outputs.

    Args:
        file_path (str): Local path to the municipal budget PDF file.
        model_name (str): Gemini model identifier (default: gemini-2.0-flash).

    Returns:
        WardBudgetData: Pydantic instance containing structured extracted fields.
    """
    client = get_genai_client()

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Specified PDF file path does not exist: {file_path}")

    logger.info(f"Uploading PDF file to Gemini Files API: {file_path}")
    uploaded_file = client.files.upload(file=file_path)
    logger.info(f"File uploaded successfully. Remote File Name: {uploaded_file.name}")

    try:
        prompt = (
            "Analyze the attached municipal budget document carefully. Extract the ward drainage allocation details, "
            "including ward number, budget head description/code, budget amounts for this year and last year in INR, "
            "total length of drains in kilometers, new zone classification, and stated road width in meters. "
            "Return the extracted values strictly adhering to the specified schema."
        )

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=WardBudgetData
        )

        models_to_try = [model_name] + [m for m in FALLBACK_MODELS if m != model_name]
        last_exception = None
        response = None

        for target_model in models_to_try:
            try:
                logger.info(f"Sending extraction request to Gemini model ({target_model})...")
                response = client.models.generate_content(
                    model=target_model,
                    contents=[uploaded_file, prompt],
                    config=config
                )
                if response and (hasattr(response, "parsed") or response.text):
                    break
            except Exception as e:
                logger.warning(f"Extraction failed with model {target_model}: {e}")
                last_exception = e

        if not response:
            raise ValueError(f"Failed to extract data across models: {last_exception}")

        if hasattr(response, "parsed") and response.parsed is not None:
            if isinstance(response.parsed, WardBudgetData):
                return response.parsed
            elif isinstance(response.parsed, dict):
                return WardBudgetData.model_validate(response.parsed)

        if response.text:
            cleaned_text = response.text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text.replace("```json", "", 1).rstrip("` \n")
            elif cleaned_text.startswith("```"):
                cleaned_text = cleaned_text.replace("```", "", 1).rstrip("` \n")
            return WardBudgetData.model_validate_json(cleaned_text)

        raise ValueError("Failed to extract data: Empty response received from Gemini model.")

    finally:
        # Clean up uploaded file from Gemini cloud storage
        try:
            client.files.delete(name=uploaded_file.name)
            logger.info(f"Cleaned up remote file: {uploaded_file.name}")
        except Exception as e:
            logger.warning(f"Could not delete remote file {uploaded_file.name}: {e}")


def extract_ward_data_dict(file_path: str, model_name: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """Helper function to return extracted data as a plain Python dictionary."""
    ward_data = extract_ward_data(file_path, model_name=model_name)
    return ward_data.model_dump()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) > 1:
        data = extract_ward_data(sys.argv[1])
        print("Extracted Ward Data:")
        print(data.model_dump_json(indent=2))
    else:
        print("Usage: python extractor.py <path_to_pdf>")
