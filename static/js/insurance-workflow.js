// Insurance Document Workflow State
const workflowState = {
    step1Completed: false,
    step2Completed: false,
    requirementsDocId: null,
    claimDocId: null,
    isUploading: false,
    uploadProgress: 0,
    currentStep: 1,
    isTransitioning: false
};

// Initialize workflow
document.addEventListener('DOMContentLoaded', function() {
    initializeWorkflow();
    attachEventListeners();
    checkExistingDocuments();
    
    // Check for flash messages
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.opacity = '0';
            setTimeout(() => msg.remove(), 300);
        }, 5000);
    });
});

function initializeWorkflow() {
    // Initially disable steps 2 and 3
    disableStep(2);
    disableStep(3);
    updateProgressBar(1);
    
    // Add transition classes to all steps
    document.querySelectorAll('[id^="step"]').forEach(step => {
        step.classList.add('transition-all', 'duration-300', 'ease-in-out');
    });
}

function attachEventListeners() {
    // Requirements form submission
    const requirementsForm = document.getElementById('requirementsForm');
    if (requirementsForm) {
        requirementsForm.addEventListener('submit', handleRequirementsUpload);
        
        // File input change listener
        const fileInput = requirementsForm.querySelector('input[type="file"]');
        if (fileInput) {
            fileInput.addEventListener('change', validateFile);
        }
    }

    // Claim form submission
    const claimForm = document.getElementById('claimForm');
    if (claimForm) {
        claimForm.addEventListener('submit', handleClaimUpload);
        
        // File input change listener
        const fileInput = claimForm.querySelector('input[type="file"]');
        if (fileInput) {
            fileInput.addEventListener('change', validateFile);
        }
    }
}

async function handleRequirementsUpload(e) {
    e.preventDefault();
    
    if (workflowState.isUploading || workflowState.isTransitioning) {
        return;
    }
    
    const form = e.target;
    const fileInput = form.querySelector('input[type="file"]');
    const file = fileInput.files[0];
    const submitButton = form.querySelector('button[type="submit"]');
    const progressIndicator = document.getElementById('uploadProgress');
    const progressText = document.getElementById('progressText');
    
    if (!file || !validateFile({ target: fileInput })) {
        return;
    }

    try {
        // Set upload states
        workflowState.isUploading = true;
        disableFormElements(true);
        showUploadingState();
        
        // Show initial loading state
        await animateProgress(0, 20);
        updateStatus('requirementsStatus', '📤 Processing document...', 'processing');

        const formData = new FormData(form);
        
        // Start upload with progress tracking
        const xhr = new XMLHttpRequest();
        xhr.open('POST', form.action, true);
        
        xhr.upload.onprogress = function(e) {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                updateUploadProgress(percentComplete);
            }
        };
        
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4) {
                if (xhr.status === 200) {
                    // Handle successful upload
                    completeUpload();
                } else {
                    // Handle upload error
                    handleUploadError(new Error('Upload failed'));
                }
            }
        };
        
        xhr.send(formData);

    } catch (error) {
        console.error('Upload error:', error);
        handleUploadError(error);
    }
}

function showUploadingState() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    const uploadProgress = document.getElementById('uploadProgress');
    
    if (loadingOverlay) {
        loadingOverlay.classList.remove('hidden');
        loadingOverlay.style.opacity = '1';
    }
    
    if (uploadProgress) {
        uploadProgress.classList.remove('hidden');
        uploadProgress.style.opacity = '1';
    }
}

async function animateProgress(start, end) {
    const progressBar = document.querySelector('.progress-bar-fill');
    const progressText = document.getElementById('progressText');
    const duration = 300;
    const steps = 20;
    const increment = (end - start) / steps;
    
    for (let i = 0; i <= steps; i++) {
        const currentProgress = start + (increment * i);
        if (progressBar) {
            progressBar.style.width = `${currentProgress}%`;
        }
        if (progressText) {
            progressText.textContent = `${Math.round(currentProgress)}%`;
        }
        await new Promise(resolve => setTimeout(resolve, duration / steps));
    }
}

function updateUploadProgress(percent) {
    const progressBar = document.querySelector('.progress-bar-fill');
    const progressText = document.getElementById('progressText');
    
    if (progressBar) {
        progressBar.style.width = `${percent}%`;
    }
    if (progressText) {
        progressText.textContent = `${Math.round(percent)}%`;
    }
}

function completeUpload() {
    // The page will be redirected by the server
    // Show final success state before redirect
    updateStatus('requirementsStatus', '✅ Upload successful! Redirecting...', 'success');
    animateProgress(90, 100);
}

