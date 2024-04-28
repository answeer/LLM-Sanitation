# Import Guard and Validator
from pydantic import BaseModel, Field
from guardrails.hub import ValidRange
from guardrails import Guard

# Initialize Validator
val = ValidRange(min=0, max=10, on_fail="exception")


# Create Pydantic BaseModel
class PetInfo(BaseModel):
    pet_name: str
    pet_age: int = Field(validators=[val])


# Create a Guard to check for valid Pydantic output
guard = Guard.from_pydantic(output_class=PetInfo)

# Run LLM output generating JSON through guard
guard.parse(
    """
    {
        "pet_name": "Caesar",
        "pet_age": 5
    }
    """
)

try:
    # Run LLM output generating JSON through guard
    guard.parse(
        """
        {
            "pet_name": "Caesar",
            "pet_age": 15
        }
        """
    )
except Exception as e:
    print(e)
