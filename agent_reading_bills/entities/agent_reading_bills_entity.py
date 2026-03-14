"""Agent Reading Bills Entity - Specialized entity for bill reading with configuration and prompts."""

from typing import List
from .base_entity import BaseEntity


class AgentReadingBillsEntity(BaseEntity):
    """
    Specialized entity for the bill reading agent.
    
    Contains configuration constants, supported bill types, redaction fields,
    and LLM prompt templates for extracting service information from bills.
    
    Class Constants:
        OPENAI_MODEL (str): GPT-4 Vision model identifier
        OPENAI_API_ENDPOINT (str): OpenAI API endpoint URL
        BILL_TYPES (list): Supported bill categories
        REDACTION_FIELDS (list): Personal information fields to redact from output
    
    Instance Attributes:
        supported_bill_types (list): Bill types this service instance supports
        redaction_fields (list): Personal info fields to redact
        version (str): Version of the bill reader model
    """
    
    # Configuration Constants
    OPENAI_MODEL = "gpt-4o"
    OPENAI_API_ENDPOINT = "https://api.openai.com/v1/chat/completions"
    
    BILL_TYPES = [
        "utility",           # Electric, water, gas, internet
        "telecom",           # Phone, mobile, broadband
        "insurance",         # Health, auto, home, life
        "credit_card",       # Credit card statements
        "other"              # Any other bill type
    ]
    
    REDACTION_FIELDS = [
        # Names
        "full_name", "first_name", "last_name", "middle_name",
        
        # Address Information
        "address", "street_address", "city", "state", "zip_code", "postal_code",
        "country", "apartment_number", "suite_number", "unit_number",
        
        # Contact Information
        "phone_number", "mobile_number", "email_address", "email", "phone",
        "fax_number", "telephone",
        
        # Identification Numbers
        "ssn", "social_security_number", "tax_id", "ein", "tin",
        "passport_number", "driver_license_number", "license_number",
        "customer_id", "account_number", "account_id", "member_id",
        
        # Financial Information
        "credit_card_number", "card_number", "bank_account_number",
        "routing_number", "invoice_number",
        
        # Personal Details
        "date_of_birth", "birth_date", "dob", "age",
        
        # Dates
        "service_start_date", "service_end_date", "billing_date",
        "payment_due_date", "statement_date",
        
        # Employment
        "employer", "occupation", "employment_id",
        
        # Other
        "ip_address", "website", "ip", "username", "password", "pin", "secret"
    ]
    
    def __init__(
        self,
        api_key: str = None,
        model_name: str = None,
        version: str = "1.0.0",
        supported_bill_types: List[str] = None,
        redaction_fields: List[str] = None
    ):
        """
        Initialize the agent reading bills entity.
        
        Args:
            api_key (str, optional): OpenAI API key
            model_name (str, optional): Model name (defaults to OPENAI_MODEL)
            version (str): Version of the bill reader (default: 1.0.0)
            supported_bill_types (list, optional): Override supported bill types (defaults to all)
            redaction_fields (list, optional): Override redaction fields (defaults to all)
        """
        model_name = model_name or self.OPENAI_MODEL
        super().__init__(api_key=api_key, model_name=model_name)
        
        self._version = version
        self._supported_bill_types = supported_bill_types or self.BILL_TYPES.copy()
        self._redaction_fields = redaction_fields or self.REDACTION_FIELDS.copy()
    
    @property
    def version(self) -> str:
        """Get the bill reader version."""
        return self._version
    
    @property
    def supported_bill_types(self) -> List[str]:
        """Get the list of supported bill types."""
        return self._supported_bill_types
    
    @property
    def redaction_fields(self) -> List[str]:
        """Get the list of personal information fields to redact."""
        return self._redaction_fields
    
    def get_extraction_prompt(self) -> str:
        """
        Get the LLM prompt for extracting ALL financial information from ANY insurance bill.
        Handles medical, dental, pharmacy, auto, homeowners, vision, and all other bill types.
        
        Returns:
            str: Comprehensive prompt for extracting maximum financial detail
        """
        supported_types = ", ".join(self.supported_bill_types)
        return f"""You are an expert insurance bill analyzer. MISSION: Extract EVERY financial detail from this bill.
Bill could be: Medical, Dental, Pharmacy, Auto, Homeowners, Vision, Property, Premium - ANY insurance claim type.

KEY RULE: Capture ALL financial information. Ignore ONLY personal identifiers (names, SSN, addresses, phone, DOB).
MASK these: Full names, street addresses, phone numbers, SSN, birth dates
CAPTURE these: Invoice #, Claim #, Policy #, Service codes, ALL amounts, dates (service/billing/claim), explanations

=== CLAIM IDENTIFICATION ===
1. Bill/Claim Type (Medical, Dental, Auto, Homeowners, Pharmacy, Vision, Premium, etc.)
2. Claim Status (Paid, Denied, Pending, Partial)
3. Invoice Number, Claim Number, Policy Number, Contract Number
4. Claim submitted date, processed date, EOB date
5. Authorization number, EOB number

=== SERVICE INFORMATION ===
1. Service dates: From [MASKED] to [MASKED] (or month/year if available)
2. Billing period description
3. Diagnosis codes: ALL codes shown with descriptions and whether primary
4. Service location/place of service code

=== MEMBER & PLAN INFORMATION ===
1. Plan name and type (PPO, HMO, Health, Auto, Homeowners, etc.)
2. Group number (mask any identifiers)
3. Member relationship (Self, Spouse, Child, Parent, etc.)
4. Coverage type (for auto/property: Liability, Collision, Comprehensive, Fire, Theft, etc.)

=== PROVIDER/FACILITY INFORMATION ===
1. Provider name
2. Provider type (Hospital, Clinic, Lab, Dentist, Auto Body, Repair Service, etc.)
3. Network status (In-Network, Out-of-Network, Preferred, Non-Preferred)
4. Place of service code / location type
5. Facility name if different from provider

=== PROCEDURE/SERVICE DETAILS (CRITICAL) ===
For EACH procedure/service line, extract ALL visible columns:
- Code: CPT, service code, procedure code
- Description: What service/repair was done
- Units: How many (sessions, visits, items, hours, etc.)
- Billed Amount: What provider charged
- Allowed Amount: What insurance allows
- Adjustment Amount: Discount applied
- Deductible Applied: Deductible for this line
- Copay: Patient copay for this line
- Coinsurance: Coinsurance amount for this line
- Patient Responsibility: Total patient owes for this line
- Service Date: Date service occurred (if per-line info)

=== PAYMENT/FINANCIAL BREAKDOWN (CRITICAL) ===
Extract EVERY line item from payment summary section:
- Total Billed / Total Amount Charged
- Contractual Adjustments (amount + code like CO-45 if shown)
- Allowed Amount / Eligible Amount
- Deductible Applied (total)
- Copay (total)
- Coinsurance % and Amount (total)
- Insurance Paid / Benefits Paid / Plan Paid
- Patient Responsibility / Balance Due
- Amount Patient Actually Paid
- Remaining Balance
- Any other financial lines shown

=== CLAIM DETERMINATION & REASONS ===
- If Paid: Percent covered, approval amount
- If Denied: Denial reason code and explanation
- If Pending: Expected decision date, what's needed
- Appeal rights and deadline
- Adjustment codes and their meanings

=== PAYMENT METHOD & STATUS ===
- Payment date
- Payment method (Check, EFT, Credit Card, Patient Portal)
- Check number if applicable
- Payment amount
- Outstanding balance
- Payment terms, due date

=== SPECIAL INFORMATION ===
For Medical: Medical necessity, prior auth, referral info
For Dental: Treatment plan, ortho coverage
For Auto: Vehicle damage, repair shop details, parts used
For Property: Damage type, repair estimates, multiple items
Any special conditions, exclusions, or notes

=== OUTPUT FORMAT (VALID JSON ONLY) ===
{{
  "service_information": "bill description",
  "service_type": "{supported_types}",
  "bill_type": "specific type on bill",
  "bill_status": "Paid/Denied/Pending/Partial",
  "provider": "provider name",
  
  "claim_information": {{
    "invoice_number": "INV-###",
    "claim_number": "CLM-###",
    "policy_number": "POL-[MASKED]",
    "contract_number": "if shown",
    "authorization_number": "AUTH-###",
    "eob_number": "EOB-####"
  }},
  
  "service_dates": {{
    "service_start": "[MASKED]",
    "service_end": "[MASKED]",
    "billing_period": "description",
    "claim_submitted": "[MASKED]",
    "claim_processed": "[MASKED]",
    "eob_date": "[MASKED]"
  }},
  
  "member_info": {{
    "plan_name": "plan name",
    "plan_type": "PPO/HMO/Auto/etc",
    "group_number": "[MASKED]",
    "relationship": "Self/Spouse/Child/etc",
    "coverage_type": "for auto/property"
  }},
  
  "provider_info": {{
    "provider_type": "Hospital/Clinic/Auto Body/etc", 
    "network_status": "In-Network/Out-of-Network",
    "place_of_service_code": "if medical"
  }},
  
  "diagnosis_codes": [
    {{
      "code": "ICD-10 code",
      "type": "ICD-10",
      "description": "diagnosis description",
      "is_primary": true/false
    }}
  ],
  
  "procedure_line_items": [
    {{
      "code": "CPT or service code",
      "description": "service description",
      "units": number,
      "amount_billed": number,
      "allowed_amount": number,
      "adjustment_amount": number,
      "deductible_applied": number,
      "copay_amount": number,
      "coinsurance_amount": number,
      "patient_responsibility": number,
      "service_date": "[MASKED] or date"
    }}
  ],
  
  "payment_summary": [
    {{"description": "Total Billed Amount", "amount": number}},
    {{"description": "Contractual Adjustment", "amount": number}},
    {{"description": "Allowed Amount", "amount": number}},
    {{"description": "Deductible Applied", "amount": number}},
    {{"description": "Copay", "amount": number}},
    {{"description": "Coinsurance", "amount": number}},
    {{"description": "Insurance Paid", "amount": number}},
    {{"description": "Patient Responsibility", "amount": number}},
    {{"description": "Amount Patient Paid", "amount": number}},
    {{"description": "Balance Due", "amount": number}}
  ],
  
  "claim_summary": {{
    "total_billed": number,
    "total_allowed": number,
    "total_adjustments": number,
    "deductible_applied": number,
    "copays": number,
    "coinsurance": number,
    "insurance_paid": number,
    "patient_responsibility": number,
    "amount_patient_paid": number,
    "balance_due": number
  }},
  
  "claim_status_info": {{
    "status": "Paid/Denied/Pending",
    "denial_reason": "if denied",
    "denial_code": "code if shown",
    "appeal_deadline": "[MASKED]",
    "adjustment_code": "code if shown",
    "adjustment_reason": "explanation"
  }},
  
  "payment_details": {{
    "payment_date": "[MASKED]",
    "payment_method": "Check/EFT/Credit Card/etc",
    "check_number": "if applicable",
    "payment_amount": number,
    "outstanding_balance": number
  }},
  
  "billing_period": {{
    "start_date": "[MASKED]",
    "end_date": "[MASKED]"
  }},
  
  "additional_details": [
    "Any notes from bill",
    "Special information",
    "Medical necessity",
    "Prior auth or referral info",
    "Repair details for auto/property"
  ],
  
  "redaction_notes": ["what was masked"]
}}

=== ABSOLUTE REQUIREMENTS ===
1. EVERY financial amount on the bill MUST be captured somewhere
2. payment_summary array MUST list every line from the bill's payment section
3. procedure_line_items MUST include ALL columns shown for each service
4. Numbers must be numbers: 123.45 not "123.45"
5. Do NOT omit financial data - if it's visible and not personal, capture it
6. Return ONLY a valid JSON object - no markdown, no text before or after, no comments
7. If a column isn't visible for a line item, use null
8. Handle multiple procedures: create separate entries in procedure_line_items
9. Ensure the JSON is properly formatted and parseable
"""
    
    def get_redaction_prompt(self) -> str:
        """
        Get the LLM prompt for redacting personal information from bill data.
        
        Returns:
            str: Prompt instructing the LLM to redact sensitive fields
        """
        redaction_list = ", ".join(self.redaction_fields)
        return f"""You are a data privacy expert. Your task is to redact personal and sensitive information from the given text or data.

Fields to redact: {redaction_list}

Rules:
1. Replace any personal information with [REDACTED] or [MASKED]
2. Do NOT remove information about services, charges, providers, or usage details
3. Keep the structure and format of the original data
4. Preserve numeric values related to billing amounts and service details
5. If a date appears in personal context (e.g., date of birth), redact it
6. If a date appears in service context (e.g., billing period), keep it or replace with [BILLING PERIOD]

Return the redacted version of the input.
"""
    
    def get_format_prompt(self) -> str:
        """
        Get the LLM prompt for formatting output as structured JSON.
        
        Returns:
            str: Prompt instructing the LLM to format output as valid JSON
        """
        return """You are a data formatting expert. Convert the provided bill information into a perfectly valid JSON object.

Requirements:
1. Output MUST be valid JSON (no trailing commas, proper escaping)
2. Use these top-level keys:
   - service_information (string)
   - service_type (string)
   - provider (string)
   - billing_period (object with start_date, end_date)
   - charges (array of objects with charge_type, amount, description)
   - summary (object with total_amount, currency)
   - additional_details (array of strings)
   - redaction_notes (array of strings)
3. Ensure all numeric values in charges and summary are actual numbers, not strings
4. Return ONLY the JSON object, no additional text

Example format:
{{
  "service_information": "Electric utility service",
  "service_type": "utility",
  "provider": "PowerCorp",
  "billing_period": {{"start_date": "[MASKED]", "end_date": "[MASKED]"}},
  "charges": [{{"charge_type": "electricity usage", "amount": 125.50, "description": "based on monthly consumption"}}],
  "summary": {{"total_amount": 145.75, "currency": "USD"}},
  "additional_details": ["avg usage per day: 15 kWh"],
  "redaction_notes": ["customer name masked", "address masked", "service dates not specified"]
}}
"""
    
    def __repr__(self) -> str:
        return (
            f"AgentReadingBillsEntity(model_name='{self.model_name}', "
            f"version='{self.version}', "
            f"supported_bill_types={self.supported_bill_types}, "
            f"initialized_at={self.initialized_at.isoformat()})"
        )
