document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    const fileInput = document.querySelector('input[type="file"]');
    const spinner = document.getElementById('uploadSpinner');
    const progressBar = document.getElementById('uploadProgress');
    const progressBarFill = progressBar?.querySelector('.progress-bar-fill');
    const progressText = document.getElementById('progressText');

    form?.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const file = fileInput.files[0];
        if (!file) {
            showError('Please select a file');
            return;
        }

        // Validate file size (max 16MB)
        if (file.size > 16 * 1024 * 1024) {
            showError('File size exceeds 16MB limit');
            return;
        }

        // Validate file type
        const allowedTypes = ['.pdf', '.docx', '.txt', '.md', '.json'];
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        if (!allowedTypes.includes(fileExtension)) {
            showError('Invalid file type. Allowed types: PDF, DOCX, TXT, MD, JSON');
            return;
        }

        // Show uploading state
        spinner.classList.remove('hidden');
        progressBar.classList.remove('hidden');
        disableForm(true);

        const formData = new FormData(form);

        try {
            // Simulate upload progress
            const progressInterval = setInterval(() => {
                const currentWidth = parseInt(progressBarFill.style.width) || 0;
                if (currentWidth < 90) {
                    progressBarFill.style.width = `${currentWidth + 10}%`;
                    progressText.textContent = `${currentWidth + 10}%`;
                }
            }, 500);

            const response = await fetch(form.action, {
                method: 'POST',
                body: formData
            });

            clearInterval(progressInterval);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Upload failed');
            }

            // Complete progress bar
            progressBarFill.style.width = '100%';
            progressText.textContent = '100%';

            // Show success message and redirect
            showSuccess('Upload successful! Redirecting...');
            setTimeout(() => {
                window.location.href = data.next_step_url;
            }, 1000);

        } catch (error) {
            showError(error.message || 'Upload failed');
        } finally {
            disableForm(false);
            spinner.classList.add('hidden');
            setTimeout(() => {
                progressBar.classList.add('hidden');
                progressBarFill.style.width = '0%';
                progressText.textContent = '';
            }, 500);
        }
    });

    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'mt-4 p-4 bg-red-100 text-red-700 rounded-md';
        errorDiv.textContent = message;
        form.appendChild(errorDiv);
        setTimeout(() => errorDiv.remove(), 5000);
    }

    function showSuccess(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'mt-4 p-4 bg-green-100 text-green-700 rounded-md';
        successDiv.textContent = message;
        form.appendChild(successDiv);
        setTimeout(() => successDiv.remove(), 5000);
    }

    function disableForm(disabled) {
        fileInput.disabled = disabled;
        form.querySelector('button[type="submit"]').disabled = disabled;
    }
});
