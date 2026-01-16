"""
PPT Slide Data Models
=====================
Pydantic models matching Template.pptx placeholders for slide generation.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class ManagementMember(BaseModel):
    """A member of the management team."""
    name: str = Field(..., description="Full name of the executive")
    position: str = Field(..., description="Job title/position")
    bio: str = Field(..., description="Career summary and background")


class Shareholder(BaseModel):
    """A shareholder in the ownership structure."""
    name: str = Field(..., description="Name of shareholder/investor")
    ownership_percentage: str = Field(..., description="Ownership % or 'n/d' if not disclosed")


class SlideData(BaseModel):
    """
    Complete data structure for PPT slide generation.
    Field names match Template.pptx placeholders exactly.
    """
    # Title section
    COMPANY_NAME: str = Field(..., description="Company name for title")
    COUNTRY: str = Field(..., description="Country/region of operation")
    
    # Content sections
    BACKGROUND_SUMMARY: str = Field(..., description="Background bullet points, separated by newlines with bullet markers")
    KEY_PRODUCTS: str = Field(..., description="Key products and services description")
    
    # Statistics header
    Unit: str = Field(default="USDm", description="Unit for statistics (e.g., USDm)")
    year: str = Field(default="2025", description="Year for statistics")
    
    # Individual metric values
    BORROWERS_VALUE: str = Field(..., description="Number of borrowers/customers served")
    EMPLOYEES_VALUE: str = Field(..., description="Number of employees")
    OUTSTANDING_VALUE: str = Field(..., description="Loan outstanding amount")
    PAR_VALUE: str = Field(default="n/d", description="PAR > 30 value or 'n/d'")
    DISBURSALS_VALUE: str = Field(..., description="Total disbursals amount")
    EQUITY_VALUE: str = Field(default="n/d", description="Equity amount or 'n/d'")
    NET_INCOME_VALUE: str = Field(default="n/d", description="Net income or 'n/d'")
    CREDIT_RATING_VALUE: str = Field(default="n/d", description="Credit rating or 'n/d'")
    
    # Table data
    TABLE_MANAGEMENT: List[ManagementMember] = Field(default_factory=list, description="List of management team members")
    TABLE_SHAREHOLDERS: List[Shareholder] = Field(default_factory=list, description="List of shareholders")
