let currentChatId = null;

document.addEventListener('DOMContentLoaded', function() {
    // Document upload handling
    const uploadForm = document.getElementById('uploadForm');
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fileInput = document.getElementById('document');
        const file = fileInput.files[0];
        if (!file) return;

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
            alert('Upload failed');
        }
    });

    // New chat handling
    document.getElementById('newChat').addEventListener('click', async () => {
        try {
            const response = await fetch('/chat/new', {
                method: 'POST'
            });
            const data = await response.json();
            currentChatId = data.chat_id;
            clearMessages();
            location.reload();
        } catch (error) {
            alert('Failed to create new chat');
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
                alert(data.error || 'Failed to send message');
            }
        } catch (error) {
            alert('Failed to send message');
        }
    });

    // Chat selection handling
    document.querySelectorAll('[data-chat-id]').forEach(element => {
        element.addEventListener('click', (e) => {
            e.preventDefault();
            currentChatId = element.dataset.chatId;
            clearMessages();
            // Here you could load previous messages for this chat
        });
    });
});

function appendMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}-message mb-3`;
    messageDiv.innerHTML = `
        <div class="message-content p-3 rounded">
            <strong>${role === 'user' ? 'You' : 'Assistant'}:</strong>
            <p class="mb-0">${content}</p>
        </div>
    `;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function clearMessages() {
    chatMessages.innerHTML = '';
}