function handleUploadError(error) {
    workflowState.isUploading = false;
    disableFormElements(false);
    hideUploadingState();
    
    const errorMessage = error.message || 'An error occurred during upload';
    updateStatus('requirementsStatus', `❌ ${errorMessage}`, 'error');
    
    // Reset progress
    updateUploadProgress(0);
}

function hideUploadingState() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    const uploadProgress = document.getElementById('uploadProgress');
    
    if (loadingOverlay) {
        loadingOverlay.style.opacity = '0';
        setTimeout(() => loadingOverlay.classList.add('hidden'), 300);
    }
    
    if (uploadProgress) {
        uploadProgress.style.opacity = '0';
        setTimeout(() => uploadProgress.classList.add('hidden'), 300);
    }
}

async function handleClaimUpload(e) {
    e.preventDefault();
    
    if (workflowState.isUploading || workflowState.isTransitioning) {
        return;
    }
    
    const form = e.target;
    const fileInput = form.querySelector('input[type="file"]');
    const file = fileInput.files[0];
    const submitButton = form.querySelector('button[type="submit"]');
    const progressIndicator = document.getElementById('uploadProgress');
    const progressText = document.getElementById('progressText');
    
    if (!file || !validateFile({ target: fileInput })) {
        return;
    }

    try {
        // Set upload states
        workflowState.isUploading = true;
        disableFormElements(true);
        showUploadingState();
        
        // Show initial loading state
        await animateProgress(0, 20);
        updateStatus('claimStatus', '📤 Processing document...', 'processing');

        const formData = new FormData(form);
        
        // Start upload with progress tracking
        const xhr = new XMLHttpRequest();
        xhr.open('POST', form.action, true);
        
        xhr.upload.onprogress = function(e) {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                updateUploadProgress(percentComplete);
            }
        };
        
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4) {
                if (xhr.status === 200) {
                    // Handle successful upload
                    completeUpload();
                } else {
                    // Handle upload error
                    handleUploadError(new Error('Upload failed'));
                }
            }
        };
        
        xhr.send(formData);

    } catch (error) {
        console.error('Upload error:', error);
        handleUploadError(error);
    }
}

function validateFile(event) {
    const file = event.target.files[0];
    const statusId = event.target.id === 'requirementsDoc' ? 'requirementsStatus' : 'claimStatus';
    const submitBtn = event.target.closest('form').querySelector('button[type="submit"]');

    if (file) {
        // Clear previous status
        updateStatus(statusId, '', 'processing');
        
        // Validate file size (max 16MB)
        if (file.size > 16 * 1024 * 1024) {
            updateStatus(statusId, '❌ File size exceeds 16MB limit', 'error');
            event.target.value = ''; // Clear the file input
            submitBtn.disabled = true;
            return false;
        }

        // Validate file type
        const allowedTypes = ['.pdf', '.docx', '.txt', '.md', '.json'];
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        if (!allowedTypes.includes(fileExtension)) {
            updateStatus(statusId, '❌ Invalid file type. Allowed types: PDF, DOCX, TXT, MD, JSON', 'error');
            event.target.value = ''; // Clear the file input
            submitBtn.disabled = true;
            return false;
        }

        submitBtn.disabled = false;
        updateStatus(statusId, '✅ File validated successfully', 'success');
        return true;
    }
    
    submitBtn.disabled = true;
    return false;
}

async function animateProgress(start, end) {
    const progressBar = document.querySelector('.progress-bar-fill');
    const progressText = document.getElementById('progressText');
    const duration = 300;
    const steps = 20;
    const increment = (end - start) / steps;
    
    for (let i = 0; i <= steps; i++) {
        const currentProgress = start + (increment * i);
        if (progressBar) {
            progressBar.style.width = `${currentProgress}%`;
        }
        if (progressText) {
            progressText.textContent = `${Math.round(currentProgress)}%`;
        }
        await new Promise(resolve => setTimeout(resolve, duration / steps));
    }
}

function updateUploadProgress(percent) {
    const progressBar = document.querySelector('.progress-bar-fill');
    const progressText = document.getElementById('progressText');
    
    if (progressBar) {
        progressBar.style.width = `${percent}%`;
    }
    if (progressText) {
        progressText.textContent = `${Math.round(percent)}%`;
    }
}

function completeUpload() {
    // The page will be redirected by the server
    // Show final success state before redirect
    updateStatus('requirementsStatus', '✅ Upload successful! Redirecting...', 'success');
    animateProgress(90, 100);
}

