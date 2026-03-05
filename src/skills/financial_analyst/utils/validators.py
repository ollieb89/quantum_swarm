"""
Validators - Input validation for financial analysis tools

Ensures data integrity and required fields presence.
"""

from typing import Dict, Any, List, Tuple, Optional


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate that all required fields are present in the data.

    Args:
        data: Input data dictionary
        required_fields: List of required field names

    Returns:
        Tuple of (is_valid, error_message)
    """
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"

    return True, None


def validate_numeric_value(value: Any, field_name: str, allow_zero: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Validate that a field contains a valid numeric value.

    Args:
        value: Value to validate
        field_name: Name of the field (for error messages)
        allow_zero: Whether zero is considered valid

    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None:
        return False, f"{field_name} is required"

    try:
        num_value = float(value)
        if not allow_zero and num_value == 0:
            return False, f"{field_name} must be non-zero"
        return True, None
    except (ValueError, TypeError):
        return False, f"{field_name} must be a numeric value"


def validate_positive_value(value: Any, field_name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that a value is positive.

    Args:
        value: Value to validate
        field_name: Name of the field

    Returns:
        Tuple of (is_valid, error_message)
    """
    is_valid, error = validate_numeric_value(value, field_name)
    if not is_valid:
        return is_valid, error

    if float(value) <= 0:
        return False, f"{field_name} must be positive"

    return True, None


def validate_ratio(value: Any, field_name: str, min_val: float = None, max_val: float = None) -> Tuple[bool, Optional[str]]:
    """
    Validate that a value is within acceptable range for a ratio.

    Args:
        value: Value to validate
        field_name: Name of the field
        min_val: Minimum acceptable value (optional)
        max_val: Maximum acceptable value (optional)

    Returns:
        Tuple of (is_valid, error_message)
    """
    is_valid, error = validate_numeric_value(value, field_name, allow_zero=True)
    if not is_valid:
        return is_valid, error

    num_value = float(value)

    if min_val is not None and num_value < min_val:
        return False, f"{field_name} must be at least {min_val}"

    if max_val is not None and num_value > max_val:
        return False, f"{field_name} must be at most {max_val}"

    return True, None


def validate_percentage(value: Any, field_name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that a value is a valid percentage (between -100% and 100% typically).

    Args:
        value: Value to validate
        field_name: Name of the field

    Returns:
        Tuple of (is_valid, error_message)
    """
    return validate_ratio(value, field_name, min_val=-10.0, max_val=10.0)


def validate_list_not_empty(data: List, field_name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate that a list field is not empty.

    Args:
        data: List to validate
        field_name: Name of the field

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not data:
        return False, f"{field_name} cannot be empty"

    return True, None


def validate_dict_structure(data: Dict, required_keys: List[str], field_name: str = "data") -> Tuple[bool, Optional[str]]:
    """
    Validate that a dictionary has required keys.

    Args:
        data: Dictionary to validate
        required_keys: List of required keys
        field_name: Name of the field (for error messages)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, f"{field_name} must be a dictionary"

    missing_keys = [key for key in required_keys if key not in data]

    if missing_keys:
        return False, f"{field_name} missing required keys: {', '.join(missing_keys)}"

    return True, None


def validate_ratio_analysis_input(data: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate input for ratio calculator.

    Expected structure:
    {
        "income_statement": {...},
        "balance_sheet": {...},
        "cash_flow": {...},  # optional
        "market_data": {...}  # optional
    }

    Args:
        data: Input data dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for required sections
    required_sections = ["income_statement", "balance_sheet"]
    for section in required_sections:
        if section not in data:
            return False, f"Missing required section: {section}"

    # Validate income_statement required fields
    income_required = ["revenue", "net_income"]
    for field in income_required:
        if field not in data["income_statement"]:
            return False, f"income_statement missing required field: {field}"

    # Validate balance_sheet required fields
    balance_required = ["total_assets", "total_equity", "total_debt"]
    for field in balance_required:
        if field not in data["balance_sheet"]:
            return False, f"balance_sheet missing required field: {field}"

    return True, None


def validate_dcf_valuation_input(data: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate input for DCF valuation.

    Args:
        data: Input data dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for historical data
    if "historical" not in data:
        return False, "Missing required section: historical"

    historical = data["historical"]
    if "revenue" not in historical:
        return False, "historical missing required field: revenue"

    # Check for assumptions
    if "assumptions" not in data:
        return False, "Missing required section: assumptions"

    assumptions = data["assumptions"]
    required_assumptions = ["terminal_growth_rate", "wacc_inputs"]
    for field in required_assumptions:
        if field not in assumptions:
            return False, f"assumptions missing required field: {field}"

    return True, None


def validate_budget_variance_input(data: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate input for budget variance analyzer.

    Args:
        data: Input data dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    if "line_items" not in data:
        return False, "Missing required field: line_items"

    is_valid, error = validate_list_not_empty(data["line_items"], "line_items")
    if not is_valid:
        return is_valid, error

    # Validate each line item has required fields
    required_item_fields = ["name", "type", "actual", "budget"]
    for i, item in enumerate(data["line_items"]):
        for field in required_item_fields:
            if field not in item:
                return False, f"line_items[{i}] missing required field: {field}"

        # Validate type is either revenue or expense
        if item["type"] not in ["revenue", "expense"]:
            return False, f"line_items[{i}] type must be 'revenue' or 'expense'"

    return True, None


def validate_forecast_input(data: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate input for forecast builder.

    Args:
        data: Input data dictionary

    Returns:
        Tuple of (is_valid, error_message)
    """
    if "historical_periods" not in data:
        return False, "Missing required field: historical_periods"

    is_valid, error = validate_list_not_empty(data["historical_periods"], "historical_periods")
    if not is_valid:
        return is_valid, error

    # Validate each period has required fields
    required_period_fields = ["period", "revenue"]
    for i, period in enumerate(data["historical_periods"]):
        for field in required_period_fields:
            if field not in period:
                return False, f"historical_periods[{i}] missing required field: {field}"

    return True, None


def validate_and_sanitize(data: Dict, validation_func) -> Tuple[Dict, Optional[str]]:
    """
    Generic validation and sanitization wrapper.

    Args:
        data: Input data
        validation_func: Specific validation function to use

    Returns:
        Tuple of (sanitized_data, error_message)
    """
    is_valid, error = validation_func(data)
    if not is_valid:
        return {}, error

    # Sanitize: Convert string numbers to floats where appropriate
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, dict):
            sanitized[key] = {}
            for k, v in value.items():
                if isinstance(v, str) and v.replace(".", "").replace("-", "").isdigit():
                    sanitized[key][k] = float(v)
                else:
                    sanitized[key][k] = v
        elif isinstance(value, str) and value.replace(".", "").replace("-", "").isdigit():
            sanitized[key] = float(value)
        else:
            sanitized[key] = value

    return sanitized, None
