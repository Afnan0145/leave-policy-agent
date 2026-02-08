"""
Leave policy data - Mock data for the assignment
"""

LEAVE_POLICIES = {
    "US": {
        "PTO": {
            "annual_allowance": 20,
            "carryover_limit": 5,
            "min_notice_days": 3,
            "max_consecutive_days": 10,
            "blackout_periods": ["Dec 20-31"],
            "approval_required": True,
            "description": "Paid Time Off for vacation and personal days"
        },
        "Sick Leave": {
            "annual_allowance": 10,
            "carryover_limit": 0,
            "min_notice_days": 0,
            "documentation_required_after_days": 3,
            "description": "Sick leave for medical appointments and illness"
        },
        "Parental Leave": {
            "allowance_weeks": 16,
            "eligibility_months": 12,
            "paid": True,
            "description": "Paid parental leave for new parents"
        }
    },
    "India": {
        "Privilege Leave": {
            "annual_allowance": 18,
            "carryover_limit": 30,
            "min_notice_days": 7,
            "encashment_allowed": True,
            "description": "Earned leave for vacation and personal matters"
        },
        "Casual Leave": {
            "annual_allowance": 12,
            "carryover_limit": 0,
            "max_consecutive_days": 3,
            "description": "Short-term leave for urgent personal matters"
        },
        "Sick Leave": {
            "annual_allowance": 12,
            "carryover_limit": 0,
            "documentation_required_after_days": 3,
            "description": "Medical leave for illness and health issues"
        },
        "Optional Holidays": {
            "annual_allowance": 3,
            "from_list": True,
            "advance_booking_required": True,
            "description": "Choice of holidays from pre-approved list"
        },
        "Maternity Leave": {
            "allowance_weeks": 26,
            "paid": True,
            "eligibility_months": 6,
            "description": "Maternity leave for expectant mothers"
        },
        "Paternity Leave": {
            "allowance_days": 15,
            "paid": True,
            "eligibility_months": 12,
            "description": "Paternity leave for new fathers"
        }
    },
    "UK": {
        "Annual Leave": {
            "annual_allowance": 25,
            "carryover_limit": 5,
            "min_notice_days": 7,
            "approval_required": True,
            "description": "Annual holiday entitlement"
        },
        "Sick Leave": {
            "annual_allowance": 10,
            "carryover_limit": 0,
            "documentation_required_after_days": 7,
            "statutory_sick_pay": True,
            "description": "Sick leave with statutory sick pay"
        },
        "Parental Leave": {
            "allowance_weeks": 18,
            "eligibility_months": 12,
            "paid": True,
            "description": "Shared parental leave"
        }
    }
}

# Mock employee data for testing
MOCK_EMPLOYEES = {
    "EMP001": {
        "employee_id": "EMP001",
        "name": "John Doe",
        "country": "US",
        "department": "Engineering",
        "join_date": "2023-01-15",
        "tenure_months": 14,
        "leave_balance": {
            "PTO": 15,
            "Sick Leave": 10,
            "Parental Leave": 0
        }
    },
    "EMP002": {
        "employee_id": "EMP002",
        "name": "Jane Smith",
        "country": "India",
        "department": "Marketing",
        "join_date": "2022-06-01",
        "tenure_months": 20,
        "leave_balance": {
            "Privilege Leave": 12,
            "Casual Leave": 8,
            "Sick Leave": 12,
            "Optional Holidays": 3
        }
    },
    "EMP003": {
        "employee_id": "EMP003",
        "name": "Alice Johnson",
        "country": "UK",
        "department": "Sales",
        "join_date": "2024-01-01",
        "tenure_months": 2,
        "leave_balance": {
            "Annual Leave": 25,
            "Sick Leave": 10
        }
    }
}


def get_leave_policy(country: str, leave_type: str = None):
    """
    Get leave policy for a specific country and leave type
    
    Args:
        country: Country code (US, India, UK)
        leave_type: Specific leave type (optional)
        
    Returns:
        Policy details or None if not found
    """
    country = country.upper()
    
    if country not in LEAVE_POLICIES:
        return None
    
    if leave_type:
        # Case-insensitive lookup
        for policy_name, policy_details in LEAVE_POLICIES[country].items():
            if policy_name.lower() == leave_type.lower():
                return {policy_name: policy_details}
        return None
    
    return LEAVE_POLICIES[country]


def get_employee_data(employee_id: str):
    """
    Get employee data by ID
    
    Args:
        employee_id: Employee identifier
        
    Returns:
        Employee details or None if not found
    """
    return MOCK_EMPLOYEES.get(employee_id)


def list_countries():
    """Get list of supported countries"""
    return list(LEAVE_POLICIES.keys())


def list_leave_types(country: str):
    """Get list of leave types for a country"""
    country = country.upper()
    if country not in LEAVE_POLICIES:
        return []
    return list(LEAVE_POLICIES[country].keys())