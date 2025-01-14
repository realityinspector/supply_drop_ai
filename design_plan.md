# Simplified Emergency Assistance App Design Plan

## Overview
A streamlined application with two focused interfaces:
1. REJECTION SIMULATION - Mock rejection analysis for insurance documents
2. RESOURCE FINDER - Chatbot for finding emergency resources

## Core Principles
- No user accounts or authentication
- No data persistence beyond current session
- No chat history storage
- Simplified, focused interfaces

## Technical Architecture

### Components to Remove
- User authentication system
- Database storage for chats/users
- Chat history features
- Profile system
- Multiple analysis types
- FEMA form wizard

### New Structure
```
├── app.py              # Main Flask application
├── rejection.py        # Rejection simulation logic
├── resource_finder.py  # Resource finder chatbot
├── document_processor.py # Document analysis (simplified)
├── templates/
│   ├── base.html
│   ├── dashboard.html      # Landing page
│   ├── rejection/
│   │   └── wizard.html     # Single-page rejection analysis
│   └── resources/
│       └── chat.html       # Resource finder interface
└── static/
    ├── css/
    │   └── main.css
    └── js/
        ├── rejection.js
        └── resource-chat.js
```

### Dashboard Interface
```
+--------------------------------+
|           Dashboard            |
|                               |
|   +----------------------+    |
|   |  REJECTION          |    |
|   |  SIMULATION         |    |
|   +----------------------+    |
|                               |
|   +----------------------+    |
|   |  RESOURCE           |    |
|   |  FINDER            |    |
|   +----------------------+    |
+--------------------------------+
```

## Rejection Simulation
- Single-page wizard interface
- Document upload
- 25-point rejection analysis
- Results display
- No data persistence
- Clear session on completion

## Resource Finder
- Simple chat interface
- No history storage
- Clear session on page leave
- Focus on immediate assistance
- Real-time resource lookup

## Implementation Steps

1. **Clean Up Phase**
   - Remove authentication system
   - Remove database models and migrations
   - Remove chat history features
   - Remove profile system
   - Remove FEMA wizard

2. **New Dashboard**
   - Create simplified landing page
   - Add direct links to both tools
   - Remove navigation complexity

3. **Rejection Simulation**
   - Simplify to single analysis type
   - Create focused upload interface
   - Implement stateless analysis
   - Add clear results display

4. **Resource Finder**
   - Implement simple chat interface
   - Remove persistence features
   - Focus on immediate responses
   - Add session cleanup

## Technical Specifications

### Session Management
```python
class SessionManager:
    def clear_session():
        # Remove all stored data
        session.clear()
    
    def store_temp_analysis(analysis_data):
        # Store only during active analysis
        session['current_analysis'] = analysis_data
```

### Document Flow
1. Upload document
2. Process immediately
3. Return results
4. Clear data

### Chat Flow
1. Receive message
2. Process with current context
3. Return response
4. Maintain only current session data

## Security
- No user data storage
- Session-only temporary storage
- Regular session clearing
- Input sanitization
- Rate limiting

## Testing Focus
- Document processing accuracy
- Session management
- Memory usage
- Load testing
- Security validation
