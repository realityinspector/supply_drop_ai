# Abbot AI Feature Design Plan

## Overview
Abbot AI is a context-aware chat interface that provides wildfire relief assistance using a persistent chat model with memory management. The system maintains chat context up to 250,000 characters and provides a user-friendly interface with conversation history.

## Technical Architecture

### Database Schema Extensions
```sql
-- New tables for Abbot AI
CREATE TABLE abbot_conversations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_archived BOOLEAN DEFAULT FALSE
);

CREATE TABLE abbot_messages (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER REFERENCES abbot_conversations(id),
    role VARCHAR(50),  -- 'user' or 'assistant'
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    token_count INTEGER
);
```

### Components

1. **Chat Interface**
   - Left sidebar: Conversation history list
   - Main chat window: Message thread
   - Input area: Message composition
   - Context management system

2. **Context Management**
   - Rolling context window of 250,000 characters
   - Automatic pruning of older messages when limit is reached
   - Context persistence across sessions
   - Token counting and management

3. **Frontend Components**
   ```javascript
   // Key components needed
   - ConversationList.js    // Left sidebar component
   - ChatWindow.js          // Main chat interface
   - MessageThread.js       // Message display
   - MessageComposer.js     // Input component
   - ContextManager.js      // Context handling
   ```

4. **Backend Routes**
   ```python
   @app.route('/api/abbot/conversations', methods=['GET'])
   @app.route('/api/abbot/conversations', methods=['POST'])
   @app.route('/api/abbot/conversations/<int:conv_id>/messages', methods=['GET'])
   @app.route('/api/abbot/conversations/<int:conv_id>/messages', methods=['POST'])
   ```

## User Interface Design

### Layout
```
+----------------+---------------------------+
|                |                          |
| Conversations  |      Chat Window         |
| List           |                          |
|                |                          |
| [Recent Chat]  |    [Message Thread]      |
| [Older Chat]   |                          |
| [...]          |                          |
|                |                          |
|                |    [Input Area]          |
+----------------+---------------------------+
```

### Features
1. **Conversation List**
   - Displays conversation titles
   - Shows preview of last message
   - Timestamp of last activity
   - Unread message indicators
   - Search/filter capabilities

2. **Chat Window**
   - Message bubbles with clear user/AI distinction
   - Timestamp for each message
   - Markdown support for formatted responses
   - Code block formatting
   - Auto-scroll to bottom
   - Loading states

3. **Input Area**
   - Rich text editor
   - Send button
   - Character count
   - Context size indicator

## Implementation Plan

### Phase 1: Core Infrastructure
1. Database schema implementation
2. Basic API endpoints
3. Context management system
4. System prompt integration

### Phase 2: UI Implementation
1. Basic chat interface
2. Conversation list
3. Message threading
4. Real-time updates

### Phase 3: Enhanced Features
1. Search functionality
2. Conversation management
3. Context visualization
4. Performance optimizations

## Technical Specifications

### Context Management
```python
class ContextManager:
    MAX_CONTEXT_SIZE = 250000
    
    def add_message(self, message):
        # Add new message to context
        # Prune if necessary
        pass
    
    def get_context(self):
        # Return current context window
        pass
    
    def prune_context(self):
        # Remove oldest messages until under limit
        pass
```

### Message Flow
1. User sends message
2. Context manager validates size
3. If needed, prunes older messages
4. Adds new message to context
5. Sends to AI with current context
6. Stores response
7. Updates UI

## Security Considerations
1. User authentication required
2. Message encryption at rest
3. Rate limiting
4. Input sanitization
5. Context isolation between users

## Testing Strategy
1. Unit tests for context management
2. Integration tests for chat flow
3. UI component testing
4. Load testing for context handling
5. Security testing

## Monitoring and Maintenance
1. Context size metrics
2. Response times
3. Error rates
4. User engagement metrics
5. System resource usage