function handleUploadError(error) {
    workflowState.isUploading = false;
    disableFormElements(false);
    hideUploadingState();
    
    const errorMessage = error.message || 'An error occurred during upload';
    updateStatus('requirementsStatus', `❌ ${errorMessage}`, 'error');
    
    // Reset progress
    updateUploadProgress(0);
}

function hideUploadingState() {
    const loadingOverlay = document.getElementById('loadingOverlay');
    const uploadProgress = document.getElementById('uploadProgress');
    
    if (loadingOverlay) {
        loadingOverlay.style.opacity = '0';
        setTimeout(() => loadingOverlay.classList.add('hidden'), 300);
    }
    
    if (uploadProgress) {
        uploadProgress.style.opacity = '0';
        setTimeout(() => uploadProgress.classList.add('hidden'), 300);
    }
}

async function completeStepWithAnimation(step) {
    const indicator = document.getElementById(`step${step}Indicator`);
    
    // Add animation classes
    indicator.classList.add('transform', 'scale-110');
    await new Promise(resolve => setTimeout(resolve, 150));
    
    indicator.classList.remove('bg-gray-300');
    indicator.classList.add('bg-blue-600');
    
    // Add checkmark with fade-in animation
    indicator.style.opacity = '0';
    indicator.innerHTML = '✓';
    await new Promise(resolve => setTimeout(resolve, 50));
    indicator.style.opacity = '1';
    
    // Remove scale animation
    indicator.classList.remove('scale-110');
    
    if (step === 1) {
        workflowState.step1Completed = true;
        await enableStepWithAnimation(2);
        updateProgressBar(2);
    } else if (step === 2) {
        workflowState.step2Completed = true;
        await enableStepWithAnimation(3);
        updateProgressBar(3);
    }
}

async function enableStepWithAnimation(step) {
    const section = document.getElementById(`step${step}Section`);
    
    // Set initial state
    section.style.opacity = '0.5';
    section.style.transform = 'translateY(10px)';
    section.classList.remove('opacity-50');
    
    // Add transition
    section.style.transition = 'all 0.3s ease-in-out';
    
    // Trigger animation
    await new Promise(resolve => setTimeout(resolve, 50));
    section.style.opacity = '1';
    section.style.transform = 'translateY(0)';
    
    // Enable form elements
    if (step === 2) {
        document.getElementById('claimDoc').disabled = false;
        document.querySelector('#claimForm button[type="submit"]').disabled = false;
        document.getElementById('step2Guidance').innerHTML = 
            '<span class="text-green-600">✓ Requirements uploaded!</span><br>' +
            'Please upload your claim document for analysis.';
    } else if (step === 3) {
        document.querySelectorAll('.analysis-btn').forEach(btn => {
            btn.disabled = false;
        });
        document.getElementById('step3Guidance').innerHTML = 
            '<span class="text-green-600">✓ All documents uploaded!</span><br>' +
            'Select an analysis option to process your documents.';
    }
}

function handleUploadError(error, statusId, step) {
    let errorMessage = '❌ ';
    if (error.name === 'AbortError') {
        errorMessage += 'Upload timed out. Please try again.';
    } else if (!navigator.onLine) {
        errorMessage += 'Network connection lost. Please check your internet connection and try again.';
    } else if (error.message.includes('network')) {
        errorMessage += 'Network error. Please check your connection and try again.';
    } else {
        errorMessage += error.message || 'Error uploading document. Please try again.';
    }
    
    updateStatus(statusId, errorMessage, 'error');
    resetStep(step);
}

function showUploadingState(spinner, progressIndicator) {
    spinner.classList.remove('hidden');
    progressIndicator.classList.remove('hidden');
    progressIndicator.style.opacity = '0';
    setTimeout(() => {
        progressIndicator.style.opacity = '1';
        progressIndicator.style.transition = 'opacity 0.3s ease-in-out';
    }, 50);
}

function cleanupUploadState(spinner, progressIndicator, progressText, submitButton) {
    workflowState.isUploading = false;
    workflowState.isTransitioning = false;
    workflowState.uploadProgress = 0;
    
    spinner.classList.add('hidden');
    progressIndicator.style.opacity = '0';
    
    setTimeout(() => {
        progressIndicator.classList.add('hidden');
        progressIndicator.querySelector('.progress-bar-fill').style.width = '0%';
        progressText.textContent = '';
        disableFormElements(false, submitButton);
    }, 300);
}

