from pydantic import BaseModel, Field
from typing import Optional

class WardBudgetData(BaseModel):
    """Pydantic schema for structured extraction of ward drainage allocation data from municipal PDF documents."""
    ward_number: int = Field(..., description="The municipal ward number (integer)")
    budget_head: str = Field(..., description="The budget head code or description for drainage works")
    amount_this_year: float = Field(..., description="Allocated budget amount for the current financial year in INR")
    amount_last_year: float = Field(..., description="Allocated or spent budget amount for the previous financial year in INR")
    drain_length_km: float = Field(..., description="Total length of stormwater/sewage drains in the ward in kilometers")
    zone_new: str = Field(..., description="Zone classification of the ward (e.g., Commercial, Residential, Industrial, Mixed)")
    stated_road_width: float = Field(..., description="Stated or average road width in the ward in meters")


class DashboardMetrics(BaseModel):
    """Civic Negligence Index & unit maintenance metrics for frontend dashboards."""
    negligence_score: float = Field(0.0, description="Composite Civic Negligence Score (0 to 100)")
    risk_level: str = Field("COMPLIANT", description="Risk Category (CRITICAL RISK, HIGH RISK, MODERATE RISK, COMPLIANT)")
    risk_color: str = Field("#22c55e", description="Color code for risk badge (#ef4444, #f97316, #eab308, #22c55e)")
    cost_per_km: float = Field(0.0, description="Allocated budget per kilometer in INR")
    cost_per_km_formatted: str = Field("₹0/km", description="Formatted cost per km string")
    statutory_norm_formatted: str = Field("₹1,50,000/km", description="Statutory benchmark standard string")
    yoy_cut_percentage: str = Field("0.0%", description="Formatted year-on-year budget cut percentage")
    yoy_cut_ratio: Optional[float] = Field(0.0, description="Year-on-year budget cut ratio")
    norm_deficit_ratio: Optional[float] = Field(0.0, description="Statutory budget per km deficit ratio")


class EvaluationResult(BaseModel):
    """Result of deterministic rule evaluation."""
    flag_triggered: bool = Field(..., description="True if any civic rule violation or anomaly was detected, False otherwise")
    plain_english_reason: str = Field(..., description="Detailed natural language explanation of the triggered flags or pass status")
    negligence_score: Optional[float] = Field(0.0, description="Composite risk score from 0 to 100 based on YoY cut severity and statutory shortfall")
    risk_level: Optional[str] = Field("COMPLIANT", description="Categorical risk assessment (e.g., CRITICAL RISK, HIGH RISK, MODERATE RISK, COMPLIANT)")
    risk_color: Optional[str] = Field("#22c55e", description="Hex color for risk indicator")
    cost_per_km: Optional[float] = Field(0.0, description="Allocated drainage budget per kilometer in INR")
    cost_per_km_formatted: Optional[str] = Field("₹0/km", description="Formatted budget per km string")
    statutory_norm_formatted: Optional[str] = Field("₹1,50,000/km", description="Statutory benchmark standard string")
    yoy_cut_percentage: Optional[str] = Field("0.0%", description="Formatted year-on-year budget cut percentage")
    yoy_cut_ratio: Optional[float] = Field(0.0, description="Year-on-year budget cut ratio")
    norm_deficit_ratio: Optional[float] = Field(0.0, description="Statutory budget per km deficit ratio")


class ProcessPDFResponse(BaseModel):
    """Response payload for /process_pdf endpoint."""
    extracted_data: WardBudgetData
    evaluation: EvaluationResult
    validation_logs: EvaluationResult = Field(..., description="Alias/copy of evaluation result logs")
    dashboard_metrics: Optional[DashboardMetrics] = Field(None, description="Pre-computed dashboard metric cards")
    rti_draft: str = Field("", description="Drafted RTI application text if flag is triggered, or status note if compliant")
    final_drafted_rti: str = Field("", description="Alias for rti_draft")

