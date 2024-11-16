let currentChatId = null;

document.addEventListener('DOMContentLoaded', function() {
    // Document upload handling
    const uploadForm = document.getElementById('uploadForm');
    const MAX_FILE_SIZE = 16 * 1024 * 1024; // 16MB in bytes

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fileInput = document.getElementById('document');
        const file = fileInput.files[0];
        if (!file) {
            alert('Please select a file');
            return;
        }

        if (file.size > MAX_FILE_SIZE) {
            alert('File size exceeds 16MB limit');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (response.ok) {
                alert('Document uploaded successfully');
                fileInput.value = '';
            } else {
                alert(data.error || 'Upload failed');
            }
        } catch (error) {
            alert('Upload failed: ' + error.message);
        }
    });

    // New chat handling
    document.getElementById('newChat').addEventListener('click', async () => {
        try {
            const response = await fetch('/chat/new', {
                method: 'POST'
            });
            const data = await response.json();
            if (response.ok) {
                currentChatId = data.chat_id;
                clearMessages();
                location.reload();
            } else {
                alert(data.error || 'Failed to create new chat');
            }
        } catch (error) {
            alert('Failed to create new chat: ' + error.message);
        }
    });

    // Message form handling
    const messageForm = document.getElementById('messageForm');
    const messageInput = document.getElementById('messageInput');
    const chatMessages = document.getElementById('chatMessages');

    messageForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!currentChatId) {
            alert('Please select or create a chat first');
            return;
        }

        const message = messageInput.value.trim();
        if (!message) return;

        // Add user message to chat
        appendMessage('user', message);
        messageInput.value = '';
        messageInput.disabled = true;

        try {
            const response = await fetch(`/chat/${currentChatId}/message`, {
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
            messageInput.disabled = false;
            messageInput.focus();
        }
    });

    // Chat selection handling
    document.querySelectorAll('[data-chat-id]').forEach(element => {
        element.addEventListener('click', async (e) => {
            e.preventDefault();
            const chatId = element.dataset.chatId;
            if (currentChatId === chatId) return;
            
            currentChatId = chatId;
            clearMessages();
            
            try {
                const response = await fetch(`/chat/${chatId}/messages`);
                const data = await response.json();
                if (response.ok) {
                    data.messages.forEach(msg => {
                        appendMessage(msg.role, msg.content);
                    });
                }
            } catch (error) {
                appendMessage('system', 'Failed to load chat history');
            }
        });
    });
});

function appendMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}-message mb-3`;
    const roleDisplay = {
        'user': 'You',
        'assistant': 'Assistant',
        'system': 'System'
    }[role];
    
    messageDiv.innerHTML = `
        <div class="message-content p-3 rounded">
            <strong>${roleDisplay}:</strong>
            <p class="mb-0">${content}</p>
        </div>
    `;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function clearMessages() {
    chatMessages.innerHTML = '';
}
