/**
 * UI Enhancements for Bybit Trading Bot Web Interface
 * This file contains additional UI functionality for the modern interface
 */

// Initialize UI enhancements when document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips with custom styling
    initTooltips();
    
    // Initialize popovers with custom styling
    initPopovers();
    
    // Add animation classes to cards
    animateCards();
    
    // Add event listeners for collapsible sections
    setupCollapsibleSections();
    
    // Initialize refresh buttons with loading animation
    setupRefreshButtons();
    
    // Setup chart toolbar positioning
    setupChartToolbar();
    
    // Setup timeframe buttons
    setupTimeframeButtons();
    
    // Setup export functionality
    setupExportButtons();
    
    // Setup log controls
    setupLogControls();
});

// Initialize tooltips with custom styling
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl, {
            boundary: document.body,
            template: '<div class="tooltip" role="tooltip"><div class="tooltip-arrow"></div><div class="tooltip-inner"></div></div>'
        });
    });
}

// Initialize popovers with custom styling
function initPopovers() {
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl, {
            trigger: 'focus',
            html: true
        });
    });
}

// Add animation classes to cards
function animateCards() {
    document.querySelectorAll('.card').forEach((card, index) => {
        card.classList.add('fade-in');
        card.style.animationDelay = `${index * 0.05}s`;
    });
}

// Add event listeners for collapsible sections
function setupCollapsibleSections() {
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
}

// Initialize refresh buttons with loading animation
function setupRefreshButtons() {
    document.querySelectorAll('[id$="-refresh"]').forEach(button => {
        button.addEventListener('click', function() {
            const originalHtml = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            this.disabled = true;
            
            // Simulate refresh (in a real implementation, this would be an actual data refresh)
            setTimeout(() => {
                this.innerHTML = originalHtml;
                this.disabled = false;
                showToast('Data refreshed successfully', 'success');
            }, 1000);
        });
    });
    
    // Special handling for specific refresh buttons
    if (document.getElementById('refresh-balance')) {
        document.getElementById('refresh-balance').addEventListener('click', function() {
            fetchBalance();
        });
    }
    
    if (document.getElementById('refresh-positions')) {
        document.getElementById('refresh-positions').addEventListener('click', function() {
            fetchPositions();
        });
    }
    
    if (document.getElementById('refresh-chart')) {
        document.getElementById('refresh-chart').addEventListener('click', function() {
            fetchMarketData();
        });
    }
    
    if (document.getElementById('refresh-performance')) {
        document.getElementById('refresh-performance').addEventListener('click', function() {
            fetchPerformanceData();
        });
    }
}

// Setup chart toolbar positioning
function setupChartToolbar() {
    const chartContainer = document.querySelector('.chart-container');
    const chartToolbar = document.querySelector('.chart-toolbar');
    
    if (chartContainer && chartToolbar) {
        // Position the toolbar at the top-right of the chart container
        chartToolbar.style.position = 'absolute';
        chartToolbar.style.top = '10px';
        chartToolbar.style.right = '10px';
        chartToolbar.style.zIndex = '10';
    }
}

// Setup timeframe buttons
function setupTimeframeButtons() {
    const timeframeButtons = document.querySelectorAll('.timeframe-btn');
    
    timeframeButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            timeframeButtons.forEach(btn => btn.classList.remove('active'));
            
            // Add active class to clicked button
            this.classList.add('active');
            
            // Get timeframe from button id
            const timeframe = this.id.split('-')[1];
            
            // Update charts with new timeframe
            if (typeof updateTimeframe === 'function') {
                updateTimeframe(timeframe);
            } else {
                console.log(`Switching to timeframe: ${timeframe}`);
                // Fallback if updateTimeframe function is not defined
                fetchMarketData(timeframe);
            }
        });
    });
}

// Setup export buttons
function setupExportButtons() {
    // Export trades as JSON
    const exportTradesJson = document.getElementById('export-trades-json');
    if (exportTradesJson) {
        exportTradesJson.addEventListener('click', function(e) {
            e.preventDefault();
            exportData('trades', 'json');
        });
    }
    
    // Export trades as CSV
    const exportTradesCsv = document.getElementById('export-trades-csv');
    if (exportTradesCsv) {
        exportTradesCsv.addEventListener('click', function(e) {
            e.preventDefault();
            exportData('trades', 'csv');
        });
    }
    
    // Export settings
    const exportSettings = document.getElementById('export-settings');
    if (exportSettings) {
        exportSettings.addEventListener('click', function(e) {
            e.preventDefault();
            exportData('settings', 'json');
        });
    }
    
    // Export log
    const exportLog = document.getElementById('export-log');
    if (exportLog) {
        exportLog.addEventListener('click', function(e) {
            e.preventDefault();
            exportLogData();
        });
    }
}

