// Insurance Document Workflow State
const workflowState = {
    step1Completed: false,
    step2Completed: false,
    requirementsDocId: null,
    claimDocId: null
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
        if (response.ok) {
            const data = await response.json();
            if (data.requirements_doc_id) {
                workflowState.requirementsDocId = data.requirements_doc_id;
                completeStep(1);
            }
            if (data.claim_doc_id) {
                workflowState.claimDocId = data.claim_doc_id;
                completeStep(2);
            }
        }
    } catch (error) {
        console.error('Error checking workflow state:', error);
    }
}

async function handleRequirementsUpload(e) {
    e.preventDefault();
    const fileInput = document.getElementById('requirementsDoc');
    const file = fileInput.files[0];
    if (!file) {
        updateStatus('requirementsStatus', 'Please select a file', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('processing_type', 'insurance_requirements');

    try {
        showLoading('Uploading requirements document...');
        const response = await fetch('/chat/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        if (response.ok) {
            workflowState.requirementsDocId = data.document_id;
            updateStatus('requirementsStatus', 'Requirements document uploaded successfully', 'success');
            completeStep(1);
        } else {
            updateStatus('requirementsStatus', data.error || 'Upload failed', 'error');
        }
    } catch (error) {
        updateStatus('requirementsStatus', 'Error uploading document', 'error');
    } finally {
        hideLoading();
    }
}

async function handleClaimUpload(e) {
    e.preventDefault();
    if (!workflowState.step1Completed) {
        updateStatus('claimStatus', 'Please complete step 1 first', 'error');
        return;
    }

    const fileInput = document.getElementById('claimDoc');
    const file = fileInput.files[0];
    if (!file) {
        updateStatus('claimStatus', 'Please select a file', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('processing_type', 'insurance_claim');
    formData.append('requirements_doc_id', workflowState.requirementsDocId);

    try {
        showLoading('Uploading claim document...');
        const response = await fetch('/chat/upload-claim', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        if (response.ok) {
            workflowState.claimDocId = data.document_id;
            updateStatus('claimStatus', 'Claim document uploaded successfully', 'success');
            completeStep(2);
        } else {
            updateStatus('claimStatus', data.error || 'Upload failed', 'error');
        }
    } catch (error) {
        updateStatus('claimStatus', 'Error uploading document', 'error');
    } finally {
        hideLoading();
    }
}

async function analyzeDocuments(analysisType) {
    if (!workflowState.step1Completed || !workflowState.step2Completed) {
        updateStatus('analysisStatus', 'Please complete both document uploads first', 'error');
        return;
    }

    try {
        showLoading('Analyzing documents...');
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
            updateStatus('analysisStatus', 'Analysis completed successfully', 'success');
            // Redirect to chat view with the new analysis
            window.location.href = `/chat?chat_id=${data.chat_id}`;
        } else {
            updateStatus('analysisStatus', data.error || 'Analysis failed', 'error');
        }
    } catch (error) {
        updateStatus('analysisStatus', 'Error during analysis', 'error');
    } finally {
        hideLoading();
    }
}

function completeStep(step) {
    const indicator = document.getElementById(`step${step}Indicator`);
    indicator.classList.remove('bg-gray-300');
    indicator.classList.add('bg-blue-600');

    if (step === 1) {
        workflowState.step1Completed = true;
        enableStep(2);
        updateProgressBar(2);
        document.getElementById('step2Guidance').textContent = 'Upload your claim document for analysis.';
    } else if (step === 2) {
        workflowState.step2Completed = true;
        enableStep(3);
        updateProgressBar(3);
        document.getElementById('step3Guidance').textContent = 'Select an analysis option to process your documents.';
    }
}

function enableStep(step) {
    const section = document.getElementById(`step${step}Section`);
    section.classList.remove('opacity-50');
    
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
    } else if (step === 3) {
        document.querySelectorAll('.analysis-btn').forEach(btn => {
            btn.disabled = true;
        });
    }
}

function updateProgressBar(step) {
    const progressBar = document.getElementById('progressBar');
    progressBar.style.width = `${(step / 3) * 100}%`;
}

function updateStatus(elementId, message, type = 'processing') {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = message;
        element.className = `status-message status-${type}`;
        if (type === 'error') {
            element.classList.add('animate-shake');
        }
    }
}
