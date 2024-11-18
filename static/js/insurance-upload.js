document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    const fileInput = document.querySelector('input[type="file"]');
    const spinner = document.getElementById('uploadSpinner');
    const progressBar = document.getElementById('uploadProgress');
    const progressBarFill = progressBar?.querySelector('.progress-bar-fill');
    const progressText = document.getElementById('progressText');
    const UPLOAD_TIMEOUT = 30000; // 30 seconds timeout
    const TRANSITION_DELAY = 1000; // 1 second delay for animations

    form?.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Clear previous error messages
        clearMessages();
        
        // Validate file input
        const file = fileInput?.files[0];
        if (!file) {
            showError('Please select a file');
            logger.error('No file selected');
            return;
        }

        // Validate file size (max 16MB)
        if (file.size > 16 * 1024 * 1024) {
            showError('File size exceeds 16MB limit');
            logger.error(`File size (${file.size} bytes) exceeds limit`);
            return;
        }

        // Validate file type
        const allowedTypes = ['.pdf', '.docx', '.txt', '.md', '.json'];
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        if (!allowedTypes.includes(fileExtension)) {
            showError('Invalid file type. Allowed types: PDF, DOCX, TXT, MD, JSON');
            logger.error(`Invalid file type: ${fileExtension}`);
            return;
        }

        // Show uploading state
        showUploadingState();

        try {
            // Create FormData and explicitly append the file
            const formData = new FormData();
            formData.append('file', file);

            // Start upload with progress tracking
            const result = await uploadWithXHR(formData);
            
            // Validate redirect URL
            if (!result.next_step_url) {
                throw new Error('Server did not provide next step URL');
            }

            // Complete the progress animation
            await animateProgress(100);
            
            // Show success message
            showSuccess('Upload successful! Redirecting...');
            
            // Wait for animations to complete before redirect
            await new Promise(resolve => setTimeout(resolve, TRANSITION_DELAY));
            
            // Redirect to next step
            window.location.href = result.next_step_url;

        } catch (error) {
            handleUploadError(error);
        } finally {
            cleanupUploadState();
        }
    });

    function uploadWithXHR(formData) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            let timedOut = false;
            
            // Setup timeout
            const timeoutId = setTimeout(() => {
                timedOut = true;
                xhr.abort();
                reject(new Error('Upload timed out. Please try again.'));
            }, UPLOAD_TIMEOUT);

            // Track upload progress
            xhr.upload.addEventListener('progress', async (event) => {
                if (event.lengthComputable) {
                    const percentComplete = Math.min((event.loaded / event.total) * 95, 95);
                    await animateProgress(percentComplete);
                }
            });

            // Handle response
            xhr.addEventListener('load', () => {
                clearTimeout(timeoutId);
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (error) {
                        reject(new Error('Invalid response from server'));
                    }
                } else {
                    try {
                        const errorResponse = JSON.parse(xhr.responseText);
                        reject(new Error(errorResponse.error || 'Upload failed'));
                    } catch (error) {
                        reject(new Error(`Upload failed with status: ${xhr.status}`));
                    }
                }
            });

            // Handle network errors
            xhr.addEventListener('error', () => {
                clearTimeout(timeoutId);
                if (!timedOut) {
                    reject(new Error('Network error occurred. Please check your connection.'));
                }
            });

            // Handle abort
            xhr.addEventListener('abort', () => {
                clearTimeout(timeoutId);
                if (!timedOut) {
                    reject(new Error('Upload was cancelled.'));
                }
            });

            // Start upload
            xhr.open('POST', form.action);
            xhr.send(formData);
        });
    }

    async function animateProgress(targetValue) {
        const currentValue = parseInt(progressBarFill?.style.width) || 0;
        const steps = 10;
        const increment = (targetValue - currentValue) / steps;
        
        for (let i = 0; i <= steps; i++) {
            const value = currentValue + (increment * i);
            updateProgress(value);
            await new Promise(resolve => setTimeout(resolve, 50));
        }
    }

    function showUploadingState() {
        spinner?.classList.remove('hidden');
        progressBar?.classList.remove('hidden');
        disableForm(true);
        updateProgress(0);
    }

    function cleanupUploadState() {
        spinner?.classList.add('hidden');
        disableForm(false);
    }

    function updateProgress(value) {
        if (progressBarFill && progressText) {
            // Ensure value is between 0 and 100
            const safeValue = Math.min(Math.max(0, value), 100);
            progressBarFill.style.width = `${safeValue}%`;
            progressText.textContent = `${Math.round(safeValue)}%`;
        }
    }

    function disableForm(disabled) {
        if (fileInput) fileInput.disabled = disabled;
        if (form) {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) submitButton.disabled = disabled;
        }
    }

    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'mt-4 p-4 bg-red-100 text-red-700 rounded-md';
        errorDiv.textContent = message;
        form?.appendChild(errorDiv);
        setTimeout(() => errorDiv.remove(), 5000);
    }

    function showSuccess(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'mt-4 p-4 bg-green-100 text-green-700 rounded-md';
        successDiv.textContent = message;
        form?.appendChild(successDiv);
        setTimeout(() => successDiv.remove(), TRANSITION_DELAY);
    }

    function clearMessages() {
        form?.querySelectorAll('.mt-4.p-4').forEach(msg => msg.remove());
    }

    function handleUploadError(error) {
        logger.error('Upload error:', error);
        showError(error.message || 'Error uploading file. Please try again.');
    }
});
