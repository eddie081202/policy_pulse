# Agent Reading Bills

A Python-based LLM service that reads bill images and extracts service information without exposing personal data. Uses OpenAI GPT-4 Vision to automatically analyze bills, identify service types, and redact sensitive personal information.

## Features

- **Bill Image Analysis**: Reads JPG, PNG, GIF, and WEBP bill images
- **Automatic Service Detection**: Identifies bill type (utility, telecom, insurance, credit card, other)
- **Personal Data Redaction**: Automatically masks 50+ categories of personal information
- **Structured JSON Output**: Returns detailed service information in a well-defined schema
- **Comprehensive Logging**: Built-in logging for debugging and monitoring
- **Type Safety**: Full type hints for better IDE support and error catching
- **Entity-Service Architecture**: Clean separation of configuration (entity) and operations (service)

## Architecture

The project follows an **Entity-Service Pattern**:

### Entities (State/Configuration)
- **BaseEntity**: Core model state (API key, model name, initialization timestamp)
- **AgentReadingBillsEntity**: Specialized entity with:
  - Configuration constants (model name, API endpoint)
  - Supported bill types
  - Redaction field definitions
  - LLM prompt templates for extraction, redaction, and formatting

### Services (Operations/Behavior)
- **BaseService**: Fundamental operations (validation, error handling, logging)
- **AgentReadingBillsService**: Bill-specific operations including:
  - Image processing (validation, encoding, format detection)
  - OpenAI Vision API integration
  - Service information extraction
  - Personal data redaction
  - JSON formatting

### Schemas (Data Structure)
- **BillSchema**: Defines output structure with type validation
  - BillingPeriod: Billing period details
  - Charge: Individual bill charges
  - Summary: Billing summary

## Installation

### Prerequisites
- Python 3.8+
- OpenAI API key with GPT-4 Vision access

### Setup

1. **Clone or download the repository**
   ```bash
   cd agent_reading_bills
   ```

