# Emergency Preparedness Application

A Flask-based application for emergency preparedness, document management, and insurance analysis.

## Technical Stack

- **Backend**: Flask 2.0+, Python 3.9+
- **Database**: SQLAlchemy 1.4+, Alembic for migrations
- **Authentication**: Auth0
- **AI Integration**: OpenAI GPT-4
- **Frontend**: HTML, CSS, JavaScript
- **Payment Processing**: Stripe
- **Email**: Mailgun

## Project Structure

```
├── app.py                 # Application factory and configuration
├── auth.py               # Authentication routes and utilities
├── chat.py              # Chat functionality and analysis routes
├── database.py          # Database configuration
├── document_processor.py # Document processing and analysis
├── extensions.py        # Flask extensions
├── models.py            # Database models
├── prompts.json         # AI system prompts configuration
└── templates/           # Jinja2 templates
```

## Key Components

### Document Processing System

The application includes a sophisticated document processing system with the following features:

1. **File Support**:
   - PDF documents (using PyPDF2)
   - Microsoft Word (DOCX)
   - Plain text files

2. **Processing Types**:
   - Text extraction
   - Document summarization
   - Content analysis
   - Insurance requirement extraction

3. **AI System Prompts**:
   - Centralized prompt management in `prompts.json`
   - Modular prompt configuration for different analysis types
   - Context-aware analysis with history tracking
   - Progressive analysis capabilities

### Insurance Document Analysis

The system provides four specialized analysis functions for insurance documents, each generating exactly 25 unique insights:

1. **Policy Explanation**
   - Generates 25 key policy points organized by priority
   - Sequential numbering across priority levels
   - Focuses on coverage details, limitations, and obligations
   - Provides clear, actionable information

2. **Coverage Enhancement**
   - Suggests 25 unique additional coverage items
   - Organized into high, medium, and low priorities
   - Based on industry best practices
   - Progressive analysis (can generate new unique points based on previous analyses)

3. **Mock Rejection Analysis**
   - Lists 25 potential rejection reasons
   - Prioritized by severity and impact
   - Analyzes compliance issues and documentation gaps
   - Identifies coverage mismatches with specific references

4. **Language & Strategic Review**
   - Comprehensive spelling and grammar analysis
   - Strategic tone and clarity assessment
   - Tactical and strategic improvement recommendations
   - Organized by priority and impact

### Analysis Features

- **Progressive Analysis**: Each analysis can build upon previous analyses, ensuring new and unique insights
- **Priority-Based Organization**: Items are categorized into high, medium, and low priorities
- **Sequential Numbering**: Maintains consistent 1-25 numbering across all priority sections
- **Context Awareness**: Takes into account previous analyses to avoid repetition
- **JSON Response Format**: Structured output for consistent UI rendering
- **Error Handling**: Comprehensive error catching and user feedback

### Session Management

- Workflow state tracking for multi-step processes
- Document reuse capabilities
- Analysis history preservation
- Context-aware analysis suggestions

## Database Features

- SQLAlchemy ORM for database operations
- Alembic migrations for schema management
- Relationship mapping between models:
  - User
  - Document
  - Chat
  - Message
  - InsuranceClaim
  - InsuranceRequirement

## Security Features

- Auth0 integration for authentication
- Environment-based configuration
- Secure file handling
- API key management
- Session-based workflow protection

## Error Handling

- Comprehensive exception handling
- JSON parsing validation
- Graceful error responses
- Detailed logging
- User-friendly error messages

## Getting Started

1. Clone the repository
2. Install dependencies:
   ```bash
   poetry install
   ```
3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```
4. Initialize the database:
   ```bash
   flask db upgrade
   ```
5. Run the development server:
   ```bash
   flask run
   ```

## Development

1. Install development dependencies:
   ```bash
   poetry install --dev
   ```
2. Run tests:
   ```bash
   pytest
   ```
3. Code formatting:
   ```bash
   black .
   flake8
   mypy .
   ```

## Configuration

The application uses various configuration sources:

1. Environment variables (see `.env.example`)
2. Auth0 configuration
3. OpenAI API configuration
4. AI system prompts (`prompts.json`)
5. Document processing settings

## API Documentation

The application provides several REST endpoints for document analysis:

### Insurance Analysis Endpoints

- `POST /insurance/analyze`
  - Analyzes insurance documents
  - Supports multiple analysis types
  - Returns structured JSON responses
  - Handles progressive analysis requests

### Document Management Endpoints

- `POST /insurance/upload-requirements`
- `POST /insurance/upload-claim`
- `GET /insurance/wizard`

For full API documentation, see [API Documentation]

## Contributing

[Contributing guidelines]

## License

[License information]
