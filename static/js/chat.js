// Chat functionality
const chatState = {
    currentChatId: null,
    isProcessing: false
};

document.addEventListener('DOMContentLoaded', function() {
    // Message form handling
    const messageForm = document.getElementById('messageForm');
    const messageInput = document.getElementById('messageInput');
    const chatMessages = document.getElementById('chatMessages');

    // New chat handling
    const newChatButton = document.getElementById('newChat');
    newChatButton?.addEventListener('click', async () => {
        if (chatState.isProcessing) return;
        chatState.isProcessing = true;

        try {
            const response = await fetch('/chat/new', {
                method: 'POST'
            });
            const data = await response.json();
            if (response.ok) {
                chatState.currentChatId = data.chat_id;
                clearMessages();
                location.reload();
            } else {
                showError(data.error || 'Failed to create new chat');
            }
        } catch (error) {
            showError('Failed to create new chat: ' + error.message);
        } finally {
            chatState.isProcessing = false;
        }
    });

    messageForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!chatState.currentChatId) {
            showError('Please select or create a chat first');
            return;
        }

        if (chatState.isProcessing) return;
        const message = messageInput.value.trim();
        if (!message) return;

        chatState.isProcessing = true;
        // Add user message to chat
        appendMessage('user', message);
        messageInput.value = '';
        messageInput.disabled = true;

        try {
            const response = await fetch(`/chat/${chatState.currentChatId}/message`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });
            const data = await response.json();
            
            if (response.ok) {
                appendMessage('assistant', data.message);
            } else {
                if (response.status === 429) {
                    appendMessage('system', 'Rate limit exceeded. Please wait a moment before trying again.');
                } else {
                    appendMessage('system', data.error || 'Failed to send message');
                }
            }
        } catch (error) {
            appendMessage('system', 'Failed to send message: ' + error.message);
        } finally {
            chatState.isProcessing = false;
            messageInput.disabled = false;
            messageInput.focus();
        }
    });

    // Chat selection handling
    document.querySelectorAll('[data-chat-id]').forEach(element => {
        element.addEventListener('click', async (e) => {
            e.preventDefault();
            if (chatState.isProcessing) return;
            
            const chatId = element.dataset.chatId;
            if (chatState.currentChatId === chatId) return;
            
            chatState.isProcessing = true;
            chatState.currentChatId = chatId;
            clearMessages();
            
            try {
                const response = await fetch(`/chat/${chatId}/messages`);
                const data = await response.json();
                if (response.ok) {
                    data.messages.forEach(msg => {
                        appendMessage(msg.role, msg.content);
                    });
                } else {
                    throw new Error(data.error || 'Failed to load messages');
                }
            } catch (error) {
                appendMessage('system', 'Failed to load chat history: ' + error.message);
            } finally {
                chatState.isProcessing = false;
            }
        });
    });
});

function appendMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}-message`;
    
    const roleDisplay = {
        'user': 'You',
        'assistant': 'SUPPLY DROP AI',
        'system': 'System'
    }[role];
    
    messageDiv.innerHTML = `
        <div class="message-content p-4 rounded-lg shadow-md ${
            role === 'user' ? 'bg-blue-600 text-white ml-auto max-w-[80%]' :
            role === 'assistant' ? 'bg-white border border-gray-200 mr-auto max-w-[80%]' :
            'bg-gray-100 text-gray-600 mx-auto max-w-[90%] text-center'
        }">
            <div class="flex items-center gap-2">
                <strong class="text-sm ${role === 'user' ? 'text-gray-100' : 'text-gray-600'}">${roleDisplay}</strong>
            </div>
            <p class="mt-2 ${role === 'user' ? 'text-white' : 'text-gray-800'} whitespace-pre-wrap">${content}</p>
        </div>
    `;
    
    const chatMessages = document.getElementById('chatMessages');
    chatMessages?.appendChild(messageDiv);
    chatMessages?.scrollTo({
        top: chatMessages.scrollHeight,
        behavior: 'smooth'
    });
}

function clearMessages() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.innerHTML = '';
    }
}

function showError(message) {
    appendMessage('system', message);
}
