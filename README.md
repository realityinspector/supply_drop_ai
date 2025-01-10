# Emergency Preparedness Application

A Flask-based application for emergency preparedness, document management, and insurance analysis.

## Technical Stack

- **Backend**: Flask 2.0+, Python 3.9+
- **Database**: SQLAlchemy 1.4+, Alembic for migrations
- **Authentication**: Auth0
- **AI Integration**: OpenAI GPT-4o
- **Frontend**: HTML, CSS, JavaScript
- **Payment Processing**: Stripe
- **Email**: Mailgun

## Project Structure

```
├── app.py                 # Application factory and configuration
├── auth.py               # Authentication routes and utilities
├── chat.py              # Chat functionality
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
   - PDF documents
   - Microsoft Word (DOCX)
   - Plain text files

2. **Processing Types**:
   - Text extraction
   - Document summarization
   - Content analysis
   - Insurance requirement extraction

3. **AI System Prompts**:
   - Centralized prompt management in `prompts.json`
   - Modular prompt configuration for different analysis types:
     - Document summarization
     - Document analysis
     - Insurance requirements
     - Insurance analysis (explain, enhance, mock rejection, language)

### Insurance Document Analysis

The system provides four specialized analysis functions for insurance documents:

1. **Policy Explanation**
   - Identifies 25 most important policy points
   - Focuses on coverage details, limitations, and obligations
   - Presents clear, actionable information

2. **Coverage Enhancement**
   - Suggests 25 additional coverage items
   - Based on industry best practices
   - Includes risk management strategies

3. **Mock Rejection Analysis**
   - Provides 25 potential rejection reasons
   - Analyzes compliance issues and documentation gaps
   - Identifies coverage mismatches

4. **Language & Strategic Review**
   - Comprehensive spelling and grammar analysis
   - Strategic tone and clarity assessment
   - Tactical and strategic improvement recommendations

## Database Features

- SQLAlchemy ORM for database operations
- Alembic migrations for schema management
- Relationship mapping between models:
  - User
  - Community
  - Page
  - Event
  - EventRegistration
  - Revision
  - Kit

## Security Features

- Auth0 integration for authentication
- Environment-based configuration
- Secure file handling
- API key management

## Error Handling

- Comprehensive exception handling
- Graceful error responses
- Detailed logging

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

## Production Deployment

1. Set production environment variables
2. Configure web server (e.g., Gunicorn)
3. Set up database backups
4. Configure SSL certificates
5. Set up monitoring

## Configuration

The application uses various configuration sources:

1. Environment variables (see `.env.example`)
2. Auth0 configuration
3. Stripe integration
4. Email service (Mailgun)
5. AI system prompts (`prompts.json`)

## API Documentation

[Link to API documentation]

## Contributing

[Contributing guidelines]

## License

[License information]