2. **Create a virtual environment** (optional but recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install requests
   ```

4. **Configure API key**
   
   Create a `.env` file in the project root:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```
   
   Or set environment variable:
   ```bash
   export OPENAI_API_KEY=your_openai_api_key_here
   ```

## Usage

### Basic Example

```python
from agent_reading_bills.entities import AgentReadingBillsEntity
from agent_reading_bills.services import AgentReadingBillsService
import json

# Step 1: Initialize the entity (configuration)
entity = AgentReadingBillsEntity()

# Step 2: Create the service
service = AgentReadingBillsService(model=entity)

# Step 3: Read a bill image
result = service.read_bill("path/to/bill_image.jpg")

# Step 4: Use the result
if 'error' not in result:
    print(json.dumps(result, indent=2))
    
    # Save to file
    with open("bill_analysis.json", "w") as f:
        json.dump(result, f, indent=2)
else:
    print(f"Error: {result['error_message']}")
```

### Output Structure

```json
{
  "service_information": "Electric utility service",
  "service_type": "utility",
  "provider": "PowerCorp Electric",
  "billing_period": {
    "start_date": "[MASKED]",
    "end_date": "[MASKED]"
  },
  "charges": [
    {
      "charge_type": "electricity usage",
      "amount": 125.50,
      "description": "based on 800 kWh monthly consumption"
    },
    {
      "charge_type": "transmission charge",
      "amount": 15.25,
      "description": "fixed monthly service fee"
    }
  ],
  "summary": {
    "total_amount": 145.75,
    "currency": "USD",
    "payment_due_date": "[MASKED]"
  },
  "additional_details": [
    "Average daily usage: 26 kWh",
    "Meter efficiency rating: Grade A"
  ],
  "redaction_notes": [
    "Redacted fields: customer_name, address, account_number, account_id"
  ]
}
```

## Supported Bill Types

The service auto-detects and categorizes bills as:
- **utility**: Electric, water, gas, internet
- **telecom**: Phone service, mobile plans, broadband
- **insurance**: Health, auto, home, life insurance
- **credit_card**: Credit card statements
- **other**: Unknown or miscellaneous bill types

## Personal Information Redaction

The service automatically redacts the following categories:

### Names
- Full name, first name, last name, middle name

### Address Information
- Street address, city, state, zip code, country
- Apartment number, suite number, unit number

### Contact Information
- Phone number, mobile number, email address, fax number

### Identification Numbers
- Social Security Number (SSN), Tax ID, EIN, TIN
- Passport number, driver's license number
- Customer ID, account number, member ID

### Financial Information
- Credit card number, bank account number, routing number
- Invoice number

### Personal Details
- Date of birth, age

### Other
- Service dates, IP address, username, password, PIN

All redactions are tracked and reported in the `redaction_notes` field of the output.

## Error Handling

The service provides structured error responses:

```python
result = service.read_bill("invalid_path.jpg")

if 'error' in result:
    print(f"Error Type: {result['error_type']}")
    print(f"Message: {result['error_message']}")
    print(f"Operation: {result['operation']}")
```

### Common Errors
- **FileNotFoundError**: Bill image file doesn't exist
- **ValueError**: Unsupported image format
- **api_error**: OpenAI API request failed (check API key, rate limits)
- **JSONDecodeError**: LLM response wasn't valid JSON

## Logging

The service includes built-in logging for debugging:

```python
import logging

# Enable debug logging
logging.getLogger().setLevel(logging.DEBUG)

# Run the service
result = service.read_bill("bill.jpg")
# See detailed logs about image validation, API calls, processing steps
```

Log levels:
- **INFO**: Major operations (bill processed successfully, etc.)
- **DEBUG**: Detailed steps (image encoded, LLM response received, etc.)
- **WARNING**: Non-critical issues
- **ERROR**: Failures with full exception traceback

## Configuration Customization

### Custom Bill Types

```python
entity = AgentReadingBillsEntity(
    supported_bill_types=["utility", "telecom", "insurance"]  # Only these types
)
```

### Custom Redaction Fields

```python
custom_redaction = ["name", "address", "phone"]  # Minimal redaction
entity = AgentReadingBillsEntity(
    redaction_fields=custom_redaction
)
```

### Custom Model

```python
entity = AgentReadingBillsEntity(
    model_name="gpt-4-turbo-vision",  # Different model if available
    api_key="sk-..."  # Explicit API key
)
```

## Project Structure

```
agent_reading_bills/
├── entities/
│   ├── __init__.py
│   ├── base_entity.py              # Core model state
│   └── agent_reading_bills_entity.py # Bill-specific config + prompts
├── services/
│   ├── __init__.py
│   ├── base_service.py             # Core operations
│   └── agent_reading_bills_service.py # Bill reading operations
├── schemas/
│   ├── __init__.py
│   └── bill_schema.py              # Output data structures
├── tests/
│   └── __init__.py
├── main.py                         # Example usage
└── README.md                       # This file
```

## Testing

Unit tests with mocked OpenAI API responses are provided in the `tests/` folder:

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=agent_reading_bills
```

Tests verify:
- Entity initialization and configuration
- Service validation and error handling
- Image processing
- Data redaction logic
- JSON formatting and schema compliance

## API Usage Costs

**Important**: Each bill image analysis incurs a charge from OpenAI:
- GPT-4 Vision charges per image token (approximately $0.01-0.03 per image)
- Monitor your usage: https://platform.openai.com/account/billing/overview

### Cost Optimization Tips
1. **Batch Processing**: Process multiple bills in bulk if possible
2. **Image Quality**: Ensure bills are clear and readable to reduce token usage
3. **Monitoring**: Track API costs in `main.py` before scaling to production
4. **Rate Limiting**: Implement rate limiting for high-volume processing

## Troubleshooting

### "API key not provided" error
```bash
# Make sure OPENAI_API_KEY environment variable is set
export OPENAI_API_KEY=sk-...

# Or pass it directly
entity = AgentReadingBillsEntity(api_key="sk-...")
```

### "Unsupported image format" error
Supported formats: JPG, PNG, GIF, WEBP
```python
# Ensure your image is in a supported format
# You may need to convert: PNG → JPG, PDF → PNG first
```

### "API request failed" errors
- Check your API key is valid
- Verify you have GPT-4 Vision access (may need to request enable)
- Check rate limits haven't been exceeded
- Ensure network connectivity

### LLM response isn't JSON
- The model may occasionally return non-JSON responses
- The service will capture this as an error in `redaction_notes`
- Try with a clearer bill image
- Consider refining the prompt templates in `AgentReadingBillsEntity`

## Future Enhancements

Potential improvements for future versions:

1. **Async Processing**: Support concurrent bill processing with `asyncio`
2. **Image Preprocessing**: Auto-rotate, enhance contrast, deskew before API call
3. **Caching**: Cache responses for identical bill images
4. **Batch API**: Use OpenAI's batch processing API for cost savings
5. **Alternative LLMs**: Support Claude 3, Gemini, or other vision models
6. **Database**: Store results for auditing and historical tracking
7. **Web Interface**: REST API for remote bill processing
8. **Mobile Support**: Capture bills directly from phone camera

## Contributing

To contribute improvements:

1. Follow the existing code structure and naming conventions
2. Add type hints to all new functions
3. Include docstrings with examples
4. Add unit tests for new functionality
5. Update this README with any new features

## License

This project is provided as-is. Ensure compliance with OpenAI's API usage terms.

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review example usage in `main.py`
3. Check log output for detailed error messages
4. Verify your OpenAI API configuration

## Version History

- **v1.0.0**: Initial release with GPT-4 Vision support
  - Bill image analysis and service extraction
  - Personal data redaction (50+ field types)
  - Structured JSON output
  - Comprehensive logging

---

Built with ❤️ using OpenAI's GPT-4 Vision API
