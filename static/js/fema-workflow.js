// Common utility functions for the FEMA workflow

// Handle file validation
function validateFile(file) {
    const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
    const maxSize = 10 * 1024 * 1024; // 10MB

    if (!file) {
        throw new Error('No file selected');
    }

    if (!allowedTypes.includes(file.type)) {
        throw new Error('Invalid file type. Please upload a PDF, DOCX, or TXT file.');
    }

    if (file.size > maxSize) {
        throw new Error('File is too large. Maximum size is 10MB.');
    }

    return true;
}

// Format file size for display
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Handle API errors
function handleApiError(error) {
    console.error('API Error:', error);
    
    if (error.response) {
        // Server responded with error
        return error.response.data.error || 'An error occurred while processing your request.';
    } else if (error.request) {
        // No response received
        return 'Unable to connect to the server. Please check your internet connection.';
    } else {
        // Error in request setup
        return error.message || 'An unexpected error occurred.';
    }
}

// Show loading spinner
function showLoading(container) {
    const spinner = document.createElement('div');
    spinner.className = 'loading-spinner';
    spinner.innerHTML = `
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        <p class="mt-4 text-gray-600">Processing...</p>
    `;
    container.appendChild(spinner);
}

// Hide loading spinner
function hideLoading(container) {
    const spinner = container.querySelector('.loading-spinner');
    if (spinner) {
        spinner.remove();
    }
}

// Format analysis results for display
function formatAnalysisResults(results) {
    const formatted = {
        high: [],
        medium: [],
        low: []
    };

    if (Array.isArray(results)) {
        // If results is a flat array, distribute items into priority buckets
        results.forEach((item, index) => {
            if (index < 8) {
                formatted.high.push(item);
            } else if (index < 16) {
                formatted.medium.push(item);
            } else {
                formatted.low.push(item);
            }
        });
    } else if (typeof results === 'object') {
        // If results already has priority structure, use it
        formatted.high = results.high || [];
        formatted.medium = results.medium || [];
        formatted.low = results.low || [];
    }

    return formatted;
}

// Export functions for use in other modules
export {
    validateFile,
    formatFileSize,
    handleApiError,
    showLoading,
    hideLoading,
    formatAnalysisResults
}; 