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
    requirementsForm?.addEventListener('submit', handleRequirementsUpload);

    // Claim form submission
    const claimForm = document.getElementById('claimForm');
    claimForm?.addEventListener('submit', handleClaimUpload);

    // File input change listeners for validation
    document.getElementById('requirementsDoc')?.addEventListener('change', validateFile);
    document.getElementById('claimDoc')?.addEventListener('change', validateFile);
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

async function handleRequirementsUpload(e) {
    e.preventDefault();
    
    if (workflowState.isUploading || workflowState.isTransitioning) {
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
    
    if (!validateFile({ target: fileInput })) {
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('processing_type', 'insurance_requirements');

    try {
        // Set upload states
        workflowState.isUploading = true;
        workflowState.isTransitioning = true;
        disableFormElements(true, submitButton);
        showUploadingState(spinner, progressIndicator);
        
        // Show initial loading state with smooth animation
        await animateProgress(progressIndicator, progressText, 0, 10);
        updateStatus('requirementsStatus', '📤 Initiating upload...', 'processing');

        const response = await fetch('/chat/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || `Upload failed with status: ${response.status}`);
        }
        
        // Complete upload progress with animation
        await animateProgress(progressIndicator, progressText, 90, 100);
        
        // Update workflow state and UI with transitions
        workflowState.requirementsDocId = data.document_id;
        await completeStepWithAnimation(1);
        
        updateStatus('requirementsStatus', 
            '✅ Requirements document uploaded successfully! You can now proceed to upload your claim document.', 
            'success'
        );
        
        // Clear file input and scroll to next section with smooth animation
        fileInput.value = '';
        await scrollToNextSection('step2Section');

    } catch (error) {
        console.error('Upload error:', error);
        handleUploadError(error, 'requirementsStatus', 1);
        
    } finally {
        cleanupUploadState(spinner, progressIndicator, progressText, submitButton);
    }
}

async function handleClaimUpload(e) {
    e.preventDefault();
    
    if (workflowState.isUploading || workflowState.isTransitioning) {
        return;
    }
    
    const fileInput = document.getElementById('claimDoc');
    const file = fileInput.files[0];
    const submitButton = e.target.querySelector('button[type="submit"]');
    const spinner = document.getElementById('claimSpinner');
    const progressIndicator = document.getElementById('claimProgress');
    const progressText = document.getElementById('claimProgressText');
    
    // Clear previous states
    updateStatus('claimStatus', '', 'processing');
    resetUploadProgress();
    
    if (!validateFile({ target: fileInput })) {
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('processing_type', 'insurance_claim');
    formData.append('requirements_doc_id', workflowState.requirementsDocId);

    try {
        // Set upload states
        workflowState.isUploading = true;
        workflowState.isTransitioning = true;
        disableFormElements(true, submitButton);
        showUploadingState(spinner, progressIndicator);
        
        // Show initial loading state with smooth animation
        await animateProgress(progressIndicator, progressText, 0, 10);
        updateStatus('claimStatus', '📤 Initiating upload...', 'processing');

        const response = await fetch('/chat/upload-claim', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || `Upload failed with status: ${response.status}`);
        }
        
        // Complete upload progress with animation
        await animateProgress(progressIndicator, progressText, 90, 100);
        
        // Update workflow state and UI with transitions
        workflowState.claimDocId = data.document_id;
        await completeStepWithAnimation(2);
        
        updateStatus('claimStatus', 
            '✅ Claim document uploaded successfully! You can now proceed with the analysis.', 
            'success'
        );
        
        // Clear file input and scroll to next section with smooth animation
        fileInput.value = '';
        await scrollToNextSection('step3Section');

    } catch (error) {
        console.error('Upload error:', error);
        handleUploadError(error, 'claimStatus', 2);
        
    } finally {
        cleanupUploadState(spinner, progressIndicator, progressText, submitButton);
    }
}

async function animateProgress(progressIndicator, progressText, startValue, endValue) {
    const duration = 500; // Animation duration in milliseconds
    const steps = 20; // Number of steps in the animation
    const stepDuration = duration / steps;
    const increment = (endValue - startValue) / steps;

    for (let i = 0; i <= steps; i++) {
        const currentProgress = startValue + (increment * i);
        progressIndicator.querySelector('.progress-bar-fill').style.width = `${currentProgress}%`;
        progressText.textContent = `${Math.round(currentProgress)}%`;
        await new Promise(resolve => setTimeout(resolve, stepDuration));
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
    
    // Remove disabled state
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
    
    // Wait for animation to complete
    await new Promise(resolve => setTimeout(resolve, 300));
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

function disableFormElements(disabled, submitButton) {
    const elements = document.querySelectorAll('#requirementsForm input, #requirementsForm button');
    elements.forEach(element => {
        element.disabled = disabled;
    });
    if (submitButton) {
        submitButton.disabled = disabled;
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