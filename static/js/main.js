/**
 * Main JavaScript file for the trading bot web interface
 * Initializes all modules and sets up global event handlers
 */
document.addEventListener('DOMContentLoaded', function() {
    'use strict';

    // Initialize modules
    // UI module includes utilities, settings, and UI enhancements
    if (typeof UI !== 'undefined') {
        UI.init();
    } else {
        console.error('UI module not found!');
    }

    // Data module handles data fetching and processing
    if (typeof DataModule !== 'undefined') {
        DataModule.init({
            defaultSymbol: UI.getPreference('symbol', 'BTCUSDT'), // Get default symbol from UI settings
            defaultTimeframe: UI.getPreference('timeframe', '15'), // Get default timeframe from UI settings
            autoRefreshInterval: 30000 // 30 seconds
        });
        DataModule.fetchData();

        if (UI.getPreference('autoRefresh', true)) {
            DataModule.enableAutoRefresh();
        }
    } else {
        console.error('DataModule not found!');
    }

    // API module handles backend communication
    if (typeof API !== 'undefined') {
        API.init(); // Assuming API module doesn't need specific options from settings for now
    } else {
        console.error('API module not found!');
    }


    // Set up global event handlers (moved from old main.js)
    // These handlers now call functions within the consolidated modules

    const startBotBtn = document.getElementById('start-bot');
    if (startBotBtn) {
        startBotBtn.addEventListener('click', function() {
            if (typeof API !== 'undefined' && API.startBot) {
                // Assuming showLoading is a global function or part of UI
                if (typeof showLoading === 'function') showLoading();
                API.startBot(function(response) {
                    if (typeof hideLoading === 'function') hideLoading();
                    if (response.status === 'OK') {
                        if (typeof showToast === 'function') showToast('Bot started successfully', 'success');
                        if (typeof UI !== 'undefined' && UI.updateBotStatus) {
                            UI.updateBotStatus('running');
                        }
                    } else {
                        if (typeof showToast === 'function') showToast(`Error starting bot: ${response.message}`, 'error');
                    }
                });
            } else {
                console.error('API module or startBot function not available.');
                 if (typeof showToast === 'function') showToast('Error: Bot control not available.', 'error');
            }
        });
    }

    const stopBotBtn = document.getElementById('stop-bot');
    if (stopBotBtn) {
        stopBotBtn.addEventListener('click', function() {
            if (typeof API !== 'undefined' && API.stopBot) {
                if (typeof UI !== 'undefined' && UI.confirmAction) {
                    UI.confirmAction('Are you sure you want to stop the bot?', function() {
                        if (typeof showLoading === 'function') showLoading();
                        API.stopBot(function(response) {
                            if (typeof hideLoading === 'function') hideLoading();
                            if (response.status === 'OK') {
                                if (typeof showToast === 'function') showToast('Bot stopped successfully', 'success');
                                if (typeof UI !== 'undefined' && UI.updateBotStatus) {
                                    UI.updateBotStatus('stopped');
                                }
                            } else {
                                if (typeof showToast === 'function') showToast(`Error stopping bot: ${response.message}`, 'error');
                            }
                        });
                    });
                } else {
                     // Fallback to simple confirm if UI.confirmAction is not available
                     if (confirm('Are you sure you want to stop the bot?')) {
                         if (typeof showLoading === 'function') showLoading();
                         API.stopBot(function(response) {
                             if (typeof hideLoading === 'function') hideLoading();
                             if (response.status === 'OK') {
                                 if (typeof showToast === 'function') showToast('Bot stopped successfully', 'success');
                                 if (typeof UI !== 'undefined' && UI.updateBotStatus) {
                                     UI.updateBotStatus('stopped');
                                 }
                             } else {
                                 if (typeof showToast === 'function') showToast(`Error stopping bot: ${response.message}`, 'error');
                             }
                         });
                     }
                }
            } else {
                console.error('API module or stopBot function not available.');
                 if (typeof showToast === 'function') showToast('Error: Bot control not available.', 'error');
            }
        });
    }

    const refreshAllBtn = document.getElementById('refresh-all');
    if (refreshAllBtn) {
        refreshAllBtn.addEventListener('click', () => {
            // The actual refresh logic is likely handled within UI.setupRefreshButtons
            // or triggered by a custom event if needed.
            console.log('"Refresh All" button clicked. Logic likely handled elsewhere (e.g., UI module).');
        });
    }

    const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
    if (autoRefreshToggle) {
        // Set initial state based on UI settings
        autoRefreshToggle.checked = UI.getPreference('autoRefresh', true);

        autoRefreshToggle.addEventListener('change', function() {
            if (typeof DataModule !== 'undefined' && typeof UI !== 'undefined') {
                const isChecked = this.checked;
                if (isChecked) {
                    DataModule.enableAutoRefresh();
                    UI.savePreference('autoRefresh', true);
                    UI.showNotification('Auto-refresh enabled', 'info');
                } else {
                    DataModule.disableAutoRefresh();
                    UI.savePreference('autoRefresh', false);
                    UI.showNotification('Auto-refresh disabled', 'info');
                }
            } else {
                 console.warn('DataModule or UI module not available for auto-refresh toggle.');
            }
        });
    }

});
