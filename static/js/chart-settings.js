/**
 * Chart Settings Module for Bybit Trading Bot
 * Handles saving and loading chart preferences
 */

// Default chart settings
const DEFAULT_CHART_SETTINGS = {
    timeframe: '15',           // Default timeframe (15m)
    chartType: 'candlestick',  // 'candlestick' or 'line'
    indicators: {
        ema: true,             // Show EMAs
        volume: true           // Show volume
    }
};

// Chart settings namespace
const ChartSettings = {
    // Current settings (will be loaded from localStorage or defaults)
    current: JSON.parse(JSON.stringify(DEFAULT_CHART_SETTINGS)),
    
    // Initialize settings
    init: function() {
        this.loadSettings();
        return this.current;
    },
    
    // Save settings to localStorage
    saveSettings: function() {
        try {
            localStorage.setItem('bybit_chart_settings', JSON.stringify(this.current));
            console.log('Chart settings saved');
            return true;
        } catch (error) {
            console.error('Error saving chart settings:', error);
            return false;
        }
    },
    
    // Load settings from localStorage
    loadSettings: function() {
        try {
            const savedSettings = localStorage.getItem('bybit_chart_settings');
            if (savedSettings) {
                const parsed = JSON.parse(savedSettings);
                // Merge saved settings with defaults to ensure all properties exist
                this.current = {...DEFAULT_CHART_SETTINGS, ...parsed};
                console.log('Chart settings loaded from localStorage');
            } else {
                console.log('No saved chart settings found, using defaults');
                this.current = JSON.parse(JSON.stringify(DEFAULT_CHART_SETTINGS));
            }
            return this.current;
        } catch (error) {
            console.error('Error loading chart settings:', error);
            this.current = JSON.parse(JSON.stringify(DEFAULT_CHART_SETTINGS));
            return this.current;
        }
    },
    
    // Update a specific setting
    updateSetting: function(key, value) {
        // Handle nested properties using dot notation (e.g., 'indicators.ema')
        if (key.includes('.')) {
            const parts = key.split('.');
            let obj = this.current;
            for (let i = 0; i < parts.length - 1; i++) {
                if (!obj[parts[i]]) obj[parts[i]] = {};
                obj = obj[parts[i]];
            }
            obj[parts[parts.length - 1]] = value;
        } else {
            this.current[key] = value;
        }
        
        this.saveSettings();
        return this.current;
    },
    
    // Reset settings to defaults
    resetSettings: function() {
        this.current = JSON.parse(JSON.stringify(DEFAULT_CHART_SETTINGS));
        this.saveSettings();
        return this.current;
    }
};
