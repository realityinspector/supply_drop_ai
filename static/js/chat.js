// Chat functionality
let currentConversationId = null;
let messageHistory = [];

// Helper function to handle API responses
async function handleResponse(response, errorMessage) {
    if (!response.ok) {
        const data = await response.json();
        console.error(`${errorMessage}:`, data.error || response.statusText);
        throw new Error(data.error || response.statusText);
    }
    return response.json();
}

// Function to send a message
async function sendMessage(content) {
    if (!content.trim()) return;
    
    try {
        if (!currentConversationId) {
            console.log("No active conversation, creating new one...");
            const newChat = await createNewChat();
            if (!newChat) return;
        }

        console.log("Sending message to conversation:", currentConversationId);
        const response = await fetch(`/abbot/api/conversations/${currentConversationId}/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ 
                content,
                message_history: messageHistory // Send message history for context
            }),
            credentials: 'same-origin'
        });
        
        const result = await handleResponse(response, 'Error sending message');
        console.log("Message sent:", result);
        
        // Update message history
        if (result.user_message) {
            messageHistory.push({
                role: 'user',
                content: result.user_message.content
            });
        }
        if (result.ai_message) {
            messageHistory.push({
                role: 'assistant',
                content: result.ai_message.content
            });
        }
        
        await loadMessages(currentConversationId);
        return result;
    } catch (error) {
        console.error('Error sending message:', error);
        alert('Error sending message: ' + error.message);
    }
}

// Create new chat and immediately load it
async function createNewChat() {
    try {
        console.log("Creating new chat...");
        const response = await fetch('/abbot/api/conversations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                title: 'New Conversation'
            }),
            credentials: 'same-origin'
        });
        
        const data = await handleResponse(response, 'Error creating chat');
        console.log("New chat created:", data);
        await loadMessages(data.id);
        return data;
    } catch (error) {
        console.error('Error creating new chat:', error);
        document.getElementById('chat-title').textContent = 'Error: ' + error.message;
    }
}

// Load conversations
async function loadConversations() {
    try {
        console.log("Loading conversations...");
        const response = await fetch('/abbot/api/conversations', {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        });
        
        const conversations = await handleResponse(response, 'Error loading conversations');
        console.log("Conversations loaded:", conversations);
        
        const list = document.getElementById('conversation-list');
        if (!list) {
            console.error('Conversation list element not found');
            return;
        }

        list.innerHTML = conversations.map(conv => `
            <div class="conversation-item p-4 hover:bg-gray-100 cursor-pointer ${currentConversationId === conv.id ? 'bg-gray-100' : ''}"
                 data-id="${conv.id}">
                <div class="font-medium">${conv.title}</div>
                <div class="text-sm text-gray-500">${new Date(conv.updated_at).toLocaleString()}</div>
            </div>
        `).join('');

        // Add click handlers
        document.querySelectorAll('.conversation-item').forEach(item => {
            item.addEventListener('click', () => loadMessages(item.dataset.id));
        });

        // If there are no conversations, create a new one
        if (conversations.length === 0) {
            console.log("No conversations found, creating a new one...");
            await createNewChat();
        } else if (!currentConversationId) {
            // If there are conversations but none is selected, load the most recent one
            console.log("Loading most recent conversation...");
            await loadMessages(conversations[0].id);
            }
        } catch (error) {
        console.error('Error loading conversations:', error);
        const list = document.getElementById('conversation-list');
        if (list) {
            list.innerHTML = `
                <div class="p-4 text-red-500">
                    Error loading conversations: ${error.message}
                </div>
            `;
        }
    }
}

// Load messages for a conversation
async function loadMessages(conversationId) {
    try {
        console.log("Loading messages for conversation:", conversationId);
        currentConversationId = conversationId;
        const response = await fetch(`/abbot/api/conversations/${conversationId}/messages`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        });
        
        const messages = await handleResponse(response, 'Error loading messages');
        console.log("Messages loaded:", messages);
        
        const thread = document.getElementById('message-thread');
        if (!thread) {
            console.error('Message thread element not found');
            return;
        }

        thread.innerHTML = messages.map(msg => `
            <div class="message ${msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'}">
                <div class="max-w-3/4 ${msg.role === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-200'} rounded-lg px-4 py-2">
                    ${msg.content}
                    <div class="text-xs ${msg.role === 'user' ? 'text-blue-100' : 'text-gray-500'} mt-1">
                        ${new Date(msg.created_at).toLocaleString()}
                    </div>
                </div>
            </div>
        `).join('');
        thread.scrollTop = thread.scrollHeight;
        
        // Update chat title
        const titleElement = document.getElementById('chat-title');
        if (titleElement) {
            titleElement.textContent = `Chat ${conversationId}`;
            }
        } catch (error) {
        console.error('Error loading messages:', error);
        const thread = document.getElementById('message-thread');
        if (thread) {
            thread.innerHTML = `
                <div class="p-4 text-red-500">
                    Error loading messages: ${error.message}
                </div>
            `;
        }
    }
}

// Initialize event listeners when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log("Initializing chat event listeners...");
    
    // Message form submission
    const messageForm = document.getElementById('message-form');
    const messageInput = document.getElementById('message-input');
    
    if (messageForm && messageInput) {
        // Handle form submission
        messageForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const content = messageInput.value.trim();
            messageInput.value = '';
            await sendMessage(content);
        });
        
        // Handle Enter key
        messageInput.addEventListener('keydown', async (e) => {
            // Send on Enter without Shift key
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const content = messageInput.value.trim();
                messageInput.value = '';
                await sendMessage(content);
            }
        });

        // Character counter
        messageInput.addEventListener('input', (e) => {
            const charCount = document.getElementById('char-count');
            if (charCount) {
                const count = e.target.value.length;
                const historyCount = messageHistory.reduce((acc, msg) => acc + msg.content.length, 0);
                charCount.textContent = `${count} (${historyCount} in history)`;
            }
        });
    }

    // New Chat button
    const newChatButton = document.getElementById('new-chat');
    if (newChatButton) {
        newChatButton.addEventListener('click', async () => {
            messageHistory = []; // Clear message history for new chat
            await createNewChat();
        });
    }

    // Initial load
    loadConversations().catch(error => {
        console.error('Error during initialization:', error);
        const titleElement = document.getElementById('chat-title');
        if (titleElement) {
            titleElement.textContent = 'Error: ' + error.message;
        }
    });
});
