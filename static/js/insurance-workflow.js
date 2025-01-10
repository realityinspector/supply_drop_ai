// Workflow State Management
const workflowState = {
    currentStep: 1,
    isProcessing: false,
    documents: {
        requirements: null,
        claim: null
    }
};

// UI State Management
const UI = {
    elements: {
        loadingOverlay: null,
        statusMessage: null,
        reuseButton: null,
        documentSelect: null,
        progressBar: null
    },

    initialize() {
        // Cache DOM elements
        this.elements = {
            loadingOverlay: document.getElementById('loadingOverlay'),
            statusMessage: document.getElementById('requirementsStatus'),
            reuseButton: document.getElementById('reuseDocumentBtn'),
            documentSelect: document.getElementById('existingDocumentSelect'),
            progressBar: document.getElementById('progressBar')
        };

        // Initialize UI state
        this.updateButtonState();
        this.initializeEventListeners();
    },

    initializeEventListeners() {
        // Document selection change handler
        if (this.elements.documentSelect) {
            this.elements.documentSelect.addEventListener('change', () => {
                this.updateButtonState();
            });
        }

        // Reuse button click handler
        if (this.elements.reuseButton) {
            this.elements.reuseButton.addEventListener('click', async () => {
                if (!this.validateSelection()) return;
                await DocumentManager.reuseDocument(this.elements.documentSelect.value);
            });
        }
    },

    updateButtonState() {
        if (this.elements.reuseButton && this.elements.documentSelect) {
            this.elements.reuseButton.disabled = !this.elements.documentSelect.value;
        }
    },

    validateSelection() {
        if (!this.elements.documentSelect.value) {
            this.showStatus('Please select a document', 'error');
            return false;
        }
        return true;
    },

    showLoading() {
        if (this.elements.loadingOverlay) {
            this.elements.loadingOverlay.classList.remove('hidden');
            this.elements.loadingOverlay.style.opacity = '1';
        }
        this.showStatus('Processing document...', 'processing');
    },

    hideLoading() {
        if (this.elements.loadingOverlay) {
            this.elements.loadingOverlay.style.opacity = '0';
            setTimeout(() => this.elements.loadingOverlay.classList.add('hidden'), 300);
        }
    },

    showStatus(message, type = 'info') {
        if (this.elements.statusMessage) {
            this.elements.statusMessage.textContent = message;
            this.elements.statusMessage.className = 'status-message ' + 
                (type === 'error' ? 'text-red-600' : 
                 type === 'success' ? 'text-green-600' : 
                 'text-blue-600');
        }
    },

    updateProgress(step) {
        if (this.elements.progressBar) {
            const width = (step / 3) * 100;
            this.elements.progressBar.style.width = `${width}%`;
        }
    }
};

// Document Management
const DocumentManager = {
    async reuseDocument(documentId) {
        if (workflowState.isProcessing) return;

        try {
            workflowState.isProcessing = true;
            UI.showLoading();

            const response = await this.sendReuseRequest(documentId);
            await this.handleReuseResponse(response);

        } catch (error) {
            console.error('Document reuse error:', error);
            UI.showStatus(error.message || 'Failed to reuse document', 'error');
        } finally {
            workflowState.isProcessing = false;
            UI.hideLoading();
        }
    },

    async sendReuseRequest(documentId) {
        const response = await fetch('/insurance/reuse-document', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ document_id: documentId })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Server error occurred');
        }

        return data;
    },

    async handleReuseResponse(data) {
        if (!data.success) {
            throw new Error(data.error || 'Failed to process document');
        }

        // Update workflow state
        workflowState.documents.requirements = data.document_id;
        
        // Show success message briefly before redirect
        UI.showStatus('Document selected successfully! Redirecting...', 'success');
        
        // Short delay to show success message
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Redirect to next step
        window.location.href = '/insurance/wizard?step=2';
    }
};

// Initialize everything when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    UI.initialize();
});

// Export for potential testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { UI, DocumentManager, workflowState };
}