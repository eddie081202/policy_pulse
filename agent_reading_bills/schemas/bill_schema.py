"""Bill Schema - Comprehensive schema for extracting ALL financial information from bills."""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime


class BillingPeriod:
    """Represents the billing period information."""
    
    def __init__(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        **kwargs
    ):
        self.start_date = start_date or "[MASKED]"
        self.end_date = end_date or "[MASKED]"
        # Capture any additional fields
        self.additional_info = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "start_date": self.start_date,
            "end_date": self.end_date
        }
        result.update(self.additional_info)
        return result
    
    def __repr__(self) -> str:
        return f"BillingPeriod(start_date='{self.start_date}', end_date='{self.end_date}')"


class Charge:
    """Represents a single charge on the bill."""
    
    def __init__(
        self,
        charge_type: str,
        amount: Union[float, str],
        description: Optional[str] = None,
        **kwargs
    ):
        self.charge_type = charge_type
        self.amount = float(amount) if isinstance(amount, str) else amount
        self.description = description or ""
        # Capture any additional fields
        self.additional_info = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "charge_type": self.charge_type,
            "amount": self.amount,
            "description": self.description
        }
        result.update(self.additional_info)
        return result
    
    def __repr__(self) -> str:
        return f"Charge(charge_type='{self.charge_type}', amount={self.amount})"