async function scrollToNextSection(sectionId) {
    const nextSection = document.getElementById(sectionId);
    nextSection.style.transform = 'translateY(10px)';
    nextSection.style.opacity = '0.5';
    
    nextSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    
    await new Promise(resolve => setTimeout(resolve, 300));
    
    nextSection.style.transform = 'translateY(0)';
    nextSection.style.opacity = '1';
    nextSection.style.transition = 'all 0.3s ease-in-out';
}

function updateStatus(elementId, message, type) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    element.textContent = message;
    element.className = 'status-message mt-2 ' + (type === 'error' ? 'text-red-600' : 
                                                 type === 'success' ? 'text-green-600' : 
                                                 'text-blue-600');
}

function disableFormElements(disabled, submitButton) {
    const elements = document.querySelectorAll('input[type="file"], button[type="submit"]');
    elements.forEach(element => {
        element.disabled = disabled;
    });
    if (submitButton) {
        submitButton.disabled = disabled;
    }
}

function resetUploadProgress() {
    workflowState.uploadProgress = 0;
    document.querySelectorAll('.progress-bar-fill').forEach(bar => {
        bar.style.width = '0%';
    });
    document.querySelectorAll('[id$="ProgressText"]').forEach(text => {
        text.textContent = '';
    });
}

function resetStep(step) {
    if (step === 1) {
        workflowState.step1Completed = false;
        workflowState.requirementsDocId = null;
    } else if (step === 2) {
        workflowState.step2Completed = false;
        workflowState.claimDocId = null;
    }
}

function disableStep(step) {
    const section = document.getElementById(`step${step}Section`);
    if (section) {
        section.classList.add('opacity-50');
        const inputs = section.querySelectorAll('input, button');
        inputs.forEach(input => input.disabled = true);
    }
}

function enableStep(step) {
    const section = document.getElementById(`step${step}Section`);
    if (section) {
        section.classList.remove('opacity-50');
        const inputs = section.querySelectorAll('input, button');
        inputs.forEach(input => input.disabled = false);
    }
}

function updateProgressBar(step) {
    const progressBar = document.getElementById('progressBar');
    if (progressBar) {
        const width = (step / 3) * 100;
        progressBar.style.width = `${width}%`;
    }
}

async function checkExistingDocuments() {
    try {
        const response = await fetch('/chat/workflow-state');
        if (!response.ok) {
            throw new Error('Failed to fetch workflow state');
        }
        const data = await response.json();
        
        if (data.requirements_doc_id) {
            workflowState.requirementsDocId = data.requirements_doc_id;
            await completeStepWithAnimation(1);
        }
        if (data.claim_doc_id) {
            workflowState.claimDocId = data.claim_doc_id;
            await completeStepWithAnimation(2);
        }
    } catch (error) {
        console.error('Error checking workflow state:', error);
        updateStatus('requirementsStatus', '❌ Error checking workflow state', 'error');
    }
}

// Analysis functions
async function analyzeDocuments(analysisType) {
    if (!workflowState.step1Completed || !workflowState.step2Completed) {
        updateStatus('analysisStatus', '⚠️ Please complete both document uploads first', 'error');
        return;
    }

    try {
        showLoading('Analyzing documents...');
        updateStatus('analysisStatus', 'Processing analysis...', 'processing');
        
        const response = await fetch('/chat/insurance-analysis', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                claim_document_id: workflowState.claimDocId,
                requirement_document_id: workflowState.requirementsDocId,
                analysis_type: analysisType
            })
        });

        const data = await response.json();
        if (response.ok) {
            updateStatus('analysisStatus', '✅ Analysis completed successfully', 'success');
            // Redirect to chat view with the new analysis
            window.location.href = `/chat?chat_id=${data.chat_id}`;
        } else {
            throw new Error(data.error || 'Analysis failed');
        }
    } catch (error) {
        updateStatus('analysisStatus', 
            `❌ ${error.message || 'Error during analysis. Please try again.'}`, 
            'error'
        );
    } finally {
        hideLoading();
    }
}

// Loading overlay functions
function showLoading(message = 'Processing...') {
    const overlay = document.getElementById('loadingOverlay');
    const loadingText = document.getElementById('loadingText');
    if (overlay && loadingText) {
        loadingText.textContent = message;
        overlay.classList.remove('hidden');
        overlay.style.opacity = '1';
    }
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.opacity = '0';
        setTimeout(() => {
            overlay.classList.add('hidden');
        }, 300);
    }
}