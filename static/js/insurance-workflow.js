// Insurance Document Workflow State
const workflowState = {
    step1Completed: false,
    step2Completed: false,
    requirementsDocId: null,
    claimDocId: null,
    isUploading: false,
    uploadProgress: 0
};

// Initialize workflow
document.addEventListener('DOMContentLoaded', function() {
    initializeWorkflow();
    attachEventListeners();
    checkExistingDocuments();
});

function initializeWorkflow() {
    // Initially disable steps 2 and 3
    disableStep(2);
    disableStep(3);
    updateProgressBar(1);
}

function attachEventListeners() {
    // Requirements form submission
    const requirementsForm = document.getElementById('requirementsForm');
    requirementsForm?.addEventListener('submit', handleRequirementsUpload);

    // Claim form submission
    const claimForm = document.getElementById('claimForm');
    claimForm?.addEventListener('submit', handleClaimUpload);
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
            completeStep(1);
        }
        if (data.claim_doc_id) {
            workflowState.claimDocId = data.claim_doc_id;
            completeStep(2);
        }
    } catch (error) {
        console.error('Error checking workflow state:', error);
        updateStatus('requirementsStatus', '❌ Error checking workflow state', 'error');
    }
}

async function handleRequirementsUpload(e) {
    e.preventDefault();
    
    // Prevent double submission
    if (workflowState.isUploading) {
        return;
    }
    
    const fileInput = document.getElementById('requirementsDoc');
    const file = fileInput.files[0];
    const submitButton = e.target.querySelector('button[type="submit"]');
    const spinner = document.getElementById('requirementsSpinner');
    const progressIndicator = document.getElementById('requirementsProgress');
    const progressText = document.getElementById('requirementsProgressText');
    
    // Clear previous states
    updateStatus('requirementsStatus', '', 'processing');
    resetUploadProgress();
    
    if (!file) {
        updateStatus('requirementsStatus', '⚠️ Please select a file', 'error');
        return;
    }

    // Validate file size (max 16MB)
    if (file.size > 16 * 1024 * 1024) {
        updateStatus('requirementsStatus', '❌ File size exceeds 16MB limit', 'error');
        return;
    }

    // Validate file type
    const allowedTypes = ['.pdf', '.docx', '.txt', '.md', '.json'];
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedTypes.includes(fileExtension)) {
        updateStatus('requirementsStatus', '❌ Invalid file type. Allowed types: PDF, DOCX, TXT, MD, JSON', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('processing_type', 'insurance_requirements');

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

    try {
        // Set upload states
        workflowState.isUploading = true;
        disableFormElements(true, submitButton);
        spinner.classList.remove('hidden');
        progressIndicator.classList.remove('hidden');
        
        // Show initial loading state
        showLoading('Preparing to upload requirements document...');
        updateStatus('requirementsStatus', '📤 Initiating upload...', 'processing');

        // Simulate upload progress
        const progressInterval = setInterval(() => {
            if (workflowState.uploadProgress < 90) {
                workflowState.uploadProgress += 10;
                updateUploadProgress(progressIndicator, progressText);
            }
        }, 500);

        const response = await fetch('/chat/upload', {
            method: 'POST',
            body: formData,
            signal: controller.signal
        });

        clearTimeout(timeoutId);
        clearInterval(progressInterval);

        // Handle response
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || `Upload failed with status: ${response.status}`);
        }
        
        // Complete upload progress
        workflowState.uploadProgress = 100;
        updateUploadProgress(progressIndicator, progressText);
        
        // Update workflow state and UI
        workflowState.requirementsDocId = data.document_id;
        updateStatus('requirementsStatus', 
            '✅ Requirements document uploaded successfully! You can now proceed to upload your claim document.', 
            'success'
        );
        completeStep(1);
        
        // Clear file input
        fileInput.value = '';
        
        // Smooth scroll to next section
        document.getElementById('step2Section').scrollIntoView({ 
            behavior: 'smooth',
            block: 'start'
        });

    } catch (error) {
        console.error('Upload error:', error);
        
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
        
        updateStatus('requirementsStatus', errorMessage, 'error');
        resetStep(1);
        
    } finally {
        // Clean up all states
        clearTimeout(timeoutId);
        workflowState.isUploading = false;
        workflowState.uploadProgress = 0;
        spinner.classList.add('hidden');
        hideLoading();
        
        // Reset form elements
        disableFormElements(false, submitButton);
        progressIndicator.classList.add('hidden');
        setTimeout(() => {
            progressIndicator.querySelector('.progress-bar-fill').style.width = '0%';
            progressText.textContent = '';
        }, 300);
    }
}

