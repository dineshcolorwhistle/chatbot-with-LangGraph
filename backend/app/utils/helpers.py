from typing import Dict, Any
from app.models.state import CollectedData

def format_company_name(namespace: str) -> str:
    """
    Format a namespace string into a user-friendly company name.
    Example: 'google_cloud' -> 'Google Cloud'
             'acme' -> 'Acme'
    """
    if not namespace:
        return "Company"
    return " ".join([word.capitalize() for word in namespace.replace("-", "_").split("_")])

def serialize_data(collected_data: CollectedData) -> Dict[str, Any]:
    """
    Convert CollectedData Pydantic model to a standard dictionary.
    """
    if isinstance(collected_data, CollectedData):
        return collected_data.model_dump()
    return collected_data

def merge_collected_data(existing: CollectedData, new_data: Dict[str, Any]) -> CollectedData:
    """
    Non-destructively merge incoming extracted data dictionary into the existing CollectedData model.
    Values are only updated if the new value is non-empty.
    """
    # Convert existing model to dictionary
    existing_dict = existing.model_dump()

    # Iterate through main category fields (personal_info, tech_discovery, scope_pricing)
    for category, fields in new_data.items():
        if category in existing_dict and isinstance(fields, dict):
            for field_name, new_val in fields.items():
                if field_name in existing_dict[category]:
                    # Update if new_val is not empty, None, or a blank string
                    if new_val not in (None, "", [], {}):
                        existing_dict[category][field_name] = str(new_val).strip()

    # Return a new populated Pydantic model
    return CollectedData(**existing_dict)
