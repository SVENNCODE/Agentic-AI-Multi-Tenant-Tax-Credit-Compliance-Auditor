from datetime import date
from enum import Enum
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MIN_TAX_YEAR = 2000
MAX_TAX_YEAR = 2100
MAX_MONEY = 100_000_000.0          
MAX_VISA_PERIODS = 20
MAX_EMPLOYERS = 50

Money = Annotated[float, Field(ge=0, le=MAX_MONEY, allow_inf_nan=False)]
DayCount = Annotated[int, Field(ge=0, le=366)]


class VisaType(str, Enum):
    F1 = "F1"
    J1 = "J1"
    M1 = "M1"
    Q1 = "Q1"
    H1B = "H1B"
    OPT = "OPT"
    OTHER = "OTHER"
    NONE = "NONE"


class ResidencyStatus(str, Enum):
    NONRESIDENT_ALIEN = "NONRESIDENT_ALIEN"
    RESIDENT_ALIEN = "RESIDENT_ALIEN"
    DUAL_STATUS = "DUAL_STATUS"
    # Inputs were missing or contradictory (e.g. no entry date, overlapping
    # visa periods of different types).
    UNDETERMINED = "UNDETERMINED"


class FilingStatus(str, Enum):
    SINGLE = "SINGLE"
    MARRIED_FILING_JOINTLY = "MARRIED_FILING_JOINTLY"
    MARRIED_FILING_SEPARATELY = "MARRIED_FILING_SEPARATELY"
    HEAD_OF_HOUSEHOLD = "HEAD_OF_HOUSEHOLD"
    QUALIFYING_SURVIVING_SPOUSE = "QUALIFYING_SURVIVING_SPOUSE"


class EmploymentType(str, Enum):
    W2 = "W2"
    CONTRACTOR_1099 = "CONTRACTOR_1099"
    UNEMPLOYED = "UNEMPLOYED"
    STUDENT_WORKER = "STUDENT_WORKER"


def _blank_to_none(value):
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


class VisaStatusPeriodInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    visa_type: VisaType
    start_date: date
    end_date: Optional[date] = None
    is_exempt_status: bool
    _blank_end = field_validator("end_date", mode="before")(_blank_to_none)

    @model_validator(mode="after")
    def _end_after_start(self):
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class VisaPeriod(BaseModel):
    visa_type: VisaType
    start_date: date
    end_date: Optional[date] = None


class TaxPayerInput(BaseModel):
    tax_year: int = Field(..., description="The calendar year being evaluated (e.g., 2025)")
    citizenship_country: str
    # Optional so the engine can classify a missing entry date as
    # UNDETERMINED instead of crashing
    entry_date: Optional[date] = None
    visa_history: List[VisaPeriod]
    days_present_current_year: int = Field(ge=0, le=366)
    days_present_prior_year: int = Field(ge=0, le=366, default=0)
    days_present_two_years_prior: int = Field(ge=0, le=366, default=0)


class AuditTrailStep(BaseModel):
    rule: str
    passed: bool
    details: str


class ResidencyDetermination(BaseModel):
    status: ResidencyStatus
    is_exempt_individual: bool
    exempt_years_used: int
    spt_weighted_days: float = 0.0
    target_form: str
    applied_treaty_code: Optional[str] = None
    audit_trail: List[AuditTrailStep]


class QuestionnaireInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tax_year: int = Field(ge=MIN_TAX_YEAR, le=MAX_TAX_YEAR)

    # Profile
    state_of_residence: str = Field(pattern=r"^[A-Z]{2}$")
    filing_status: FilingStatus
    citizenship_country: str = Field(pattern=r"^[A-Z]{3}$")
    us_entry_date: date
    current_visa_type: VisaType
    is_fulltime_student: bool
    employment_type: EmploymentType
    spouse_is_us_citizen_or_resident: Optional[bool] = None
    visa_status_periods: List[VisaStatusPeriodInput] = Field(
        max_length=MAX_VISA_PERIODS
    )

    # Substantial Presence Test day counts.
    days_present_current_year: DayCount = 0
    days_present_prior_year: DayCount = 0
    days_present_two_years_prior: DayCount = 0

    # Income
    annual_income: Money
    number_of_employers: int = Field(ge=0, le=MAX_EMPLOYERS)
    scholarship_amount: Money
    tuition_paid: Money
    tuition_paid_to_nj: Optional[bool] = None
    prior_years_aotc_claimed: Optional[int] = Field(default=None, ge=0, le=4)

    # Expense categories
    has_education_expenses: bool
    has_childcare_expenses: bool
    has_medical_expenses: bool
    has_charitable_donations: bool
    has_retirement_contributions: bool
    has_valid_ssn: Optional[bool] = None

    @field_validator("state_of_residence", "citizenship_country", mode="before")
    @classmethod
    def _upper(cls, v):
        return v.strip().upper() if isinstance(v, str) else v

    @model_validator(mode="after")
    def _entry_date_sane(self):
        if self.us_entry_date.year > self.tax_year:
            raise ValueError("us_entry_date cannot be after the tax year")
        return self


class FederalCreditRule(BaseModel):
    tax_year: int
    credit_code: str
    credit_name: str
    max_credit_amount: float
    refundable_percentage: float
    max_refundable_amount: float
    expense_cap: float
    max_years_claimable: Optional[int]
    requires_ssn: bool
    allows_nonresident_aliens: bool
    min_enrollment_status: str
    magi_phaseout_single_start: float
    magi_phaseout_single_end: float
    magi_phaseout_mfj_start: float
    magi_phaseout_mfj_end: float
    notes: Optional[str] = None


class CreditEvaluationResult(BaseModel):
    source_type: str
    rule_code: str
    status: str
    reason: str
    estimated_amount: Optional[float] = None
    # ISO-3166 alpha-3 code for TREATY_BENEFIT rows; None otherwise.
    country_code: Optional[str] = None