function updateUploadProgress(progressIndicator, progressText) {
    const progressBar = progressIndicator.querySelector('.progress-bar-fill');
    progressBar.style.width = `${workflowState.uploadProgress}%`;
    progressText.textContent = `${workflowState.uploadProgress}%`;
}

function disableFormElements(disabled, submitButton) {
    const elements = document.querySelectorAll('#requirementsForm input, #requirementsForm button');
    elements.forEach(element => {
        element.disabled = disabled;
    });
    if (submitButton) {
        submitButton.disabled = disabled;
    }
}

async function handleClaimUpload(e) {
    e.preventDefault();
    if (!workflowState.step1Completed) {
        updateStatus('claimStatus', '⚠️ Please complete step 1 first', 'error');
        return;
    }
    
    // Prevent double submission
    if (workflowState.isUploading) return;

    const fileInput = document.getElementById('claimDoc');
    const file = fileInput.files[0];
    const submitButton = e.target.querySelector('button[type="submit"]');
    const spinner = document.getElementById('claimSpinner');
    const progressIndicator = document.getElementById('claimProgress');
    const progressText = document.getElementById('claimProgressText');
    
    // Clear previous error states
    updateStatus('claimStatus', '', 'processing');
    
    if (!file) {
        updateStatus('claimStatus', 'Please select a file', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('processing_type', 'insurance_claim');
    formData.append('requirements_doc_id', workflowState.requirementsDocId);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

    try {
        // Set upload states
        workflowState.isUploading = true;
        disableFormElements(true, submitButton);
        spinner.classList.remove('hidden');
        progressIndicator.classList.remove('hidden');
        
        showLoading('Uploading and processing claim document...');
        updateStatus('claimStatus', '📤 Initiating upload...', 'processing');

        // Simulate upload progress
        const progressInterval = setInterval(() => {
            if (workflowState.uploadProgress < 90) {
                workflowState.uploadProgress += 10;
                updateUploadProgress(progressIndicator, progressText);
            }
        }, 500);

        const response = await fetch('/chat/upload-claim', {
            method: 'POST',
            body: formData,
            signal: controller.signal
        });

        clearTimeout(timeoutId);
        clearInterval(progressInterval);

        // Handle response
        const data = await response.json();
        if (response.ok) {
            // Complete upload progress
            workflowState.uploadProgress = 100;
            updateUploadProgress(progressIndicator, progressText);
            
            workflowState.claimDocId = data.document_id;
            updateStatus('claimStatus', 
                '✅ Claim document uploaded successfully! You can now proceed with the analysis.', 
                'success'
            );
            completeStep(2);
            
            // Clear file input
            fileInput.value = '';
            
            // Scroll to step 3 section
            document.getElementById('step3Section').scrollIntoView({ behavior: 'smooth' });
        } else {
            throw new Error(data.error || 'Upload failed');
        }
    } catch (error) {
        console.error('Upload error:', error);
        
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
        
        updateStatus('claimStatus', errorMessage, 'error');
        resetStep(2);
        
    } finally {
        // Clean up all states
        clearTimeout(timeoutId);
        workflowState.isUploading = false;
        workflowState.uploadProgress = 0;
        spinner.classList.add('hidden');
        hideLoading();
        
        // Reset form elements
        disableFormElements(false, submitButton);
        progressIndicator.classList.add('hidden');
        setTimeout(() => {
            progressIndicator.querySelector('.progress-bar-fill').style.width = '0%';
            progressText.textContent = '';
        }, 300);
    }
}

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

function completeStep(step) {
    const indicator = document.getElementById(`step${step}Indicator`);
    indicator.classList.remove('bg-gray-300');
    indicator.classList.add('bg-blue-600');
    
    // Add checkmark icon to completed step
    indicator.innerHTML = '✓';

    if (step === 1) {
        workflowState.step1Completed = true;
        enableStep(2);
        updateProgressBar(2);
        document.getElementById('step2Guidance').innerHTML = 
            '<span class="text-green-600">✓ Requirements uploaded!</span><br>' +
            'Please upload your claim document for analysis.';
    } else if (step === 2) {
        workflowState.step2Completed = true;
        enableStep(3);
        updateProgressBar(3);
        document.getElementById('step3Guidance').innerHTML = 
            '<span class="text-green-600">✓ All documents uploaded!</span><br>' +
            'Select an analysis option to process your documents.';
    }
}

function resetStep(step) {
    const indicator = document.getElementById(`step${step}Indicator`);
    indicator.classList.remove('bg-blue-600');
    indicator.classList.add('bg-gray-300');
    indicator.textContent = step;

    if (step === 1) {
        workflowState.step1Completed = false;
        workflowState.requirementsDocId = null;
        disableStep(2);
        disableStep(3);
        updateProgressBar(1);
    } else if (step === 2) {
        workflowState.step2Completed = false;
        workflowState.claimDocId = null;
        disableStep(3);
        updateProgressBar(2);
    }
}

function enableStep(step) {
    const section = document.getElementById(`step${step}Section`);
    section.classList.remove('opacity-50');
    
    // Add transition effect
    section.style.transition = 'opacity 0.3s ease-in-out';
    
    if (step === 2) {
        document.getElementById('claimDoc').disabled = false;
        document.querySelector('#claimForm button[type="submit"]').disabled = false;
    } else if (step === 3) {
        document.querySelectorAll('.analysis-btn').forEach(btn => {
            btn.disabled = false;
        });
    }
}

function disableStep(step) {
    const section = document.getElementById(`step${step}Section`);
    section.classList.add('opacity-50');
    
    if (step === 2) {
        document.getElementById('claimDoc').disabled = true;
        document.querySelector('#claimForm button[type="submit"]').disabled = true;
        document.getElementById('step2Guidance').textContent = 'Complete Step 1 to unlock this step.';
    } else if (step === 3) {
        document.querySelectorAll('.analysis-btn').forEach(btn => {
            btn.disabled = true;
        });
        document.getElementById('step3Guidance').textContent = 'Complete Steps 1 and 2 to unlock analysis options.';
    }
}

function updateProgressBar(step) {
    const progressBar = document.getElementById('progressBar');
    const newWidth = `${(step / 3) * 100}%`;
    
    // Add smooth transition
    progressBar.style.transition = 'width 0.5s ease-in-out';
    progressBar.style.width = newWidth;
}

function updateProgressIndicator(elementId, show) {
    const progress = document.getElementById(elementId);
    const progressFill = progress.querySelector('.progress-bar-fill');
    
    if (show) {
        progress.classList.remove('hidden');
        progressFill.style.width = '100%';
    } else {
        progress.classList.add('hidden');
        progressFill.style.width = '0%';
    }
}

function updateStatus(elementId, message, type = 'processing') {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = message;
        element.className = `status-message status-${type}`;
        
        // Add shake animation for errors
        if (type === 'error') {
            element.classList.add('animate-shake');
            // Remove animation class after it completes
            setTimeout(() => element.classList.remove('animate-shake'), 500);
        }
    }
}

// Loading overlay management
function showLoading(message = 'Processing...') {
    const overlay = document.getElementById('loadingOverlay');
    const loadingText = document.getElementById('loadingText');
    
    if (!overlay || !loadingText) {
        console.error('Loading overlay elements not found');
        return;
    }
    
    // Store current state of interactive elements
    document.querySelectorAll('button, input, select').forEach(element => {
        if (!element.closest('#loadingOverlay')) {
            element.dataset.wasDisabled = element.disabled;
            element.disabled = true;
        }
    });
    
    // Set message and show overlay with transition
    loadingText.textContent = message;
    
    // Ensure proper transition
    overlay.style.display = 'flex';
    overlay.style.opacity = '0';
    overlay.style.transition = 'opacity 0.3s ease-in-out';
    
    // Force reflow to ensure transition works
    overlay.offsetHeight;
    
    // Show overlay
    overlay.style.opacity = '1';
    overlay.classList.add('active');
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    
    if (!overlay) {
        console.error('Loading overlay element not found');
        return;
    }
    
    // Set up transition
    overlay.style.transition = 'opacity 0.3s ease-in-out';
    overlay.style.opacity = '0';
    
    // Wait for transition to complete before hiding
    const handleTransitionEnd = () => {
        overlay.style.display = 'none';
        overlay.classList.remove('active');
        overlay.removeEventListener('transitionend', handleTransitionEnd);
        
        // Restore interactive elements to their previous state
        document.querySelectorAll('button, input, select').forEach(element => {
            if (!element.closest('#loadingOverlay')) {
                const wasDisabled = element.dataset.wasDisabled === 'true';
                element.disabled = wasDisabled;
                delete element.dataset.wasDisabled;
            }
        });
    };
    
    overlay.addEventListener('transitionend', handleTransitionEnd);
}

function resetUploadProgress() {
    workflowState.uploadProgress = 0;
    const progressBar = document.getElementById('requirementsProgress');
    if (progressBar) {
        progressBar.classList.add('hidden');
        const fill = progressBar.querySelector('.progress-bar-fill');
        if (fill) {
            fill.style.transition = 'width 0.3s ease-in-out';
            fill.style.width = '0%';
        }
        const text = progressBar.querySelector('#requirementsProgressText');
        if (text) {
            text.textContent = '';
        }
    }
}

// Export workflowState for testing purposes
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { workflowState };
}