class Deduction:
    """Represents a deduction, adjustment, or fee reduction on the bill."""
    
    def __init__(
        self,
        deduction_type: str,
        amount: Union[float, str],
        description: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize a deduction.
        
        Args:
            deduction_type: Type of deduction (e.g., "copay", "deductible", "coinsurance", 
                           "contractual_adjustment", "insurance_paid", etc.)
            amount: Amount of the deduction (typically negative or positive depending on context)
            description: Optional detailed description of the deduction
        """
        self.deduction_type = deduction_type
        self.amount = float(amount) if isinstance(amount, str) else amount
        self.description = description or ""
        # Capture any additional fields
        self.additional_info = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "deduction_type": self.deduction_type,
            "amount": self.amount,
            "description": self.description
        }
        result.update(self.additional_info)
        return result
    
    def __repr__(self) -> str:
        return f"Deduction(deduction_type='{self.deduction_type}', amount={self.amount})"


class StatementLineItem:
    """
    Represents a detailed line item on a bill statement.
    
    Captures all financial information for a single service/procedure:
    - What was billed
    - What amount is allowed by the insurance plan
    - Deductible applied to this item
    - What the plan/insurance paid
    - What the patient/member pays
    """
    
    def __init__(
        self,
        service_description: str,
        billed_amount: Union[float, str],
        allowed_amount: Optional[Union[float, str]] = None,
        deductible_applied: Optional[Union[float, str]] = None,
        plan_paid: Optional[Union[float, str]] = None,
        patient_pays: Optional[Union[float, str]] = None,
        copay: Optional[Union[float, str]] = None,
        coinsurance: Optional[Union[float, str]] = None,
        contractual_adjustment: Optional[Union[float, str]] = None,
        quantity: Optional[Union[int, str]] = None,
        units: Optional[str] = None,
        procedure_code: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize a detailed statement line item.
        
        Args:
            service_description: Description of the service/procedure
            billed_amount: Amount the provider billed
            allowed_amount: Amount allowed by the insurance plan
            deductible_applied: Amount of deductible applied to this item
            plan_paid: Amount the insurance plan paid
            patient_pays: Amount the patient/member is responsible for
            copay: Copay amount (if applicable)
            coinsurance: Coinsurance amount or percentage (if applicable)
            contractual_adjustment: Contractual adjustment/discount amount
            quantity: Number of units/procedures
            units: Unit type (e.g., "minutes", "sessions")
            procedure_code: Medical procedure code (e.g., CPT code)
        """
        self.service_description = service_description
        self.billed_amount = float(billed_amount) if billed_amount else None
        self.allowed_amount = float(allowed_amount) if allowed_amount else None
        self.deductible_applied = float(deductible_applied) if deductible_applied else None
        self.plan_paid = float(plan_paid) if plan_paid else None
        self.patient_pays = float(patient_pays) if patient_pays else None
        self.copay = float(copay) if copay else None
        self.coinsurance = coinsurance
        self.contractual_adjustment = float(contractual_adjustment) if contractual_adjustment else None
        self.quantity = int(quantity) if quantity and isinstance(quantity, (int, str)) else None
        self.units = units
        self.procedure_code = procedure_code
        # Capture any additional fields
        self.additional_info = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values for cleaner output."""
        result = {
            "service_description": self.service_description,
            "billed_amount": self.billed_amount,
        }
        
        # Add amounts if they exist
        if self.allowed_amount is not None:
            result["allowed_amount"] = self.allowed_amount
        if self.deductible_applied is not None:
            result["deductible_applied"] = self.deductible_applied
        if self.plan_paid is not None:
            result["plan_paid"] = self.plan_paid
        if self.patient_pays is not None:
            result["patient_pays"] = self.patient_pays
        if self.copay is not None:
            result["copay"] = self.copay
        if self.coinsurance is not None:
            result["coinsurance"] = self.coinsurance
        if self.contractual_adjustment is not None:
            result["contractual_adjustment"] = self.contractual_adjustment
        
        # Add procedure details if they exist
        if self.quantity is not None:
            result["quantity"] = self.quantity
        if self.units:
            result["units"] = self.units
        if self.procedure_code:
            result["procedure_code"] = self.procedure_code
        
        result.update(self.additional_info)
        return result
    
    def __repr__(self) -> str:
        return f"StatementLineItem(service='{self.service_description}', billed={self.billed_amount}, patient_pays={self.patient_pays})"


class Summary:
    """Represents the billing summary."""
    
    def __init__(
        self,
        total_amount: Union[float, str],
        currency: str = "USD",
        subtotal_amount: Optional[Union[float, str]] = None,
        payment_due_date: Optional[str] = None,
        **kwargs
    ):
        self.total_amount = float(total_amount) if isinstance(total_amount, str) else total_amount
        self.subtotal_amount = float(subtotal_amount) if subtotal_amount and isinstance(subtotal_amount, str) else subtotal_amount
        self.currency = currency
        self.payment_due_date = payment_due_date or "[MASKED]"
        # Capture any additional fields
        self.additional_info = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "subtotal_amount": self.subtotal_amount,
            "total_amount": self.total_amount,
            "currency": self.currency,
            "payment_due_date": self.payment_due_date
        }
        result.update(self.additional_info)
        return result
    
    def __repr__(self) -> str:
        return f"Summary(subtotal_amount={self.subtotal_amount}, total_amount={self.total_amount}, currency='{self.currency}')"


class ProcedureLineItem:
    """Represents a detailed line item for a procedure/service with all financial columns."""
    
    def __init__(
        self,
        procedure_description: str,
        amount_billed: Union[float, str],
        cpt_code: Optional[str] = None,
        units: Optional[Union[int, float, str]] = None,
        allowed_amount: Optional[Union[float, str]] = None,
        adjustment_amount: Optional[Union[float, str]] = None,
        deductible_applied: Optional[Union[float, str]] = None,
        copay_amount: Optional[Union[float, str]] = None,
        coinsurance_amount: Optional[Union[float, str]] = None,
        patient_responsibility: Optional[Union[float, str]] = None,
        service_date: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize a procedure line item with comprehensive financial details.
        
        Args:
            procedure_description: Description of the procedure/service
            amount_billed: Amount billed for this procedure
            cpt_code: CPT code for the procedure (medical procedures)
            units: Number of units/sessions
            allowed_amount: Allowed amount by insurance
            adjustment_amount: Adjustment/discount amount
            deductible_applied: Deductible applied to this line
            copay_amount: Copay amount for this line
            coinsurance_amount: Coinsurance amount for this line
            patient_responsibility: Total patient responsibility for this line
            service_date: Date service was provided
            **kwargs: Additional financial columns specific to the bill
        """
        self.procedure_description = procedure_description
        self.amount_billed = float(amount_billed) if amount_billed else None
        self.cpt_code = cpt_code
        self.units = float(units) if units else None
        self.allowed_amount = float(allowed_amount) if allowed_amount else None
        self.adjustment_amount = float(adjustment_amount) if adjustment_amount else None
        self.deductible_applied = float(deductible_applied) if deductible_applied else None
        self.copay_amount = float(copay_amount) if copay_amount else None
        self.coinsurance_amount = float(coinsurance_amount) if coinsurance_amount else None
        self.patient_responsibility = float(patient_responsibility) if patient_responsibility else None
        self.service_date = service_date
        # Capture any additional financial columns
        self.additional_columns = {k: v for k, v in kwargs.items() if v is not None}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {}
        if self.cpt_code:
            result["cpt_code"] = self.cpt_code
        result["procedure_description"] = self.procedure_description
        if self.units is not None:
            result["units"] = self.units
        if self.amount_billed is not None:
            result["amount_billed"] = self.amount_billed
        if self.allowed_amount is not None:
            result["allowed_amount"] = self.allowed_amount
        if self.adjustment_amount is not None:
            result["adjustment_amount"] = self.adjustment_amount
        if self.deductible_applied is not None:
            result["deductible_applied"] = self.deductible_applied
        if self.copay_amount is not None:
            result["copay_amount"] = self.copay_amount
        if self.coinsurance_amount is not None:
            result["coinsurance_amount"] = self.coinsurance_amount
        if self.patient_responsibility is not None:
            result["patient_responsibility"] = self.patient_responsibility
        if self.service_date:
            result["service_date"] = self.service_date
        # Add any additional columns
        result.update(self.additional_columns)
        return result
    
    def __repr__(self) -> str:
        return f"ProcedureLineItem(description='{self.procedure_description}', billed={self.amount_billed})"


class PaymentSummaryItem:
    """Represents a single line item in the payment summary section of a bill."""
    
    def __init__(
        self,
        item_description: str,
        amount: Union[float, str],
        item_type: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize a payment summary item.
        
        Args:
            item_description: Description of the payment item (e.g., "Total Billed Amount", "Insurance Paid")
            amount: Amount for this item
            item_type: Type of item (e.g., "subtotal", "deduction", "adjustment", "patient_responsibility")
            **kwargs: Additional attributes
        """
        self.item_description = item_description
        self.amount = float(amount) if isinstance(amount, str) else amount
        self.item_type = item_type
        self.additional_info = {k: v for k, v in kwargs.items() if v is not None}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "item_description": self.item_description,
            "amount": self.amount
        }
        if self.item_type:
            result["item_type"] = self.item_type
        result.update(self.additional_info)
        return result
    
    def __repr__(self) -> str:
        return f"PaymentSummaryItem('{self.item_description}', {self.amount})"


class MemberInfo:
    """Represents member/patient information."""
    
    def __init__(
        self,
        member_id: Optional[str] = None,
        member_name: Optional[str] = None,
        relationship: Optional[str] = None,
        group_number: Optional[str] = None,
        plan_name: Optional[str] = None,
        policy_number: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize member information.
        
        Args:
            member_id: Member ID number
            member_name: Member name (will be redacted)
            relationship: Relationship to primary (Self, Spouse, Dependent, etc.)
            group_number: Group number
            plan_name: Health plan name
            policy_number: Policy number
            **kwargs: Additional member details
        """
        self.member_id = member_id or "[MASKED]"
        self.member_name = member_name or "[MASKED]"
        self.relationship = relationship
        self.group_number = group_number or "[MASKED]"
        self.plan_name = plan_name
        self.policy_number = policy_number or "[MASKED]"
        self.additional_info = {k: v for k, v in kwargs.items() if v is not None}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "member_id": self.member_id,
            "member_name": self.member_name
        }
        if self.relationship:
            result["relationship"] = self.relationship
        result.update({
            "group_number": self.group_number,
            "plan_name": self.plan_name,
            "policy_number": self.policy_number
        })
        result.update(self.additional_info)
        return result
    
    def __repr__(self) -> str:
        return f"MemberInfo(relationship='{self.relationship}', plan='{self.plan_name}')"


class ProviderInfo:
    """Represents provider/facility information."""
    
    def __init__(
        self,
        provider_name: str,
        provider_type: Optional[str] = None,
        network_status: Optional[str] = None,
        tax_id: Optional[str] = None,
        npi_number: Optional[str] = None,
        address: Optional[str] = None,
        phone: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize provider information.
        
        Args:
            provider_name: Name of provider/facility
            provider_type: Type of provider (Hospital, Clinic, Lab, etc.)
            network_status: In-Network or Out-of-Network
            tax_id: Provider tax ID
            npi_number: National Provider Identifier
            address: Provider address
            phone: Provider phone number
            **kwargs: Additional provider details
        """
        self.provider_name = provider_name
        self.provider_type = provider_type
        self.network_status = network_status
        self.tax_id = tax_id or "[MASKED]"
        self.npi_number = npi_number or "[MASKED]"
        self.address = address or "[MASKED]"
        self.phone = phone or "[MASKED]"
        self.additional_info = {k: v for k, v in kwargs.items() if v is not None}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "provider_name": self.provider_name,
            "provider_type": self.provider_type,
            "network_status": self.network_status,
            "tax_id": self.tax_id,
            "npi_number": self.npi_number,
            "address": self.address,
            "phone": self.phone
        }
        result.update(self.additional_info)
        return result
    
    def __repr__(self) -> str:
        return f"ProviderInfo(name='{self.provider_name}', network='{self.network_status}')"


class DiagnosisInfo:
    """Represents diagnosis code information."""
    
    def __init__(
        self,
        code: str,
        code_type: Optional[str] = None,
        description: Optional[str] = None,
        is_primary: Optional[bool] = None,
        **kwargs
    ):
        """
        Initialize diagnosis information.
        
        Args:
            code: Diagnosis code (ICD-10, ICD-9, etc.)
            code_type: Type of code (ICD-10, ICD-9, etc.)
            description: Description of the diagnosis
            is_primary: Whether this is the primary diagnosis
            **kwargs: Additional details
        """
        self.code = code
        self.code_type = code_type
        self.description = description
        self.is_primary = is_primary
        self.additional_info = {k: v for k, v in kwargs.items() if v is not None}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "code": self.code
        }
        if self.code_type:
            result["code_type"] = self.code_type
        if self.description:
            result["description"] = self.description
        if self.is_primary is not None:
            result["is_primary"] = self.is_primary
        result.update(self.additional_info)
        return result
    
    def __repr__(self) -> str:
        return f"DiagnosisInfo(code='{self.code}', type='{self.code_type}')"


class BillSchema:
    """
    COMPREHENSIVE Bill Schema for capturing ALL financial information.
    
    Represents complete structured output from bill analysis including:
    - Service information and provider details
    - Member/patient details
    - Detailed procedure/service line items with all financial columns
    - Complete payment summary breakdown
    - Charges and deductions
    - Summary totals
    - Diagnosis codes and service dates
    - Additional notes and redaction information
    
    Attributes:
        service_information (str): Description of the service
        service_type (str): Type of service (utility, telecom, insurance, etc.)
        provider (str): Service provider/company name
        member_info (MemberInfo): Member/patient information (optional)
        provider_info (ProviderInfo): Provider/facility information (optional)
        billing_period (BillingPeriod): Start and end dates of billing period
        procedure_line_items (list): Detailed line items with all financial columns (optional)
        charges (list): List of charges on the bill
        deductions (list): List of deductions, adjustments, and reductions
        payment_summary_items (list): Breakdown of payment summary section (optional)
        diagnosis_codes (list): Diagnosis codes (optional)
        summary (Summary): Billing summary with total amount
        additional_details (list): Any other relevant service information
        redaction_notes (list): Notes about what information was redacted
    """
    
    # Valid service types
    VALID_SERVICE_TYPES = [
        "utility",      # Electric, water, gas, internet
        "telecom",      # Phone, mobile, broadband
        "insurance",    # Health, auto, home, life
        "credit_card",  # Credit card statements
        "other"         # Any other type
    ]
    
    def __init__(
        self,
        service_information: str,
        service_type: str,
        provider: str,
        billing_period: Union[Dict, BillingPeriod],
        charges: List[Union[Dict, Charge]],
        summary: Union[Dict, Summary],
        member_info: Optional[Union[Dict, MemberInfo]] = None,
        provider_info: Optional[Union[Dict, ProviderInfo]] = None,
        procedure_line_items: Optional[List[Union[Dict, ProcedureLineItem]]] = None,
        deductions: Optional[List[Union[Dict, Deduction]]] = None,
        payment_summary_items: Optional[List[Union[Dict, PaymentSummaryItem]]] = None,
        diagnosis_codes: Optional[List[Union[Dict, DiagnosisInfo]]] = None,
        additional_details: Optional[List[str]] = None,
        redaction_notes: Optional[List[str]] = None
    ):
        """
        Initialize the comprehensive bill schema.
        
        Args:
            service_information: Description of the service
            service_type: Type of service
            provider: Service provider name
            billing_period: Billing period info (dict or BillingPeriod)
            charges: List of charges (dicts or Charge objects)
            summary: Billing summary (dict or Summary object)
            member_info: Optional member information (dict or MemberInfo)
            provider_info: Optional provider information (dict or ProviderInfo)
            procedure_line_items: Optional detailed line items (dicts or ProcedureLineItem objects)
            deductions: Optional list of deductions (dicts or Deduction objects)
            payment_summary_items: Optional payment summary items (dicts or PaymentSummaryItem objects)
            diagnosis_codes: Optional diagnosis codes (dicts or DiagnosisInfo objects)
            additional_details: Optional additional information
            redaction_notes: Optional notes about redactions
        """
        self.service_information = service_information
        self.service_type = self._validate_service_type(service_type)
        self.provider = provider
        
        # Convert member_info
        if member_info:
            if isinstance(member_info, dict):
                self.member_info = MemberInfo(**member_info)
            else:
                self.member_info = member_info
        else:
            self.member_info = None
        
        # Convert provider_info
        if provider_info:
            if isinstance(provider_info, dict):
                self.provider_info = ProviderInfo(**provider_info)
            else:
                self.provider_info = provider_info
        else:
            self.provider_info = None
        
        # Convert billing_period
        if isinstance(billing_period, dict):
            self.billing_period = BillingPeriod(**billing_period)
        else:
            self.billing_period = billing_period
        
        # Convert procedure_line_items
        self.procedure_line_items = []
        if procedure_line_items:
            for item in procedure_line_items:
                if isinstance(item, dict):
                    self.procedure_line_items.append(ProcedureLineItem(**item))
                else:
                    self.procedure_line_items.append(item)
        
        # Convert charges list
        self.charges = []
        for charge in charges:
            if isinstance(charge, dict):
                self.charges.append(Charge(**charge))
            else:
                self.charges.append(charge)
        
        # Convert deductions list
        self.deductions = []
        if deductions:
            for deduction in deductions:
                if isinstance(deduction, dict):
                    self.deductions.append(Deduction(**deduction))
                else:
                    self.deductions.append(deduction)
        
        # Convert payment_summary_items
        self.payment_summary_items = []
        if payment_summary_items:
            for item in payment_summary_items:
                if isinstance(item, dict):
                    self.payment_summary_items.append(PaymentSummaryItem(**item))
                else:
                    self.payment_summary_items.append(item)
        
        # Convert diagnosis_codes
        self.diagnosis_codes = []
        if diagnosis_codes:
            for code in diagnosis_codes:
                if isinstance(code, dict):
                    self.diagnosis_codes.append(DiagnosisInfo(**code))
                else:
                    self.diagnosis_codes.append(code)
        
        # Convert summary
        if isinstance(summary, dict):
            self.summary = Summary(**summary)
        else:
            self.summary = summary
        
        # Handle optional fields
        self.additional_details = additional_details or []
        self.redaction_notes = redaction_notes or ["Personal information has been redacted"]
    
    @staticmethod
    def _validate_service_type(service_type: str) -> str:
        """
        Validate and normalize service type.
        
        Args:
            service_type: Service type to validate
        
        Returns:
            str: Validated service type (lowercase)
        
        Raises:
            ValueError: If service type is not recognized
        """
        normalized = service_type.lower().strip()
        if normalized not in BillSchema.VALID_SERVICE_TYPES:
            return "other"  # Default to 'other' for unknown types
        return normalized
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert schema to dictionary (suitable for JSON serialization).
        Includes all captured financial information.
        
        Returns:
            Dict: Dictionary representation of the schema
        """
        result = {
            "service_information": self.service_information,
            "service_type": self.service_type,
            "provider": self.provider,
            "billing_period": self.billing_period.to_dict(),
            "charges": [charge.to_dict() for charge in self.charges],
            "deductions": [deduction.to_dict() for deduction in self.deductions],
            "summary": self.summary.to_dict(),
            "additional_details": self.additional_details,
            "redaction_notes": self.redaction_notes
        }
        
        # Add optional detailed information
        if self.member_info:
            result["member_info"] = self.member_info.to_dict()
        
        if self.provider_info:
            result["provider_info"] = self.provider_info.to_dict()
        
        if self.procedure_line_items:
            result["procedure_line_items"] = [item.to_dict() for item in self.procedure_line_items]
        
        if self.payment_summary_items:
            result["payment_summary"] = [item.to_dict() for item in self.payment_summary_items]
        
        if self.diagnosis_codes:
            result["diagnosis_codes"] = [code.to_dict() for code in self.diagnosis_codes]
        
        return result
    
    def __repr__(self) -> str:
        return (
            f"BillSchema(service_type='{self.service_type}', "
            f"provider='{self.provider}', "
            f"charges={len(self.charges)}, "
            f"procedure_items={len(self.procedure_line_items)})"
        )
