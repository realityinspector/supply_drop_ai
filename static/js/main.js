// Common utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Auto-resize textarea
function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = (textarea.scrollHeight) + 'px';
}

// Format timestamps
function formatTimestamp(timestamp) {
    return new Date(timestamp).toLocaleString();
}

// Show loading state
function showLoading(button) {
    const originalText = button.textContent;
    button.disabled = true;
    button.innerHTML = `
        <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        Loading...
    `;
    return originalText;
}

// Hide loading state
function hideLoading(button, originalText) {
    button.disabled = false;
    button.textContent = originalText;
}

// Export common functions
window.utils = {
    debounce,
    autoResizeTextarea,
    formatTimestamp,
    showLoading,
    hideLoading
}; 