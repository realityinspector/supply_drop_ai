# Emergency Preparedness Assistant

An open-source Flask application providing AI-powered tools for disaster preparedness and recovery. Built in response to Hurricane Helene's impact on Western North Carolina and Los Angeles fires.

## Core Features

- **Resource Finder**: OpenAI-powered chatbot for locating emergency resources and community support
- **Rejection Simulation**: AI system that simulates application reviews for insurance claims, FEMA assistance, and grants
- **Toxicity Assessment**: Environmental health analysis tool for evaluating potential exposure risks
- **Recovery Capital Finder**: Financial advisor bot for discovering disaster recovery funding sources

## Technical Stack

- **Backend**: Flask (Python 3.9+)
- **Frontend**: Bootstrap 5 with vanilla JavaScript
- **AI Integration**: OpenAI GPT-4 API
- **PDF Processing**: PyPDF (for document analysis)
- **Security**: Flask-WTF for CSRF protection
- **Input Sanitization**: Bleach for text sanitization

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/realityinspector/supply_drop_ai.git
cd supply_drop_ai
```

2. Set up Python environment (using Poetry):
```bash
poetry install
```

3. Configure environment variables:
```bash
FLASK_SECRET_KEY=your_secret_key
OPENAI_API_KEY=your_openai_key
UPLOAD_FOLDER=./uploads
```

4. Run the development server:
```bash
poetry run flask run
```

## Project Structure

- `main.py`: Core Flask application and route handlers
- `templates/`: Jinja2 templates for web interface
  - `base.html`: Base template with common layout
  - `index.html`: Landing page
  - Various feature-specific templates
- `static/`: Static assets (CSS, images, videos)
- `*_prompt.json`: System prompts for different AI features

## Contributing

### Architecture Decisions

1. **Stateless Design**: No database/persistent storage to minimize security concerns
2. **File Processing**: Temporary file storage with secure cleanup
3. **AI Integration**: Modular prompt system for easy updates
4. **Security First**: CSRF protection, input sanitization, and file upload restrictions

### Development Guidelines

1. **Code Style**
   - Follow PEP 8
   - Use type hints
   - Document functions and complex logic
   - Keep functions focused and modular

2. **Security Practices**
   - Sanitize all user inputs
   - Validate file uploads
   - Use secure file operations
   - Never commit API keys

3. **AI Integration**
   - Keep prompts in separate JSON files
   - Test with various input scenarios
   - Handle API failures gracefully
   - Monitor token usage

4. **Testing**
   - Write unit tests for new features
   - Test edge cases in file processing
   - Verify prompt effectiveness
   - Check security measures

### Current Development Focus

1. Video damage analysis integration
2. Resource API development
3. Community event coordination features
4. Performance optimization for file processing

## License

[License information needed]

## Security Notice

This is a prototype system. While we implement security best practices, contributors should be aware that this system processes sensitive disaster-related information. Always review security implications of changes.

## Contact

[Contact information needed]
