/**
 * Main JavaScript file for Bybit Trading Bot Web Interface
 * Enhanced with modern UI features
 */

// Format number with commas
function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return parseFloat(num).toLocaleString(undefined, { maximumFractionDigits: 8 });
}

// Format currency
function formatCurrency(num, decimals = 2) {
    if (num === null || num === undefined) return '0.00';
    return parseFloat(num).toFixed(decimals);
}

// Format percentage
function formatPercentage(num, decimals = 2) {
    if (num === null || num === undefined) return '0.00%';
    return parseFloat(num).toFixed(decimals) + '%';
}

// Format date
function formatDate(dateString) {
    if (!dateString) return '';
    try {
        const date = new Date(dateString);
        return date.toLocaleString();
    } catch (e) {
        return dateString;
    }
}

// Format price based on asset precision
function formatPrice(price, symbol = 'BTCUSDT') {
    if (price === null || price === undefined) return '0';

    // Default precision based on common assets
    let precision = 2;

    if (symbol.includes('BTC')) {
        precision = 2;
    } else if (symbol.includes('ETH')) {
        precision = 2;
    } else if (symbol.includes('SOL')) {
        precision = 3;
    } else {
        // For other assets, determine dynamically
        const priceStr = price.toString();
        const decimalIndex = priceStr.indexOf('.');

        if (decimalIndex !== -1) {
            const decimalPart = priceStr.substring(decimalIndex + 1);
            // Find first non-zero digit after decimal
            let firstNonZero = 0;
            for (let i = 0; i < decimalPart.length; i++) {
                if (decimalPart[i] !== '0') {
                    firstNonZero = i;
                    break;
                }
            }
            precision = Math.min(firstNonZero + 2, 8); // At least 2 significant digits, max 8
        }
    }

    return parseFloat(price).toFixed(precision);
}

// Show notification using the new toast system
function showNotification(message, type = 'info') {
    if (typeof window.showToast === 'function') {
        window.showToast(message, type);
    } else {
        // Fallback to old alert system
        const alertClass = type === 'success' ? 'alert-success' :
                          type === 'error' ? 'alert-danger' :
                          type === 'warning' ? 'alert-warning' : 'alert-info';

        const alertHtml = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;

        // Add alert to the top of the content area
        const contentArea = document.querySelector('.container-fluid');
        if (contentArea) {
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = alertHtml;
            contentArea.insertBefore(tempDiv.firstChild, contentArea.firstChild);

            // Auto-dismiss after 5 seconds
            setTimeout(() => {
                const alerts = document.querySelectorAll('.alert');
                if (alerts.length > 0) {
                    const bsAlert = new bootstrap.Alert(alerts[0]);
                    bsAlert.close();
                }
            }, 5000);
        }
    }
}

// Show loading spinner
function showLoading() {
    if (typeof window.showLoading === 'function') {
        window.showLoading();
    }
}

// Hide loading spinner
function hideLoading() {
    if (typeof window.hideLoading === 'function') {
        window.hideLoading();
    }
}

// Format trade side with icon
function formatTradeSide(side) {
    if (side === 'Buy' || side === 'Long') {
        return `<span class="badge bg-success"><i class="fas fa-arrow-up me-1"></i>${side}</span>`;
    } else if (side === 'Sell' || side === 'Short') {
        return `<span class="badge bg-danger"><i class="fas fa-arrow-down me-1"></i>${side}</span>`;
    } else {
        return `<span class="badge bg-secondary">${side}</span>`;
    }
}

// Format profit/loss with color
function formatPnL(pnl) {
    const value = parseFloat(pnl);
    if (value > 0) {
        return `<span class="profit">+${formatCurrency(value)}</span>`;
    } else if (value < 0) {
        return `<span class="loss">${formatCurrency(value)}</span>`;
    } else {
        return `<span>${formatCurrency(value)}</span>`;
    }
}

// Format percentage with color
function formatColorPercentage(value) {
    const num = parseFloat(value);
    if (num > 0) {
        return `<span class="profit">+${formatPercentage(num)}</span>`;
    } else if (num < 0) {
        return `<span class="loss">${formatPercentage(num)}</span>`;
    } else {
        return `<span>${formatPercentage(num)}</span>`;
    }
}

// Create a confirmation dialog
function confirmAction(message, callback) {
    // Create modal if it doesn't exist
    let confirmModal = document.getElementById('confirm-modal');

    if (!confirmModal) {
        const modalHtml = `
            <div class="modal fade" id="confirm-modal" tabindex="-1" aria-labelledby="confirm-modal-label" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="confirm-modal-label">Confirmation</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body" id="confirm-modal-message">
                            Are you sure?
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary" id="confirm-modal-confirm">Confirm</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);
        confirmModal = document.getElementById('confirm-modal');
    }

    // Set message and callback
    document.getElementById('confirm-modal-message').textContent = message;

    // Remove previous event listener if exists
    const confirmBtn = document.getElementById('confirm-modal-confirm');
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

    // Add new event listener
    newConfirmBtn.addEventListener('click', function() {
        const modal = bootstrap.Modal.getInstance(confirmModal);
        modal.hide();
        if (typeof callback === 'function') {
            callback();
        }
    });

    // Show modal
    const modal = new bootstrap.Modal(confirmModal);
    modal.show();
}

// Document ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Add animation classes to cards
    document.querySelectorAll('.card').forEach(card => {
        card.classList.add('fade-in');
    });

    // Add event listeners for collapsible sections
    document.querySelectorAll('[data-bs-toggle="collapse"]').forEach(button => {
        button.addEventListener('click', function() {
            const icon = this.querySelector('i.fas');
            if (icon) {
                if (icon.classList.contains('fa-chevron-down')) {
                    icon.classList.replace('fa-chevron-down', 'fa-chevron-up');
                } else {
                    icon.classList.replace('fa-chevron-up', 'fa-chevron-down');
                }
            }
        });
    });
});
