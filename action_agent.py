import os
import logging
from typing import Union, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from google import genai

from schema import WardBudgetData
from extractor import get_genai_client, DEFAULT_MODEL, FALLBACK_MODELS

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "rti_template.txt")

def load_rti_template(template_path: str = DEFAULT_TEMPLATE_PATH) -> str:
    """Load template text from rti_template.txt."""
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"RTI template file not found at {template_path}")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

def draft_rti_application(
    extracted_data: Union[WardBudgetData, Dict[str, Any]],
    evaluation_result: Dict[str, Any],
    template_path: str = DEFAULT_TEMPLATE_PATH,
    model_name: str = DEFAULT_MODEL
) -> str:
    """
    Takes plain_english_reason and extracted data, reads rti_template.txt, and 
    uses Gemini model to accurately fill in the template placeholders.

    Args:
        extracted_data: WardBudgetData object or dictionary of extracted fields.
        evaluation_result: Dict containing 'flag_triggered' and 'plain_english_reason'.
        template_path: Path to rti_template.txt.
        model_name: Gemini model identifier.

    Returns:
        str: Drafted RTI application ready for filing, or compliance notification.
    """
    flag_triggered = evaluation_result.get("flag_triggered", False)
    reason = evaluation_result.get("plain_english_reason", "")

    if not flag_triggered:
        return (
            "NO_RTI_REQUIRED: Ward drainage allocation data fully complies with all civic standards "
            "and threshold rules. No Right to Information application filing is necessary.\n\n"
            f"Compliance Details:\n{reason}"
        )

    if isinstance(extracted_data, WardBudgetData):
        data_dict = extracted_data.model_dump()
    elif isinstance(extracted_data, dict):
        data_dict = extracted_data
    else:
        data_dict = {}

    raw_template = load_rti_template(template_path)
    client = get_genai_client()

    current_date_str = datetime.now().strftime("%d %B %Y")

    amount_this_year = float(data_dict.get('amount_this_year') or 0.0)
    amount_last_year = float(data_dict.get('amount_last_year') or 0.0)

    prompt = f"""
You are an expert civic transparency legal draft assistant specializing in Right to Information (RTI) Act 2005 applications in India.

Task:
Fill in the placeholders in the provided RTI Template using the extracted ward data and evaluation findings below.

RTI Template:
---
{raw_template}
---

Extracted Ward Data:
- Ward Number: {data_dict.get('ward_number', 'N/A')}
- Budget Head: {data_dict.get('budget_head', 'N/A')}
- Current Year Budget Amount: ₹{amount_this_year:,.2f}
- Previous Year Budget Amount: ₹{amount_last_year:,.2f}
- Total Drain Length: {data_dict.get('drain_length_km', 'N/A')} km
- Zone Classification: {data_dict.get('zone_new', 'N/A')}
- Stated Road Width: {data_dict.get('stated_road_width', 'N/A')} meters

Evaluation Violation Findings (DISCREPANCY_DETAILS):
{reason}

Current Date: {current_date_str}

Instructions:
1. Replace `[WARD_NUMBER]` with the exact ward number.
2. Replace `[BUDGET_HEAD]` with the exact budget head code/description.
3. Replace `[DISCREPANCY_DETAILS]` with a clear, well-structured, legal bullet point summary of the exact violation findings provided above.
4. Replace `[CURRENT_DATE]` with '{current_date_str}'.
5. Ensure the final document is formal, highly legalistic, grammatically perfect, and ready to print or submit under the RTI Act 2005.
6. Return ONLY the finalized text of the completed RTI application.
"""

    logger.info("Generating RTI Application draft via Gemini API...")
    models_to_try = [model_name] + [m for m in FALLBACK_MODELS if m != model_name]
    last_exception = None
    response = None

    for target_model in models_to_try:
        try:
            response = client.models.generate_content(
                model=target_model,
                contents=prompt
            )
            if response and response.text:
                break
        except Exception as e:
            logger.warning(f"RTI draft generation failed with model {target_model}: {e}")
            last_exception = e

    if response and response.text:
        return response.text.strip()
    
    raise ValueError(f"Failed to generate RTI draft across models: {last_exception}")


def draft_rti(plain_english_reason: str, extracted_data: Dict[str, Any] = None) -> str:
    """Alternative signature taking plain_english_reason directly."""
    eval_result = {
        "flag_triggered": True,
        "plain_english_reason": plain_english_reason
    }
    return draft_rti_application(extracted_data or {}, eval_result)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sample_data = {
        "ward_number": 42,
        "budget_head": "2217-01-101 Drainage Infrastructure",
        "amount_this_year": 1200000.0,
        "amount_last_year": 3800000.0,
        "drain_length_km": 10.0,
        "zone_new": "Commercial South",
        "stated_road_width": 9.5
    }
    sample_eval = {
        "flag_triggered": True,
        "plain_english_reason": "Violation 1: Allocated drainage budget per km (₹120,000.00/km) is below minimum threshold of ₹150,000.00/km | Violation 2: Current allocation of ₹1,200,000.00 is 64.7% below historical ward average baseline | Violation 3: Stated road width (9.5m) in commercial zone fails minimum 12m standard."
    }
    draft = draft_rti_application(sample_data, sample_eval)
    print("Drafted RTI Application:")
    print("=" * 60)
    print(draft)
