document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    const fileInput = document.querySelector('input[type="file"]');
    const spinner = document.getElementById('uploadSpinner');
    const progressBar = document.getElementById('uploadProgress');
    const progressBarFill = progressBar?.querySelector('.progress-bar-fill');
    const progressText = document.getElementById('progressText');

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

            // Log FormData contents for debugging
            logFormData(formData);

            // Start upload with progress tracking
            await uploadWithProgress(formData);

        } catch (error) {
            handleUploadError(error);
        } finally {
            cleanupUploadState();
        }
    });

    function showUploadingState() {
        spinner?.classList.remove('hidden');
        progressBar?.classList.remove('hidden');
        disableForm(true);
        updateProgress(0);
    }

    function cleanupUploadState() {
        spinner?.classList.add('hidden');
        disableForm(false);
        setTimeout(() => {
            progressBar?.classList.add('hidden');
            updateProgress(0);
        }, 500);
    }

    async function uploadWithProgress(formData) {
        // Start progress animation
        let progress = 0;
        const progressInterval = setInterval(() => {
            if (progress < 90) {
                progress += 10;
                updateProgress(progress);
            }
        }, 500);

        try {
            const response = await fetch(form.action, {
                method: 'POST',
                body: formData
            });

            clearInterval(progressInterval);

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || `Upload failed with status: ${response.status}`);
            }

            const data = await response.json();
            
            // Complete progress bar
            updateProgress(100);
            showSuccess('Upload successful! Redirecting...');

            // Redirect to next step
            setTimeout(() => {
                window.location.href = data.next_step_url;
            }, 1000);

        } catch (error) {
            clearInterval(progressInterval);
            throw error;
        }
    }

    function updateProgress(value) {
        if (progressBarFill && progressText) {
            progressBarFill.style.width = `${value}%`;
            progressText.textContent = `${value}%`;
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
        setTimeout(() => successDiv.remove(), 5000);
    }

    function clearMessages() {
        form?.querySelectorAll('.mt-4.p-4').forEach(msg => msg.remove());
    }

    function handleUploadError(error) {
        logger.error('Upload error:', error);
        showError(error.message || 'Error uploading file. Please try again.');
    }

    function logFormData(formData) {
        console.log('FormData contents:');
        for (const pair of formData.entries()) {
            console.log(pair[0], pair[1]);
        }
    }
});