// Export data function
function exportData(dataType, format) {
    showLoading();
    
    fetch(`/api/export?type=${dataType}&format=${format}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'OK') {
                // Create a blob and download link
                const blob = new Blob([JSON.stringify(data.data, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = data.filename || `${dataType}_export.${format}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                showToast(`${dataType} exported successfully`, 'success');
            } else {
                showToast(`Failed to export ${dataType}: ${data.message}`, 'error');
            }
        })
        .catch(error => {
            console.error('Export error:', error);
            showToast(`Error exporting ${dataType}`, 'error');
        })
        .finally(() => {
            hideLoading();
        });
}

// Export log data
function exportLogData() {
    const logContainer = document.getElementById('log-container');
    if (!logContainer) return;
    
    // Get all log entries
    const logEntries = Array.from(logContainer.querySelectorAll('.log-entry')).map(entry => {
        const timestamp = entry.querySelector('.log-timestamp')?.innerText || '';
        const message = entry.innerText.replace(timestamp, '').trim();
        return { timestamp, message };
    });
    
    if (logEntries.length === 0) {
        showToast('No log entries to export', 'warning');
        return;
    }
    
    // Create a text file with log entries
    const logText = logEntries.map(entry => `${entry.timestamp} ${entry.message}`).join('\n');
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `bot_log_${new Date().toISOString().replace(/[:.]/g, '-')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showToast('Log exported successfully', 'success');
}

// Setup log controls
function setupLogControls() {
    const clearLogBtn = document.getElementById('clear-log');
    if (clearLogBtn) {
        clearLogBtn.addEventListener('click', function() {
            const logContainer = document.getElementById('log-container');
            if (logContainer) {
                // Ask for confirmation
                if (confirm('Are you sure you want to clear all log entries?')) {
                    logContainer.innerHTML = `
                        <div class="text-center py-5">
                            <i class="fas fa-clipboard-list mb-3" style="font-size: 2rem; opacity: 0.3;"></i>
                            <p>No log entries yet</p>
                        </div>
                    `;
                    showToast('Log cleared', 'info');
                }
            }
        });
    }
}

// Add a log entry to the log container
function addLogEntry(message, level, timestamp) {
    const logContainer = document.getElementById('log-container');
    if (!logContainer) return;

    // Remove placeholder if present
    if (logContainer.querySelector('.text-center')) {
        logContainer.innerHTML = '';
    }

    // Create log entry
    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';
    
    const timestampSpan = document.createElement('span');
    timestampSpan.className = 'log-timestamp';
    timestampSpan.textContent = `[${timestamp}]`;
    
    const messageSpan = document.createElement('span');
    messageSpan.className = `log-${level}`;
    messageSpan.textContent = ` ${message}`;
    
    logEntry.appendChild(timestampSpan);
    logEntry.appendChild(messageSpan);

    // Add to container
    logContainer.appendChild(logEntry);

    // Scroll to bottom
    logContainer.scrollTop = logContainer.scrollHeight;
}

// Update signal display
function updateSignal(side) {
    const signalElement = document.getElementById('signal');
    const signalTimeElement = document.getElementById('signal-time');
    
    if (signalElement) {
        let signalHtml = '';
        let signalClass = '';
        
        if (side === 'Buy' || side === 'Long') {
            signalHtml = '<i class="fas fa-arrow-up me-1"></i>LONG';
            signalClass = 'signal-long';
        } else if (side === 'Sell' || side === 'Short') {
            signalHtml = '<i class="fas fa-arrow-down me-1"></i>SHORT';
            signalClass = 'signal-short';
        } else {
            signalHtml = '<i class="fas fa-minus me-1"></i>NONE';
            signalClass = 'signal-none';
        }
        
        signalElement.innerHTML = `<span class="signal-badge ${signalClass}">${signalHtml}</span>`;
    }
    
    if (signalTimeElement) {
        const now = new Date();
        signalTimeElement.textContent = `Last update: ${now.toLocaleTimeString()}`;
    }
}

// Update bot status display
function updateBotStatus(status) {
    const statusElement = document.getElementById('bot-status');
    
    if (statusElement) {
        let statusHtml = '';
        let statusClass = '';
        
        switch (status.toLowerCase()) {
            case 'running':
                statusHtml = '<i class="fas fa-play-circle me-1"></i>RUNNING';
                statusClass = 'bg-success';
                break;
            case 'stopped':
                statusHtml = '<i class="fas fa-stop-circle me-1"></i>STOPPED';
                statusClass = 'bg-danger';
                break;
            case 'paused':
                statusHtml = '<i class="fas fa-pause-circle me-1"></i>PAUSED';
                statusClass = 'bg-warning';
                break;
            default:
                statusHtml = '<i class="fas fa-question-circle me-1"></i>UNKNOWN';
                statusClass = 'bg-secondary';
        }
        
        statusElement.innerHTML = `<span class="badge ${statusClass}">${statusHtml}</span>`;
        
        // Update button states
        const startButton = document.getElementById('start-bot');
        const stopButton = document.getElementById('stop-bot');
        
        if (startButton && stopButton) {
            if (status.toLowerCase() === 'running') {
                startButton.disabled = true;
                stopButton.disabled = false;
            } else {
                startButton.disabled = false;
                stopButton.disabled = true;
            }
        }
    }
}

// Format positions for display
function formatPositions(positions) {
    if (!positions || positions.length === 0) {
        return '';
    }
    
    let html = '';
    
    positions.forEach(position => {
        const profitClass = parseFloat(position.unrealizedPnl) > 0 ? 'profit' : 
                           parseFloat(position.unrealizedPnl) < 0 ? 'loss' : '';
        
        const sideClass = position.side === 'Buy' ? 'long' : 'short';
        
        html += `
        <div class="col-md-6 mb-3">
            <div class="card position-card ${sideClass}">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">${position.symbol}</h5>
                    <span class="badge ${position.side === 'Buy' ? 'bg-success' : 'bg-danger'}">
                        ${position.side}
                    </span>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-6">
                            <p class="mb-1"><strong>Size:</strong> ${position.size}</p>
                            <p class="mb-1"><strong>Entry Price:</strong> ${position.entryPrice}</p>
                            <p class="mb-1"><strong>Mark Price:</strong> ${position.markPrice}</p>
                            <p class="mb-1"><strong>Leverage:</strong> ${position.leverage}x</p>
                        </div>
                        <div class="col-6">
                            <p class="mb-1"><strong>PnL:</strong> <span class="${profitClass}">${position.unrealizedPnl} (${position.unrealizedPnlPercent}%)</span></p>
                            <p class="mb-1"><strong>Liq. Price:</strong> ${position.liqPrice}</p>
                            <p class="mb-1"><strong>Take Profit:</strong> ${position.takeProfit !== '0.00' ? position.takeProfit : 'None'}</p>
                            <p class="mb-1"><strong>Stop Loss:</strong> ${position.stopLoss !== '0.00' ? position.stopLoss : 'None'}</p>
                        </div>
                    </div>
                    <div class="mt-3">
                        <button class="btn btn-sm btn-danger close-position-btn" data-symbol="${position.symbol}">
                            <i class="fas fa-times-circle me-1"></i>Close Position
                        </button>
                    </div>
                </div>
            </div>
        </div>
        `;
    });
    
    return `<div class="row">${html}</div>`;
}

// Update performance metrics display
function updatePerformanceMetrics(data) {
    if (!data) return;
    
    // Update total trades
    const totalTradesElement = document.getElementById('total-trades');
    if (totalTradesElement) {
        totalTradesElement.textContent = data.total_trades || '0';
        totalTradesElement.className = 'performance-value neutral-value';
    }
    
    // Update win rate
    const winRateElement = document.getElementById('win-rate');
    if (winRateElement) {
        const winRate = data.win_rate || 0;
        winRateElement.textContent = `${winRate}%`;
        
        if (winRate > 50) {
            winRateElement.className = 'performance-value positive-value';
        } else if (winRate < 40) {
            winRateElement.className = 'performance-value negative-value';
        } else {
            winRateElement.className = 'performance-value neutral-value';
        }
    }
    
    // Update profit factor
    const profitFactorElement = document.getElementById('profit-factor');
    if (profitFactorElement) {
        const profitFactor = data.profit_factor || 0;
        profitFactorElement.textContent = profitFactor.toFixed(2);
        
        if (profitFactor > 1.5) {
            profitFactorElement.className = 'performance-value positive-value';
        } else if (profitFactor < 1) {
            profitFactorElement.className = 'performance-value negative-value';
        } else {
            profitFactorElement.className = 'performance-value neutral-value';
        }
    }
    
    // Update total PnL
    const totalPnlElement = document.getElementById('total-pnl');
    if (totalPnlElement) {
        const totalPnl = data.total_pnl || 0;
        totalPnlElement.textContent = `${totalPnl.toFixed(2)} USDT`;
        
        if (totalPnl > 0) {
            totalPnlElement.className = 'performance-value positive-value';
        } else if (totalPnl < 0) {
            totalPnlElement.className = 'performance-value negative-value';
        } else {
            totalPnlElement.className = 'performance-value neutral-value';
        }
    }
}
