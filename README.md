# Supply Drop AI - Emergency Preparedness Assistant

A Flask-based web application that provides emergency preparedness and disaster response assistance through AI-powered chat interactions, document processing, and insurance requirement analysis.

## Features

- 🤖 AI-powered chat assistance for emergency preparedness
- 📄 Document processing and analysis
- 📋 Insurance requirement analysis and claim processing
- 👤 User profile management
- 📊 Activity reporting and analytics

## Project Structure

### Core Application Files

- `app.py` - Main application factory and configuration
- `main.py` - Application entry point
- `extensions.py` - Flask extensions initialization (SQLAlchemy, Login Manager)

### Authentication and User Management

- `auth.py` - User authentication routes (login, signup, logout)
- `models.py` - Database models (User, Chat, Message, Document, Insurance models)
- `profile.py` - User profile management and reporting

### Chat and Document Processing

- `chat.py` - Chat functionality and message handling
- `document_processor.py` - Document processing and analysis using OpenAI
- `database.py` & `database_manager.py` - Database connection and management

### Templates and Static Files

- `/templates` - HTML templates for the web interface
- `/static` - Static assets (CSS, JavaScript, images)

## Technical Stack

- **Framework**: Flask
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: Flask-Login
- **AI Integration**: OpenAI GPT-4
- **Document Processing**: PyPDF2, python-docx
- **Frontend**: HTML, CSS, JavaScript

## Key Components

### Database Models

- `User`: User account management and profile information
- `Chat`: Chat session management
- `Message`: Individual chat messages
- `Document`: Document storage and processing
- `InsuranceRequirement`: Insurance requirement tracking
- `InsuranceClaim`: Insurance claim processing
- `Report`: User activity and analysis reporting

### Core Functionality

1. **Chat System**
   - Real-time AI interactions
   - Context-aware responses
   - Credit-based usage tracking

2. **Document Processing**
   - PDF, DOCX, and TXT file support
   - Content extraction and analysis
   - Insurance document specialization

3. **Insurance Analysis**
   - Requirement extraction
   - Claim analysis
   - Compliance checking
   - Enhancement suggestions

4. **User Management**
   - Secure authentication
   - Profile customization
   - Activity tracking
   - Credit system

5. **Reporting**
   - Activity reports
   - Document analysis
   - Usage statistics

## Dependencies

```toml
[project]
name = "repl-nix-docchatgpt"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "flask>=3.1.0",
    "flask-sqlalchemy>=3.1.1",
    "flask-login>=0.6.3",
    "openai>=1.54.4",
    "python-docx>=1.1.2",
    "pypdf2>=3.0.1",
    "psycopg2-binary>=2.9.10",
    "sqlalchemy>=2.0.36",
    "email-validator>=2.2.0",
    "werkzeug>=3.1.3",
    "docx>=0.2.4"
]
```

## Database Features

- Connection pooling
- Automatic recovery
- Health monitoring
- Transaction management
- Connection state tracking

## Security Features

- Password hashing
- Session management
- Rate limiting
- Secure file handling
- Credit system for API usage

## Error Handling

- Comprehensive logging
- Graceful degradation
- Automatic recovery
- User feedback
- Transaction rollback

## Getting Started

1. Clone the repository
2. Install dependencies: `pip install -e .`
3. Set up environment variables:
   - `FLASK_SECRET_KEY`
   - `DATABASE_URL`
   - `OPENAI_API_KEY`
4. Initialize database: `flask db upgrade`
5. Run the application: `python main.py`

## Development

The application uses a robust development setup with:

- Comprehensive logging
- Database connection monitoring
- Automatic database recovery
- Development server with debug mode
- SQLAlchemy ORM for database operations

## Production Considerations

- Configure proper database connection pooling
- Set up proper logging
- Configure proper security headers
- Use production-grade WSGI server
- Set up proper monitoring
- Configure backup systems
- Set up proper error reporting
