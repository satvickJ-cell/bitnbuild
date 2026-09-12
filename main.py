import os
import shutil
import tempfile
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException, Body, status
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from schema import ProcessPDFResponse, WardBudgetData, EvaluationResult, DashboardMetrics
from extractor import extract_ward_data
from evaluator import evaluate_ward_data
from action_agent import draft_rti_application

load_dotenv()

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("civic_backend")

app = FastAPI(
    title="Civic Transparency Agentic AI Backend API",
    description="Backend orchestration API for municipal budget extraction, civic rule evaluation, and RTI drafting.",
    version="1.0.0"
)

# Enable CORS for external frontends and direct file opens
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Serve index.html at root "/"
@app.get("/", include_in_schema=False)
async def serve_frontend():
    frontend_path = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
    # If index.html is in the root directory instead, just use: "index.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    elif os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Frontend file index.html not found"}



@app.get("/health", tags=["Health Check"])
async def health():
    return {"status": "healthy"}


@app.get("/sample_pdf", tags=["Orchestration"])
async def get_sample_pdf():
    """Returns the sample BBMP budget circular PDF."""
    sample_path = os.path.join(os.path.dirname(__file__), "test_docs", "bbmp_budget_circular_2025 - Sheet1.pdf")
    if os.path.exists(sample_path):
        return FileResponse(
            sample_path, 
            media_type="application/pdf", 
            filename="bbmp_budget_circular_2025.pdf"
        )
    raise HTTPException(status_code=404, detail="Sample PDF not found.")


@app.post("/sample_audit", response_model=ProcessPDFResponse, tags=["Orchestration"])
async def run_sample_audit():
    """Runs the full orchestration pipeline on the sample Ward 150 BBMP circular."""
    sample_path = os.path.join(os.path.dirname(__file__), "test_docs", "bbmp_budget_circular_2025 - Sheet1.pdf")
    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail="Sample PDF not found on server.")
    
    extracted_data = extract_ward_data(sample_path)
    evaluation_dict = evaluate_ward_data(extracted_data)
    evaluation_result = EvaluationResult.model_validate(evaluation_dict)
    dashboard_metrics = DashboardMetrics.model_validate(evaluation_dict)
    rti_draft_text = draft_rti_application(extracted_data, evaluation_dict)

    return ProcessPDFResponse(
        extracted_data=extracted_data,
        evaluation=evaluation_result,
        validation_logs=evaluation_result,
        dashboard_metrics=dashboard_metrics,
        rti_draft=rti_draft_text,
        final_drafted_rti=rti_draft_text
    )



@app.post("/process_pdf", response_model=ProcessPDFResponse, tags=["Orchestration"])
async def process_pdf(file: UploadFile = File(...)):
    """
    Accepts a municipal budget PDF upload, extracts structured ward data using Gemini Files API,
    evaluates rule conditions, and autonomously drafts an RTI application if violations are flagged.
    """
    filename = file.filename or "uploaded_document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Please upload a valid PDF document."
        )

    logger.info(f"Received file upload: {filename} ({file.content_type})")

    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, filename)

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"Saved uploaded PDF to temporary file: {temp_file_path}")

        # Step 1: Extract structured data via Gemini Files API & Structured Outputs
        logger.info("Executing Step 1: Extracting structured data from PDF via Gemini Files API...")
        try:
            extracted_data: WardBudgetData = extract_ward_data(temp_file_path)
        except Exception as e:
            logger.error(f"Error during Step 1 extraction: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to extract structured data from PDF: {str(e)}"
            )

        # Step 2: Evaluate extracted data against deterministic rules
        logger.info("Executing Step 2: Evaluating extracted data against civic threshold rules...")
        try:
            evaluation_dict = evaluate_ward_data(extracted_data)
            evaluation_result = EvaluationResult.model_validate(evaluation_dict)
            dashboard_metrics = DashboardMetrics.model_validate(evaluation_dict)
        except Exception as e:
            logger.error(f"Error during Step 2 evaluation: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to evaluate extracted data: {str(e)}"
            )

        # Step 3: Action Agent - Draft RTI application if flag is triggered
        logger.info("Executing Step 3: Drafting RTI Application via Gemini Action Agent...")
        try:
            rti_draft_text = draft_rti_application(extracted_data, evaluation_dict)
        except Exception as e:
            logger.error(f"Error during Step 3 RTI drafting: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate RTI draft: {str(e)}"
            )

        logger.info("Successfully completed PDF orchestration pipeline.")

        return ProcessPDFResponse(
            extracted_data=extracted_data,
            evaluation=evaluation_result,
            validation_logs=evaluation_result,
            dashboard_metrics=dashboard_metrics,
            rti_draft=rti_draft_text,
            final_drafted_rti=rti_draft_text
        )

    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.info("Cleaned up local temporary directory.")


@app.post("/process_json", response_model=ProcessPDFResponse, tags=["Orchestration"])
async def process_json(data: WardBudgetData = Body(...)):
    """
    Accepts pre-extracted JSON data directly, evaluates rule conditions (Step 2),
    and autonomously drafts an RTI application if violations are flagged (Step 3).
    """
    logger.info(f"Received JSON payload for ward {data.ward_number}")

    # Step 2: Evaluate extracted data against deterministic rules
    evaluation_dict = evaluate_ward_data(data)
    evaluation_result = EvaluationResult.model_validate(evaluation_dict)
    dashboard_metrics = DashboardMetrics.model_validate(evaluation_dict)

    # Step 3: Action Agent - Draft RTI application if flag is triggered
    try:
        rti_draft_text = draft_rti_application(data, evaluation_dict)
    except Exception as e:
        logger.error(f"Error during RTI drafting: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate RTI draft: {str(e)}"
        )

    return ProcessPDFResponse(
        extracted_data=data,
        evaluation=evaluation_result,
        validation_logs=evaluation_result,
        dashboard_metrics=dashboard_metrics,
        rti_draft=rti_draft_text,
        final_drafted_rti=rti_draft_text
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
