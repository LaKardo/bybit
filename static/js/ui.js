/**
 * UI Module - Handles all UI interactions, enhancements, settings, and utilities
 * Consolidates functionality from utils.js, ui-enhancements.js, chart-settings.js, and chart-enhancements.js
 */
const UI = (function() {
    'use strict';

    // --- Private Variables ---

    // Default settings for charts and UI
    const DEFAULT_SETTINGS = {
        timeframe: '15',
        symbol: 'BTCUSDT',
        theme: 'light',
        indicators: {
            ema: true,
            rsi: true,
            volume: true
        },
        chartType: 'candlestick',
        autoRefresh: true,
        maxLogEntries: 100
    };

    // Current settings (initialized with defaults)
    let _currentSettings = { ...DEFAULT_SETTINGS };

    // State for UI elements and charts
    const _state = {
        charts: {
            price: null,
            indicators: null,
            volume: null,
            equity: null
        },
        syncEnabled: true, // For chart synchronization
        zoomEnabled: true, // For chart zoom
        isBotRunning: false // Track bot status
    };

    const DEFAULT_TOAST_DURATION = 5000; // Default duration for toast notifications

    // --- Private Utility Functions (from utils.js) ---

    /**
     * Format a number with thousands separators and fixed decimals
     * @param {number} number - The number to format
     * @param {number} decimals - Number of decimal places
     * @returns {string} Formatted number
     */
    function formatNumber(number, decimals = 2) {
        if (number === undefined || number === null) return '0.00';
        return parseFloat(number).toLocaleString('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    }

    /**
     * Format a number as currency with fixed decimals
     * @param {number} number - The number to format
     * @param {number} decimals - Number of decimal places
     * @returns {string} Formatted currency
     */
    function formatCurrency(number, decimals = 2) {
        if (number === undefined || number === null) return '0.00';
        return parseFloat(number).toFixed(decimals);
    }

    /**
     * Format a number as percentage with fixed decimals
     * @param {number} number - The number to format
     * @param {number} decimals - Number of decimal places
     * @returns {string} Formatted percentage
     */
    function formatPercentage(number, decimals = 2) {
        if (number === undefined || number === null) return '0.00%';
        return parseFloat(number).toFixed(decimals) + '%';
    }

    /**
     * Format a date string
     * @param {string} dateString - The date string to format
     * @param {string} format - The format to use (if moment.js is available)
     * @returns {string} Formatted date
     */
    function formatDate(dateString, format = 'YYYY-MM-DD HH:mm:ss') {
        if (!dateString) return '';
        if (typeof moment !== 'undefined') {
            return moment(dateString).format(format);
        }
        try {
            const date = new Date(dateString);
            return date.toLocaleString();
        } catch (e) {
            return dateString;
        }
    }

    /**
     * Format a price with appropriate precision based on the symbol
     * @param {number} price - The price to format
     * @param {string} symbol - The trading symbol
     * @returns {string} Formatted price
     */
    function formatPrice(price, symbol = 'BTCUSDT') {
        if (price === null || price === undefined) return '0';
        let precision = 2;

        // Basic precision logic, could be enhanced with symbol info from API
        if (symbol.includes('BTC')) {
            precision = 2;
        } else if (symbol.includes('ETH')) {
            precision = 2;
        } else if (symbol.includes('SOL')) {
            precision = 3;
        } else {
            const priceStr = price.toString();
            const decimalIndex = priceStr.indexOf('.');
            if (decimalIndex !== -1) {
                const decimalPart = priceStr.substring(decimalIndex + 1);
                let firstNonZero = 0;
                for (let i = 0; i < decimalPart.length; i++) {
                    if (decimalPart[i] !== '0') {
                        firstNonZero = i;
                        break;
                    }
                }
                precision = Math.min(firstNonZero + 2, 8); // Max 8 decimals
            }
        }

        return parseFloat(price).toFixed(precision);
    }

    /**
     * Show a notification toast or alert
     * @param {string} message - The message to display
     * @param {string} type - The type of notification (success, error, warning, info)
     */
    function showNotification(message, type = 'info') {
        // Check if a global showToast function exists (e.g., from a library)
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
        } else {
            // Fallback to Bootstrap alerts or console log
            const alertClass = type === 'success' ? 'alert-success' :
                               type === 'error' ? 'alert-danger' :
                               type === 'warning' ? 'alert-warning' : 'alert-info';
            const alertHtml = `
                <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
            const contentArea = document.querySelector('.container-fluid'); // Adjust selector as needed
            if (contentArea) {
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = alertHtml;
                contentArea.insertBefore(tempDiv.firstChild, contentArea.firstChild);

                // Auto-dismiss after a duration
                setTimeout(() => {
                    const alerts = document.querySelectorAll('.alert');
                    if (alerts.length > 0 && typeof bootstrap !== 'undefined') {
                        const bsAlert = new bootstrap.Alert(alerts[0]);
                        bsAlert.close();
                    }
                }, DEFAULT_TOAST_DURATION);
            } else {
                // Fallback: Log to console if no other notification method is available
                // Consider implementing a more robust fallback or removing this log
            }
        }
    }

    /**
     * Format trade side with appropriate styling
     * @param {string} side - The trade side (Buy, Sell, Long, Short)
     * @returns {string} HTML for formatted trade side
     */
    function formatTradeSide(side) {
        if (side === 'Buy' || side === 'Long') {
            return `<span class="badge bg-success"><i class="fas fa-arrow-up me-1"></i>${side}</span>`;
        } else if (side === 'Sell' || side === 'Short') {
            return `<span class="badge bg-danger"><i class="fas fa-arrow-down me-1"></i>${side}</span>`;
        } else {
            return `<span class="badge bg-secondary">${side}</span>`;
        }
    }

    /**
     * Format profit/loss with appropriate styling
     * @param {number|string} pnl - The profit/loss value
     * @returns {string} HTML for formatted P&L
     */
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

    /**
     * Format percentage with color coding
     * @param {number|string} value - The percentage value
     * @returns {string} HTML for formatted percentage
     */
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

    /**
     * Show a confirmation modal
     * @param {string} message - The confirmation message
     * @param {Function} callback - Function to call when confirmed
     */
    function confirmAction(message, callback) {
        let confirmModal = document.getElementById('confirm-modal');
        if (!confirmModal) {
            // Create modal if it doesn't exist
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

        // Update message and set up confirm button listener
        document.getElementById('confirm-modal-message').textContent = message;
        const confirmBtn = document.getElementById('confirm-modal-confirm');
        // Clone and replace to remove previous event listeners
        const newConfirmBtn = confirmBtn.cloneNode(true);
        confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

        newConfirmBtn.addEventListener('click', function() {
            if (typeof bootstrap !== 'undefined') {
                const modal = bootstrap.Modal.getInstance(confirmModal);
                if (modal) modal.hide();
            }
            if (typeof callback === 'function') {
                callback();
            }
        });

        // Show the modal
        if (typeof bootstrap !== 'undefined') {
            const modal = new bootstrap.Modal(confirmModal);
            modal.show();
        } else {
            // Fallback to browser confirm
            if (confirm(message) && typeof callback === 'function') {
                callback();
            }
        }
    }

    /**
     * Debounce a function call
     * @param {Function} func - The function to debounce
     * @param {number} wait - The debounce wait time in ms
     * @returns {Function} Debounced function
     */
    function debounce(func, wait = 300) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    /**
     * Throttle a function call
     * @param {Function} func - The function to throttle
     * @param {number} limit - The throttle limit in ms
     * @returns {Function} Throttled function
     */
    function throttle(func, limit = 300) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    /**
     * Get a cookie value by name
     * @param {string} name - The cookie name
     * @returns {string} Cookie value
     */
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return '';
    }

    /**
     * Set a cookie
     * @param {string} name - The cookie name
     * @param {string} value - The cookie value
     * @param {number} days - Days until expiration
     */
    function setCookie(name, value, days = 30) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        const expires = `expires=${date.toUTCString()}`;
        document.cookie = `${name}=${value};${expires};path=/`;
    }

    // --- Private Settings Functions (from chart-settings.js) ---

    function _loadSettings() {
        try {
            const savedSettings = localStorage.getItem('bybit_chart_settings');
            if (savedSettings) {
                // Merge saved settings with defaults
                _currentSettings = { ...DEFAULT_SETTINGS, ...JSON.parse(savedSettings) };
            } else {
                // Using default settings as none were saved
            }
        } catch (error) {
            console.error('Error loading chart settings:', error);
        }
    }

    function _saveSettings() {
        try {
            localStorage.setItem('bybit_chart_settings', JSON.stringify(_currentSettings));
            return true;
        } catch (error) {
            console.error('Error saving chart settings:', error);
            return false;
        }
    }

    function savePreference(key, value) {
        if (key.includes('.')) {
            // Handle nested properties (e.g., 'indicators.ema')
            const parts = key.split('.');
            const mainKey = parts[0];
            const subKey = parts[1];

            if (!_currentSettings[mainKey]) {
                _currentSettings[mainKey] = {};
            }

            _currentSettings[mainKey][subKey] = value;
        } else {
            // Handle top-level properties
            _currentSettings[key] = value;
        }

        _saveSettings();
    }

    function getPreference(key, defaultValue) {
        if (key.includes('.')) {
            // Handle nested properties
            const parts = key.split('.');
            const mainKey = parts[0];
            const subKey = parts[1];

            if (!_currentSettings[mainKey]) {
                return defaultValue;
            }

            return _currentSettings[mainKey][subKey] !== undefined ?
                _currentSettings[mainKey][subKey] : defaultValue;
        }

        // Handle top-level properties
        return _currentSettings[key] !== undefined ?
            _currentSettings[key] : defaultValue;
    }

    function resetToDefaults() {
        _currentSettings = { ...DEFAULT_SETTINGS };
        _saveSettings();
    }

    function applySettingsToCharts() {
        const theme = getPreference('theme', 'light');
        const isDark = theme === 'dark';

        const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
        const textColor = isDark ? 'rgba(255, 255, 255, 0.7)' : 'rgba(0, 0, 0, 0.7)';

        // Update chart options for all managed charts
        Object.values(_state.charts).forEach(chart => {
            if (!chart) return;

            // Update grid and text colors
            if (chart.options.scales.x) {
                 chart.options.scales.x.grid.color = gridColor;
                 chart.options.scales.x.ticks.color = textColor;
            }
             if (chart.options.scales.y) {
                chart.options.scales.y.grid.color = gridColor;
                chart.options.scales.y.ticks.color = textColor;
             }
             // Handle secondary axes like RSI
             if (chart.options.scales.rsi) {
                 chart.options.scales.rsi.grid.color = gridColor;
                 chart.options.scales.rsi.ticks.color = textColor;
             }


            // Update chart
            chart.update();
        });
    }

    // --- Private UI Enhancement Functions (from ui-enhancements.js) ---

    function setupRefreshButtons() {
        document.querySelectorAll('[id$="-refresh"]').forEach(button => {
            button.addEventListener('click', function() {
                const originalHtml = this.innerHTML;
                this.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                this.disabled = true;

                // Simulate loading for a brief period
                setTimeout(() => {
                    this.innerHTML = originalHtml;
                    this.disabled = false;
                    showNotification('Data refreshed successfully', 'success');
                }, 500); // Reduced timeout

                // Trigger actual data fetch based on button ID
                if (typeof DataModule !== 'undefined') {
                    switch (this.id) {
                        case 'refresh-balance':
                            DataModule.fetchBalance();
                            break;
                        case 'refresh-positions':
                            DataModule.fetchPositions();
                            break;
                        case 'refresh-chart':
                            DataModule.fetchMarketData();
                            break;
                        case 'refresh-performance':
                            DataModule.fetchPerformanceData();
                            break;
                        case 'refresh-all': // Global refresh button
                             DataModule.fetchData();
                             break;
                    }
                } else {
                    console.warn('DataModule not available to fetch data.');
                }
            });
        });
    }

    function setupChartToolbar() {
        const chartContainer = document.querySelector('.chart-container');
        const chartToolbar = document.querySelector('.chart-toolbar'); // Assuming this class exists

        if (chartContainer && chartToolbar) {
            // Position toolbar absolutely within the container
            chartToolbar.style.position = 'absolute';
            chartToolbar.style.top = '10px';
            chartToolbar.style.right = '10px';
            chartToolbar.style.zIndex = '10'; // Ensure it's above the chart
        }
    }

    function setupTimeframeButtons() {
        const timeframeButtons = document.querySelectorAll('.timeframe-btn'); // Assuming this class exists

        timeframeButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Update active state
                timeframeButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');

                // Extract timeframe from button ID (e.g., "tf-15" -> "15")
                const timeframe = this.id.replace('tf-', '');

                // Update timeframe in DataModule and save preference
                if (typeof DataModule !== 'undefined' && DataModule.setTimeframe) {
                    DataModule.setTimeframe(timeframe);
                    savePreference('timeframe', timeframe);
                } else {
                    console.warn('DataModule not available to set timeframe.');
                }
            });
        });

        // Set initial active state based on saved preference or default
        const savedTimeframe = getPreference('timeframe', DEFAULT_SETTINGS.timeframe);
        const initialButton = document.getElementById(`tf-${savedTimeframe}`);
        if (initialButton) {
            initialButton.classList.add('active');
        }
    }

    function setupExportButtons() {
        // Define export buttons and their actions
        const exportButtons = {
            'export-trades-json': () => exportData('trades', 'json'),
            'export-trades-csv': () => exportData('trades', 'csv'),
            'export-settings': () => exportData('settings', 'json'),
            'export-log': () => exportLogData()
        };

        // Add event listeners to each button if it exists
        Object.entries(exportButtons).forEach(([id, callback]) => {
            const button = document.getElementById(id);
            if (button) {
                button.addEventListener('click', function(e) {
                    e.preventDefault(); // Prevent default link behavior
                    callback();
                });
            }
        });
    }

    /**
     * Export data to file by calling backend API
     * @param {string} dataType - Type of data to export (e.g., 'trades', 'settings')
     * @param {string} format - Format to export data in (e.g., 'json', 'csv')
     */
    function exportData(dataType, format) {
        if (typeof showLoading === 'function') {
            showLoading(); // Assuming a global showLoading function exists
        }

        if (typeof API === 'undefined' || typeof API.exportData !== 'function') {
            console.error('API module or exportData function not available.');
            if (typeof hideLoading === 'function') hideLoading();
            showNotification(`Export failed: API not available.`, 'error');
            return;
        }

        API.exportData(dataType, format, function(data) {
            if (typeof hideLoading === 'function') {
                hideLoading(); // Assuming a global hideLoading function exists
            }

            if (data.status === 'OK' && data.data) {
                try {
                    const blob = new Blob([JSON.stringify(data.data, null, 2)], { type: 'application/json' }); // Assuming JSON data for now
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = data.filename || `${dataType}_export.${format}`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    showNotification(`${dataType} exported successfully`, 'success');
                } catch (error) {
                    console.error('Error creating or downloading blob:', error);
                    showNotification(`Failed to export ${dataType}: Download error.`, 'error');
                }
            } else {
                showNotification(`Failed to export ${dataType}: ${data.message || 'Unknown error'}`, 'error');
            }
        });
    }

    /**
     * Export log data from the UI log container to a text file
     */
    function exportLogData() {
        const logContainer = document.getElementById('log-container');
        if (!logContainer) {
            console.warn('Log container not found.');
            showNotification('No log container found to export.', 'warning');
            return;
        }

        const logEntries = Array.from(logContainer.querySelectorAll('.log-entry')).map(entry => {
            const timestamp = entry.querySelector('.log-timestamp')?.innerText || '';
            // Get the full text content and remove the timestamp part
            const fullText = entry.innerText;
            const message = fullText.replace(timestamp, '').trim();
            return `${timestamp} ${message}`;
        }).join('\n');

        if (logEntries.trim().length === 0) {
            showNotification('No log entries to export', 'warning');
            return;
        }

        try {
            const blob = new Blob([logEntries], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `bot_log_${new Date().toISOString().replace(/[:.]/g, '-')}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            showNotification('Log exported successfully', 'success');
        } catch (error) {
            console.error('Error creating or downloading log blob:', error);
            showNotification('Failed to export log data.', 'error');
        }
    }

    function setupLogControls() {
        const clearLogBtn = document.getElementById('clear-log');
        if (clearLogBtn) {
            clearLogBtn.addEventListener('click', function() {
                const logContainer = document.getElementById('log-container');
                if (logContainer) {
                    confirmAction('Are you sure you want to clear all log entries?', function() {
                        logContainer.innerHTML = `
                            <div class="text-center py-5 text-muted">
                                <i class="fas fa-clipboard-list mb-3" style="font-size: 2rem; opacity: 0.5;"></i>
                                <p>No log entries yet</p>
                            </div>
                        `;
                        showNotification('Log cleared', 'info');
                    });
                }
            });
        }

        // Set up log level filters if they exist
        const logLevelButtons = document.querySelectorAll('.log-level-btn'); // Assuming this class exists
        if (logLevelButtons.length > 0) {
            logLevelButtons.forEach(button => {
                button.addEventListener('click', function() {
                    const level = this.getAttribute('data-level');
                    const logContainer = document.getElementById('log-container');

                    // Update active state
                    logLevelButtons.forEach(btn => btn.classList.remove('active'));
                    this.classList.add('active');

                    if (logContainer) {
                        const logEntries = logContainer.querySelectorAll('.log-entry');
                        if (level === 'all') {
                            // Show all log entries
                            logEntries.forEach(entry => {
                                entry.style.display = 'block';
                            });
                        } else {
                            // Filter log entries by level
                            logEntries.forEach(entry => {
                                // Check if any span with the specific log level class exists within the entry
                                if (entry.querySelector(`.log-${level}`)) {
                                    entry.style.display = 'block';
                                } else {
                                    entry.style.display = 'none';
                                }
                            });
                        }
                         // Ensure the "No log entries yet" message is hidden if there are entries
                        const noLogsMessage = logContainer.querySelector('.text-center.text-muted');
                        if (noLogsMessage) {
                            noLogsMessage.style.display = logEntries.length > 0 && level === 'all' ? 'none' : 'block';
                             if (logEntries.length > 0 && level !== 'all') {
                                 // If filtering, check if any entries match the filter
                                 const visibleEntries = logContainer.querySelectorAll('.log-entry:not([style*="display: none"])');
                                 if (visibleEntries.length === 0) {
                                     noLogsMessage.style.display = 'block';
                                     noLogsMessage.innerHTML = `
                                         <div class="text-center py-5 text-muted">
                                             <i class="fas fa-filter mb-3" style="font-size: 2rem; opacity: 0.5;"></i>
                                             <p>No log entries match the selected filter.</p>
                                         </div>
                                     `;
                                 } else {
                                      noLogsMessage.style.display = 'none';
                                 }
                             } else if (logEntries.length === 0) {
                                  noLogsMessage.style.display = 'block';
                                   noLogsMessage.innerHTML = `
                                         <div class="text-center py-5 text-muted">
                                             <i class="fas fa-clipboard-list mb-3" style="font-size: 2rem; opacity: 0.5;"></i>
                                             <p>No log entries yet</p>
                                         </div>
                                     `;
                             }
                        }
                    }
                });
            });
        }
    }

    /**
     * Add a log entry to the log container
     * @param {string} message - Log message
     * @param {string} level - Log level (info, warning, error, debug)
     * @param {string} timestamp - Timestamp for the log entry (optional)
     */
    function addLogEntry(message, level, timestamp) {
        const logContainer = document.getElementById('log-container');
        if (!logContainer) return;

        // Remove placeholder if present
        const placeholder = logContainer.querySelector('.text-center.text-muted');
        if (placeholder) {
            placeholder.remove();
        }

        // Create log entry elements
        const logEntry = document.createElement('div');
        logEntry.className = 'log-entry';

        const timestampSpan = document.createElement('span');
        timestampSpan.className = 'log-timestamp text-muted me-1';
        timestampSpan.textContent = `[${timestamp || new Date().toLocaleTimeString()}]`;

        const messageSpan = document.createElement('span');
        messageSpan.className = `log-message log-${level || 'info'}`; // Add log-message class
        messageSpan.textContent = message;

        // Assemble and append log entry
        logEntry.appendChild(timestampSpan);
        logEntry.appendChild(messageSpan);
        logContainer.appendChild(logEntry);

        // Scroll to bottom
        logContainer.scrollTop = logContainer.scrollHeight;

        // Trim log if it exceeds max entries
        const logEntries = logContainer.querySelectorAll('.log-entry');
        if (logEntries.length > _currentSettings.maxLogEntries) {
            for (let i = 0; i < logEntries.length - _currentSettings.maxLogEntries; i++) {
                logContainer.removeChild(logEntries[i]);
            }
        }
    }

    /**
     * Update trading signal display
     * @param {string} side - Signal side (Buy, Sell, Long, Short, or empty for none)
     */
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

    /**
     * Update bot status display and control buttons
     * @param {string} status - Bot status (running, stopped, paused, unknown)
     */
    function updateBotStatus(status) {
        const statusElement = document.getElementById('bot-status');
        if (!statusElement) return;

        // Define status configurations
        const statusConfigs = {
            running: {
                icon: 'play-circle',
                text: 'RUNNING',
                class: 'bg-success'
            },
            stopped: {
                icon: 'stop-circle',
                text: 'STOPPED',
                class: 'bg-danger'
            },
            paused: {
                icon: 'pause-circle',
                text: 'PAUSED',
                class: 'bg-warning'
            },
            default: {
                icon: 'question-circle',
                text: 'UNKNOWN',
                class: 'bg-secondary'
            }
        };

        // Get status config or default
        const statusKey = status ? status.toLowerCase() : 'default';
        const config = statusConfigs[statusKey] || statusConfigs.default;

        // Update status display
        statusElement.innerHTML = `
            <span class="badge ${config.class}">
                <i class="fas fa-${config.icon} me-1"></i>${config.text}
            </span>
        `;

        // Update control buttons
        const startButton = document.getElementById('start-bot');
        const stopButton = document.getElementById('stop-bot');
        const pauseButton = document.getElementById('pause-bot'); // Assuming a pause button exists

        _state.isBotRunning = statusKey === 'running';

        if (startButton) {
            startButton.disabled = _state.isBotRunning;
        }
        if (stopButton) {
            stopButton.disabled = !_state.isBotRunning;
        }
        if (pauseButton) {
             pauseButton.disabled = statusKey !== 'running'; // Only enable pause if running
        }


        // Add log entry for status change (avoid logging 'unknown' on initial load)
        if (statusKey !== 'unknown') {
             addLogEntry(`Bot status changed to ${config.text}`, 'info');
        }
    }

    /**
     * Initialize general UI components (tooltips, popovers, animations)
     */
    function initializeUIComponents() {
        if (typeof bootstrap === 'undefined') {
            console.warn('Bootstrap not available for UI component initialization.');
            return;
        }

        // Initialize tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.forEach(function(tooltipTriggerEl) {
            new bootstrap.Tooltip(tooltipTriggerEl, {
                boundary: document.body,
                template: '<div class="tooltip" role="tooltip"><div class="tooltip-arrow"></div><div class="tooltip-inner"></div></div>'
            });
        });

        // Initialize popovers
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.forEach(function(popoverTriggerEl) {
            new bootstrap.Popover(popoverTriggerEl, {
                trigger: 'focus', // Show on focus
                html: true
            });
        });

        // Add fade-in animation to cards (optional, depends on CSS)
        document.querySelectorAll('.card').forEach((card, index) => {
            card.classList.add('fade-in');
            card.style.animationDelay = `${index * 0.05}s`;
        });

        // Handle collapse toggle icons
        document.querySelectorAll('[data-bs-toggle="collapse"]').forEach(button => {
            button.addEventListener('click', function() {
                const icon = this.querySelector('i.fas');
                if (icon) {
                    // Toggle chevron direction based on collapse state
                    const targetId = this.getAttribute('data-bs-target');
                    const targetElement = document.querySelector(targetId);
                    if (targetElement && targetElement.classList.contains('show')) {
                         icon.classList.replace('fa-chevron-up', 'fa-chevron-down');
                    } else {
                         icon.classList.replace('fa-chevron-down', 'fa-chevron-up');
                    }
                }
            });
        });
    }


    // --- Private Chart Enhancement Functions (from chart-enhancements.js) ---

    function setupChartEventListeners() {
        // Chart type toggle button (assuming an element with ID 'chart-type-toggle')
        const chartTypeToggle = document.getElementById('chart-type-toggle');
        if (chartTypeToggle) {
            chartTypeToggle.addEventListener('click', function() {
                const currentType = getPreference('chartType', DEFAULT_SETTINGS.chartType);
                const newType = currentType === 'candlestick' ? 'line' : 'candlestick';
                const icon = this.querySelector('i');

                if (icon) {
                    // Toggle icon based on new chart type
                    if (newType === 'line') {
                        icon.classList.replace('fa-chart-line', 'fa-chart-bar'); // Assuming fa-chart-bar for candlestick
                    } else {
                        icon.classList.replace('fa-chart-bar', 'fa-chart-line'); // Assuming fa-chart-line for line
                    }
                }

                savePreference('chartType', newType);
                updateChartType(newType);
                showNotification(`Chart type changed to ${newType}`, 'info');
            });
        }

        // Indicators toggle button (assuming an element with ID 'toggle-indicators')
        const toggleIndicators = document.getElementById('toggle-indicators');
        if (toggleIndicators) {
            toggleIndicators.addEventListener('click', function() {
                const currentValue = getPreference('indicators.ema', true); // Assuming EMA toggle controls all indicators
                savePreference('indicators.ema', !currentValue);
                updateIndicatorsVisibility();
                showNotification(`Indicators ${!currentValue ? 'shown' : 'hidden'}`, 'info');
            });
        }

        // Reset zoom button (assuming an element with ID 'reset-zoom')
        const resetZoom = document.getElementById('reset-zoom');
        if (resetZoom) {
            resetZoom.addEventListener('click', function() {
                // Reset zoom for all managed charts
                Object.values(_state.charts).forEach(chart => {
                    if (chart && chart.resetZoom) {
                        chart.resetZoom();
                    }
                });
                showNotification('Chart zoom reset', 'info');
            });
        }

        // Chart settings button (assuming an element with ID 'chart-settings' and a modal with ID 'chart-settings-modal')
        const chartSettingsButton = document.getElementById('chart-settings');
        if (chartSettingsButton) {
            chartSettingsButton.addEventListener('click', function() {
                if (typeof bootstrap !== 'undefined') {
                    const modalElement = document.getElementById('chart-settings-modal');
                    if (modalElement) {
                         // Apply current settings to the form before showing the modal
                        applySettingsToSettingsForm();
                        const modal = new bootstrap.Modal(modalElement);
                        modal.show();
                    } else {
                        console.warn('Chart settings modal not found.');
                    }
                } else {
                    console.warn('Bootstrap not available for modal.');
                }
            });
        }

        // Save chart settings button inside the modal (assuming an element with ID 'save-chart-settings')
        const saveChartSettingsButton = document.getElementById('save-chart-settings');
        if (saveChartSettingsButton) {
            saveChartSettingsButton.addEventListener('click', function() {
                saveSettingsFromForm();
                if (typeof bootstrap !== 'undefined') {
                    const modalElement = document.getElementById('chart-settings-modal');
                     if (modalElement) {
                        const modal = bootstrap.Modal.getInstance(modalElement);
                        if (modal) modal.hide();
                     }
                }
                showNotification('Chart settings saved', 'success');
            });
        }

        // Reset chart settings button inside the modal (assuming an element with ID 'reset-chart-settings')
        const resetChartSettingsButton = document.getElementById('reset-chart-settings');
        if (resetChartSettingsButton) {
            resetChartSettingsButton.addEventListener('click', function() {
                confirmAction('Are you sure you want to reset chart settings to defaults?', function() {
                    resetToDefaults();
                    applySettingsToUI(); // Apply defaults to UI elements
                    updateChartType(getPreference('chartType', DEFAULT_SETTINGS.chartType)); // Update chart type visually
                    updateIndicatorsVisibility(); // Update indicator visibility visually
                    if (typeof bootstrap !== 'undefined') {
                        const modalElement = document.getElementById('chart-settings-modal');
                         if (modalElement) {
                            const modal = bootstrap.Modal.getInstance(modalElement);
                            if (modal) modal.hide();
                         }
                    }
                    showNotification('Chart settings reset to defaults', 'info');
                });
            });
        }

        // Timeframe buttons (already handled in setupTimeframeButtons, but ensure settings are saved)
        // This part might be redundant if setupTimeframeButtons is called after init
    }

    /**
     * Apply current settings to chart settings form inputs
     */
    function applySettingsToSettingsForm() {
        const settings = _currentSettings;

        // Update chart type radio buttons
        const chartTypeCandlestick = document.getElementById('chart-type-candlestick');
        const chartTypeLine = document.getElementById('chart-type-line');
        if (chartTypeCandlestick) {
            chartTypeCandlestick.checked = settings.chartType === 'candlestick';
        }
        if (chartTypeLine) {
            chartTypeLine.checked = settings.chartType === 'line';
        }

        // Update indicator checkboxes
        const showEma = document.getElementById('show-ema');
        if (showEma) {
            showEma.checked = settings.indicators.ema;
        }
        const showVolume = document.getElementById('show-volume');
        if (showVolume) {
            showVolume.checked = settings.indicators.volume;
        }

        // Update default timeframe select
        const defaultTimeframeSelect = document.getElementById('default-timeframe');
        if (defaultTimeframeSelect) {
            defaultTimeframeSelect.value = settings.timeframe;
        }
    }


    /**
     * Apply chart settings to UI elements (buttons, toggles, etc.)
     */
    function applySettingsToUI() {
        const settings = _currentSettings;

        // Update timeframe buttons active state
        document.querySelectorAll('.timeframe-btn').forEach(button => {
            button.classList.remove('active');
        });
        const activeTimeframeBtn = document.getElementById(`tf-${settings.timeframe}`);
        if (activeTimeframeBtn) {
            activeTimeframeBtn.classList.add('active');
        }

        // Update chart type toggle button icon
        const chartTypeToggle = document.getElementById('chart-type-toggle');
        if (chartTypeToggle) {
            const icon = chartTypeToggle.querySelector('i');
            if (icon) {
                if (settings.chartType === 'line') {
                    icon.classList.replace('fa-chart-line', 'fa-chart-bar');
                } else {
                    icon.classList.replace('fa-chart-bar', 'fa-chart-line');
                }
            }
        }

        // Update indicator toggle button state (if applicable, e.g., a single toggle for all)
        // This might need adjustment based on how indicators are toggled in the UI
        const toggleIndicatorsButton = document.getElementById('toggle-indicators');
        if (toggleIndicatorsButton) {
             // Example: if the button text/icon changes based on state
             const icon = toggleIndicatorsButton.querySelector('i');
             if (icon) {
                 if (settings.indicators.ema) { // Assuming EMA state represents overall indicator visibility
                     icon.classList.replace('fa-eye-slash', 'fa-eye');
                 } else {
                     icon.classList.replace('fa-eye', 'fa-eye-slash');
                 }
             }
        }

        // Apply theme settings (if any UI elements change based on theme)
        // This would typically involve adding/removing CSS classes on the body or a container
        const body = document.body;
        if (body) {
            if (settings.theme === 'dark') {
                body.classList.add('dark-theme');
                body.classList.remove('light-theme');
            } else {
                body.classList.add('light-theme');
                body.classList.remove('dark-theme');
            }
        }
    }


    /**
     * Save settings from chart settings form inputs to localStorage and apply
     */
    function saveSettingsFromForm() {
        const chartTypeInput = document.querySelector('input[name="chartType"]:checked');
        const chartType = chartTypeInput ? chartTypeInput.value : getPreference('chartType', DEFAULT_SETTINGS.chartType);

        const showEmaCheckbox = document.getElementById('show-ema');
        const showEma = showEmaCheckbox ? showEmaCheckbox.checked : getPreference('indicators.ema', true);

        const showVolumeCheckbox = document.getElementById('show-volume');
        const showVolume = showVolumeCheckbox ? showVolumeCheckbox.checked : getPreference('indicators.volume', true);

        const defaultTimeframeSelect = document.getElementById('default-timeframe');
        const defaultTimeframe = defaultTimeframeSelect ? defaultTimeframeSelect.value : getPreference('timeframe', DEFAULT_SETTINGS.timeframe);

        // Assuming a theme selector exists in the form
        const themeSelect = document.getElementById('ui-theme');
        const theme = themeSelect ? themeSelect.value : getPreference('theme', DEFAULT_SETTINGS.theme);


        savePreference('chartType', chartType);
        savePreference('indicators.ema', showEma);
        savePreference('indicators.volume', showVolume);
        savePreference('timeframe', defaultTimeframe);
        savePreference('theme', theme);


        // Apply the saved settings
        applySettingsToUI();
        updateChartType(chartType);
        updateIndicatorsVisibility();
        applySettingsToCharts(); // Apply theme and other chart-specific settings
    }

    /**
     * Update chart type (candlestick/line) for the price chart
     * @param {string} chartType - Chart type to set ('candlestick' or 'line')
     */
    function updateChartType(chartType) {

        if (_state.charts.price) {
            // Destroy the existing chart instance
            _state.charts.price.destroy();
            _state.charts.price = null; // Clear the reference

            // Re-create the chart with the new type
            const chartCanvas = document.getElementById('price-chart');
            if (chartCanvas && typeof Chart !== 'undefined' && typeof DataModule !== 'undefined' && typeof DataModule.getState === 'function') {
                 const ctx = chartCanvas.getContext('2d');
                 const currentState = DataModule.getState();
                 // Re-fetch or use cached market data to redraw
                 // For simplicity here, we'll assume DataModule has the last fetched market data accessible
                 // A better approach would be to trigger a data fetch or have DataModule provide the data
                 console.warn('Redrawing price chart with new type. DataModule needs to provide market data.');
                 // Placeholder: In a real scenario, you'd get the market data here and pass it to DataModule.updatePriceChart
                 // DataModule.updatePriceChart(lastFetchedMarketData);
                 // For now, we'll just log and the next data fetch will update it correctly.
            } else {
                 console.error('Could not redraw price chart: dependencies missing or canvas not found.');
            }
        } else {
            console.warn('Price chart instance not available to update type.');
        }
    }

    /**
     * Update indicator visibility on the indicators chart and volume chart display
     */
    function updateIndicatorsVisibility() {
        const showEma = getPreference('indicators.ema', true);
        const showVolume = getPreference('indicators.volume', true);

        // Update visibility on the indicators chart
        if (_state.charts.indicators) {
            _state.charts.indicators.data.datasets.forEach(dataset => {
                // Assuming dataset labels contain 'EMA' or 'RSI'
                if (dataset.label && (dataset.label.includes('EMA') || dataset.label.includes('RSI'))) {
                    dataset.hidden = !showEma; // Toggle visibility based on showEma
                }
            });
            _state.charts.indicators.update();
        } else {
             console.warn('Indicators chart instance not available to update visibility.');
        }


        // Toggle visibility of the volume chart container/tab
        const volumeChartContainer = document.getElementById('volume-chart-container'); // Assuming a container element
        const volumeTab = document.getElementById('volume-tab'); // Assuming a tab element
        if (volumeChartContainer) {
            volumeChartContainer.style.display = showVolume ? 'block' : 'none';
        }
        if (volumeTab) {
             volumeTab.style.display = showVolume ? 'block' : 'none';
        }
         if (!volumeChartContainer && !volumeTab) {
             console.warn('Volume chart container or tab not found to toggle visibility.');
         }
    }


    /**
     * Set chart instances for synchronization and settings application
     * Called by DataModule after charts are created/updated
     * @param {Object} priceChart - Price chart instance
     * @param {Object} indicatorsChart - Indicators chart instance
     * @param {Object} volumeChart - Volume chart instance
     * @param {Object} equityChart - Equity chart instance
     */
    function setChartInstances(priceChart, indicatorsChart, volumeChart, equityChart) {
        _state.charts.price = priceChart;
        _state.charts.indicators = indicatorsChart;
        _state.charts.volume = volumeChart;
        _state.charts.equity = equityChart;

        // Set up chart synchronization if enabled
        if (_state.syncEnabled) {
            setupChartSync();
        }

        // Apply current settings to the newly set chart instances
        applySettingsToCharts();
    }

    /**
     * Set up chart synchronization for zoom and pan
     */
    function setupChartSync() {
        const chartsToSync = [_state.charts.price, _state.charts.indicators, _state.charts.volume].filter(chart => chart);

        chartsToSync.forEach(chart => {
            if (!chart || !chart.options || !chart.options.plugins || !chart.options.plugins.zoom) {
                 console.warn('Chart or zoom plugin not available for sync setup.');
                 return;
            }

            // Remove existing zoom/pan event handlers to prevent duplicates
            if (chart.options.plugins.zoom.zoom.onZoom) {
                 delete chart.options.plugins.zoom.zoom.onZoom;
            }
             if (chart.options.plugins.zoom.pan.onPan) {
                 delete chart.options.plugins.zoom.pan.onPan;
             }


            // Add new zoom event handlers
            chart.options.plugins.zoom.zoom.onZoom = (chart) => {
                syncChartZoom(chart);
            };

            chart.options.plugins.zoom.pan.onPan = (chart) => {
                syncChartZoom(chart);
            };
        });

    }

    /**
     * Synchronize chart zoom across specified charts
     * @param {Object} sourceChart - Source chart to sync from
     */
    function syncChartZoom(sourceChart) {
        if (!_state.syncEnabled || !sourceChart || !sourceChart.options || !sourceChart.options.scales || !sourceChart.options.scales.x) {
             console.warn('Chart sync disabled or source chart invalid.');
             return;
        }

        const sourceXScale = sourceChart.options.scales.x;
        const targetCharts = [_state.charts.price, _state.charts.indicators, _state.charts.volume]
            .filter(chart => chart && chart !== sourceChart); // Exclude the source chart

        targetCharts.forEach(chart => {
            if (!chart || !chart.options || !chart.options.scales || !chart.options.scales.x) {
                 console.warn('Target chart invalid for sync.');
                 return;
            }

            // Sync min and max values of the x-axis
            if (sourceXScale.min !== undefined && sourceXScale.max !== undefined) {
                chart.options.scales.x.min = sourceXScale.min;
                chart.options.scales.x.max = sourceXScale.max;
                chart.update('none'); // 'none' prevents animation
            }
        });
    }


    // --- Public API ---

    return {
        /**
         * Initialize the UI module
         * Loads settings, sets up event listeners, and applies initial settings
         */
        init: function() {
            _loadSettings(); // Load settings from localStorage
            initializeUIComponents(); // Initialize general Bootstrap components etc.
            setupRefreshButtons();
            setupChartToolbar();
            setupTimeframeButtons();
            setupExportButtons();
            setupLogControls();
            setupChartEventListeners(); // Setup listeners for chart-specific controls
            applySettingsToUI(); // Apply loaded settings to UI elements
            // Note: Charts are initialized by DataModule, which will then call setChartInstances

        },

        // Expose utility functions
        formatNumber: formatNumber,
        formatCurrency: formatCurrency,
        formatPercentage: formatPercentage,
        formatDate: formatDate,
        formatPrice: formatPrice,
        showNotification: showNotification,
        formatTradeSide: formatTradeSide,
        formatPnL: formatPnL,
        formatColorPercentage: formatColorPercentage,
        confirmAction: confirmAction,
        debounce: debounce,
        throttle: throttle,
        getCookie: getCookie,
        setCookie: setCookie,
        addLogEntry: addLogEntry, // Expose log function

        // Expose settings functions
        get settings() {
            return { ..._currentSettings };
        },
        savePreference: savePreference,
        getPreference: getPreference,
        resetToDefaults: resetToDefaults,
        applySettingsToCharts: applySettingsToCharts, // Expose for DataModule to call

        // Expose chart enhancement functions needed by DataModule
        setChartInstances: setChartInstances,
        updateChartType: updateChartType, // Expose for DataModule to call after data load
        updateIndicatorsVisibility: updateIndicatorsVisibility, // Expose for DataModule to call after data load

        // Expose UI update functions called by DataModule
        updateSignal: updateSignal,
        updateBotStatus: updateBotStatus,

        // Expose state if needed (read-only)
        get state() {
            return { ..._state };
        }
    };
})();

// Initialize the UI module when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    UI.init();
});

// Expose UI to global scope (optional, depending on module system)
window.UI = UI;

// Make showToast available globally for convenience (calls UI.showNotification)
window.showToast = function(message, type = 'info', duration = 5000) {
    UI.showNotification(message, type);
};
