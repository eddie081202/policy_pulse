"""Main module - Bill reading service initialization and execution."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_reading_bills.entities import AgentReadingBillsEntity
from agent_reading_bills.services import AgentReadingBillsService


def main():
    """Initialize entity and service to read bills."""
    
    # Initialize the entity
    entity = AgentReadingBillsEntity(
        api_key=None,
        model_name="gpt-4o",
        version="1.0.0"
    )
    
    # Create the service
    service = AgentReadingBillsService(model=entity)
    
    # Read a bill
    image_path = "test_image.png"
    result = service.read_bill(image_path)
    
    # Output results
    print(json.dumps(result, indent=2))
    
    # Save to file
    output_path = Path("bill_analysis_output.json")
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\nOutput saved to: {output_path.absolute()}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
