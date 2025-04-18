/**
 * Chart Enhancements for Bybit Trading Bot
 * Improves chart design and adds settings persistence
 */

// Chart enhancements namespace
const ChartEnhancements = {
    // Chart instances
    charts: {
        price: null,
        indicators: null,
        volume: null
    },
    
    // Initialize chart enhancements
    init: function() {
        // Initialize chart settings
        ChartSettings.init();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Apply saved settings to UI
        this.applySettingsToUI();
        
        console.log('Chart enhancements initialized');
    },
    
    // Set up event listeners for chart controls
    setupEventListeners: function() {
        // Chart type toggle
        const chartTypeToggle = document.getElementById('chart-type-toggle');
        if (chartTypeToggle) {
            chartTypeToggle.addEventListener('click', function() {
                const currentType = ChartSettings.current.chartType;
                const newType = currentType === 'candlestick' ? 'line' : 'candlestick';
                
                // Update icon
                const icon = this.querySelector('i');
                if (icon) {
                    if (newType === 'line') {
                        icon.classList.replace('fa-chart-line', 'fa-chart-bar');
                    } else {
                        icon.classList.replace('fa-chart-bar', 'fa-chart-line');
                    }
                }
                
                // Update setting
                ChartSettings.updateSetting('chartType', newType);
                
                // Update chart
                ChartEnhancements.updateChartType(newType);
                
                // Show notification
                showToast(`Chart type changed to ${newType}`, 'info');
            });
        }
        
        // Toggle indicators
        const toggleIndicators = document.getElementById('toggle-indicators');
        if (toggleIndicators) {
            toggleIndicators.addEventListener('click', function() {
                const currentValue = ChartSettings.current.indicators.ema;
                ChartSettings.updateSetting('indicators.ema', !currentValue);
                
                // Update chart
                ChartEnhancements.updateIndicators();
                
                // Show notification
                showToast(`Indicators ${!currentValue ? 'shown' : 'hidden'}`, 'info');
            });
        }
        
        // Reset zoom
        const resetZoom = document.getElementById('reset-zoom');
        if (resetZoom) {
            resetZoom.addEventListener('click', function() {
                if (ChartEnhancements.charts.price && ChartEnhancements.charts.price.resetZoom) {
                    ChartEnhancements.charts.price.resetZoom();
                    showToast('Chart zoom reset', 'info');
                }
            });
        }
        
        // Chart settings button
        const chartSettings = document.getElementById('chart-settings');
        if (chartSettings) {
            chartSettings.addEventListener('click', function() {
                // Show settings modal
                const modal = new bootstrap.Modal(document.getElementById('chart-settings-modal'));
                modal.show();
            });
        }
        
        // Save chart settings
        const saveChartSettings = document.getElementById('save-chart-settings');
        if (saveChartSettings) {
            saveChartSettings.addEventListener('click', function() {
                ChartEnhancements.saveSettingsFromForm();
                
                // Hide modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('chart-settings-modal'));
                if (modal) {
                    modal.hide();
                }
                
                // Show notification
                showToast('Chart settings saved', 'success');
            });
        }
        
        // Reset chart settings
        const resetChartSettings = document.getElementById('reset-chart-settings');
        if (resetChartSettings) {
            resetChartSettings.addEventListener('click', function() {
                if (confirm('Are you sure you want to reset chart settings to defaults?')) {
                    ChartSettings.resetSettings();
                    ChartEnhancements.applySettingsToUI();
                    
                    // Hide modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('chart-settings-modal'));
                    if (modal) {
                        modal.hide();
                    }
                    
                    // Show notification
                    showToast('Chart settings reset to defaults', 'info');
                }
            });
        }
        
        // Timeframe buttons
        document.querySelectorAll('.timeframe-btn').forEach(button => {
            button.addEventListener('click', function() {
                const timeframe = this.id.split('-')[1];
                ChartSettings.updateSetting('timeframe', timeframe);
            });
        });
    },
    
    // Apply saved settings to UI
    applySettingsToUI: function() {
        const settings = ChartSettings.current;
        
        // Set active timeframe button
        document.querySelectorAll('.timeframe-btn').forEach(button => {
            button.classList.remove('active');
        });
        const activeTimeframeBtn = document.getElementById(`timeframe-${settings.timeframe}`);
        if (activeTimeframeBtn) {
            activeTimeframeBtn.classList.add('active');
        }
        
        // Set chart type icon
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
        
        // Set form values
        const chartTypeCandlestick = document.getElementById('chart-type-candlestick');
        const chartTypeLine = document.getElementById('chart-type-line');
        if (chartTypeCandlestick && chartTypeLine) {
            if (settings.chartType === 'candlestick') {
                chartTypeCandlestick.checked = true;
            } else {
                chartTypeLine.checked = true;
            }
        }
        
        const showEma = document.getElementById('show-ema');
        if (showEma) {
            showEma.checked = settings.indicators.ema;
        }
        
        const showVolume = document.getElementById('show-volume');
        if (showVolume) {
            showVolume.checked = settings.indicators.volume;
        }
        
        const defaultTimeframe = document.getElementById('default-timeframe');
        if (defaultTimeframe) {
            defaultTimeframe.value = settings.timeframe;
        }
    },
    
    // Save settings from form
    saveSettingsFromForm: function() {
        // Get form values
        const chartType = document.querySelector('input[name="chartType"]:checked').value;
        const showEma = document.getElementById('show-ema').checked;
        const showVolume = document.getElementById('show-volume').checked;
        const defaultTimeframe = document.getElementById('default-timeframe').value;
        
        // Update settings
        ChartSettings.updateSetting('chartType', chartType);
        ChartSettings.updateSetting('indicators.ema', showEma);
        ChartSettings.updateSetting('indicators.volume', showVolume);
        ChartSettings.updateSetting('timeframe', defaultTimeframe);
        
        // Apply settings to UI and charts
        this.applySettingsToUI();
        this.updateChartType(chartType);
        this.updateIndicators();
    },
    
    // Update chart type
    updateChartType: function(chartType) {
        // This function would update the chart type
        // The actual implementation depends on how your charts are created
        console.log(`Chart type updated to: ${chartType}`);
        
        // If we have access to the chart instance, we could update it
        if (this.charts.price) {
            // Example of how this might be implemented
            // This is a placeholder and would need to be adapted to your actual chart implementation
            if (chartType === 'line') {
                // Convert to line chart
                this.charts.price.data.datasets.forEach(dataset => {
                    if (dataset.type === 'candlestick') {
                        dataset.type = 'line';
                        dataset.borderColor = 'rgba(13, 110, 253, 1)';
                        dataset.backgroundColor = 'rgba(13, 110, 253, 0.1)';
                        dataset.fill = true;
                    }
                });
            } else {
                // Convert to candlestick chart
                this.charts.price.data.datasets.forEach(dataset => {
                    if (dataset.type === 'line') {
                        dataset.type = 'candlestick';
                        delete dataset.borderColor;
                        delete dataset.backgroundColor;
                        delete dataset.fill;
                    }
                });
            }
            
            this.charts.price.update();
        }
    },
    
    // Update indicators visibility
    updateIndicators: function() {
        const showEma = ChartSettings.current.indicators.ema;
        const showVolume = ChartSettings.current.indicators.volume;
        
        // This function would update the indicators visibility
        // The actual implementation depends on how your charts are created
        console.log(`Indicators updated: EMA=${showEma}, Volume=${showVolume}`);
        
        // If we have access to the chart instances, we could update them
        if (this.charts.price) {
            // Example of how this might be implemented
            // This is a placeholder and would need to be adapted to your actual chart implementation
            this.charts.price.data.datasets.forEach(dataset => {
                if (dataset.label && dataset.label.includes('EMA')) {
                    dataset.hidden = !showEma;
                }
            });
            
            this.charts.price.update();
        }
        
        if (this.charts.volume) {
            // Toggle volume chart visibility
            const volumeTab = document.getElementById('volume-tab');
            if (volumeTab) {
                volumeTab.style.display = showVolume ? 'block' : 'none';
            }
        }
    },
    
    // Store chart instances for later reference
    setChartInstances: function(priceChart, indicatorsChart, volumeChart) {
        this.charts.price = priceChart;
        this.charts.indicators = indicatorsChart;
        this.charts.volume = volumeChart;
    }
};

// Initialize chart enhancements when document is ready
document.addEventListener('DOMContentLoaded', function() {
    ChartEnhancements.init();
});
