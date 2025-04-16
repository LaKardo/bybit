/**
 * API Module - Handles all API communication with the trading bot backend
 * Provides methods for data formatting and API requests
 */
const API = (function() {
    'use strict';

    // Private variables and functions
    const DEFAULT_ENDPOINTS = {
        status: '/api/status',
        balance: '/api/balance',
        positions: '/api/positions',
        marketData: '/api/market_data',
        performance: '/api/performance',
        startBot: '/api/start_bot',
        stopBot: '/api/stop_bot',
        closePosition: '/api/close_position',
        exportData: '/api/export_data',
        health: '/api/health',
        healthHistory: '/api/health/history',
        performance: '/api/health/performance',
        updateSettings: '/api/update_settings',
        logs: '/api/logs'
    };

    /**
     * Process API error and call error callback if provided
     * @param {Error} error - The error object
     * @param {Function} callback - Optional callback function
     * @private
     */
    function _handleApiError(error, callback) {
        console.error('API Error:', error);
        if (typeof callback === 'function') {
            callback({
                status: 'ERROR',
                message: error.message || 'Unknown error'
            });
        }
    }

    /**
     * Make an API request with error handling
     * @param {string} url - API endpoint URL
     * @param {Object} options - Fetch options
     * @param {Function} callback - Callback function
     * @private
     */
    function _apiRequest(url, options = {}, callback) {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
                // Add CSRF token header if needed, e.g., 'X-CSRFToken': Utils.getCookie('csrftoken')
            }
        };

        const fetchOptions = { ...defaultOptions, ...options };

        // Add CSRF token for POST/PUT/DELETE requests if using Django/Flask CSRF protection
        if (['POST', 'PUT', 'DELETE'].includes(fetchOptions.method.toUpperCase())) {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || Utils?.getCookie('csrftoken');
            if (csrfToken) {
                fetchOptions.headers['X-CSRFToken'] = csrfToken;
            }
        }


        fetch(url, fetchOptions)
            .then(response => {
                if (!response.ok) {
                    // Try to get error message from response body
                    return response.json().then(errData => {
                         throw new Error(`HTTP error ${response.status}: ${errData.message || response.statusText}`);
                    }).catch(() => {
                        // Fallback if response body is not JSON or empty
                        throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (typeof callback === 'function') {
                    callback(data);
                }
            })
            .catch(error => _handleApiError(error, callback));
    }

    // Public API
    return {
        config: {
            baseUrl: '',
            endpoints: { ...DEFAULT_ENDPOINTS }
        },

        /**
         * Initialize the API module
         * @param {Object} options - Configuration options
         * @returns {Object} The API module instance
         */
        init: function(options) {
            if (options) {
                this.config = {
                    ...this.config,
                    ...options,
                    endpoints: { ...this.config.endpoints, ...(options.endpoints || {}) }
                };
            }
            // console.log('API module initialized'); // Removed as per original intent
            return this;
        },

        /**
         * Format balance data from Bybit API v5
         * @param {Object} balance - Balance data from API
         * @returns {Object} Formatted balance object
         */
        formatBalanceV5: function(balance) {
            if (!balance) return {};
            // Use Utils for formatting if available, otherwise fallback
            const formatFn = typeof Utils !== 'undefined' ? Utils.formatCurrency : (num, dec = 4) => parseFloat(num || 0).toFixed(dec);
            return {
                availableBalance: formatFn(balance.available_balance),
                walletBalance: formatFn(balance.wallet_balance),
                unrealizedPnl: formatFn(balance.unrealized_pnl),
                equity: formatFn(balance.equity),
                usedMargin: formatFn(balance.used_margin),
                usedMarginRate: parseFloat(balance.used_margin_rate || 0).toFixed(2),
                marginRatio: parseFloat(balance.margin_ratio || 0).toFixed(2),
                freeMargin: formatFn(balance.free_margin),
                coin: balance.coin || 'USDT'
            };
        },

        /**
         * Format position data from Bybit API v5
         * @param {Object} position - Position data from API
         * @returns {Object} Formatted position object
         */
        formatPositionV5: function(position) {
            if (!position) return {};

            const unrealizedPnl = parseFloat(position.unrealized_pnl || 0);
            const positionValue = parseFloat(position.position_value || 0);
            const entryPrice = parseFloat(position.entry_price || 0);
            const unrealizedPnlPercent = entryPrice !== 0 && positionValue !== 0 ?
                (unrealizedPnl / (parseFloat(position.size || 0) * entryPrice) * 100).toFixed(2) : '0.00'; // Correct PnL % calculation

            // Use Utils for formatting if available
            const formatCurrencyFn = typeof Utils !== 'undefined' ? Utils.formatCurrency : (num, dec = 2) => parseFloat(num || 0).toFixed(dec);
            const formatPriceFn = typeof Utils !== 'undefined' ? Utils.formatPrice : (num, sym) => parseFloat(num || 0).toFixed(2); // Basic fallback
            const formatDateFn = typeof Utils !== 'undefined' ? Utils.formatDate : (dateStr) => dateStr ? new Date(dateStr).toLocaleString() : '';

            return {
                symbol: position.symbol || '',
                side: position.side || '',
                size: parseFloat(position.size || 0).toFixed(4), // Keep higher precision for size
                positionValue: formatCurrencyFn(position.position_value),
                entryPrice: formatPriceFn(position.entry_price, position.symbol),
                markPrice: formatPriceFn(position.mark_price, position.symbol),
                unrealizedPnl: formatCurrencyFn(unrealizedPnl, 4), // Higher precision for PnL
                unrealizedPnlPercent: unrealizedPnlPercent,
                leverage: parseFloat(position.leverage || 0).toFixed(0),
                liqPrice: formatPriceFn(position.liq_price, position.symbol),
                takeProfit: formatPriceFn(position.take_profit, position.symbol),
                stopLoss: formatPriceFn(position.stop_loss, position.symbol),
                trailingStop: formatPriceFn(position.trailing_stop, position.symbol),
                createdTime: formatDateFn(position.created_time),
                updatedTime: formatDateFn(position.updated_time)
            };
        },

        /**
         * Format ticker data from Bybit API v5
         * @param {Object} ticker - Ticker data from API
         * @returns {Object} Formatted ticker object
         */
        formatTickerV5: function(ticker) {
            if (!ticker) return {};
            // Use Utils for formatting if available
            const formatNumberFn = typeof Utils !== 'undefined' ? Utils.formatNumber : (num, dec = 2) => parseFloat(num || 0).toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
            const formatPriceFn = typeof Utils !== 'undefined' ? Utils.formatPrice : (num, sym) => parseFloat(num || 0).toFixed(2);
            const formatDateFn = typeof Utils !== 'undefined' ? Utils.formatDate : (dateStr) => dateStr ? new Date(dateStr).toLocaleString() : '';

            return {
                symbol: ticker.symbol || '',
                lastPrice: formatPriceFn(ticker.lastPrice, ticker.symbol),
                markPrice: formatPriceFn(ticker.markPrice, ticker.symbol),
                indexPrice: formatPriceFn(ticker.indexPrice, ticker.symbol),
                highPrice24h: formatPriceFn(ticker.highPrice24h, ticker.symbol),
                lowPrice24h: formatPriceFn(ticker.lowPrice24h, ticker.symbol),
                volume24h: formatNumberFn(ticker.volume24h, 2),
                turnover24h: formatNumberFn(ticker.turnover24h, 2),
                price24hPcnt: (parseFloat(ticker.price24hPcnt || 0) * 100).toFixed(2) + '%',
                openInterest: formatNumberFn(ticker.openInterest, 2),
                fundingRate: (parseFloat(ticker.fundingRate || 0) * 100).toFixed(4) + '%',
                nextFundingTime: formatDateFn(ticker.nextFundingTime)
            };
        },

        /**
         * Format market data for chart display (OHLC and Volume only)
         * Indicator calculation moved to DataModule
         * @param {Array} data - Market data from API
         * @returns {Object} Formatted data for chart display { ohlc: [], volume: [] }
         */
        formatMarketDataForChartV5: function(data) {
            if (!data || !data.length) {
                console.warn('No data to format for chart');
                return { ohlc: [], volume: [] };
            }

            try {
                const ohlc = [];
                const volume = [];

                data.forEach(item => {
                    const timestamp = new Date(item.timestamp).getTime();
                    const open = parseFloat(item.open);
                    const high = parseFloat(item.high);
                    const low = parseFloat(item.low);
                    const close = parseFloat(item.close);
                    const vol = parseFloat(item.volume);

                    if (!isNaN(timestamp) && !isNaN(open) && !isNaN(high) && !isNaN(low) && !isNaN(close)) {
                        ohlc.push({
                            x: timestamp,
                            o: open,
                            h: high,
                            l: low,
                            c: close
                        });

                        if (!isNaN(vol)) {
                            volume.push({
                                x: timestamp,
                                y: vol
                            });
                        } else {
                             volume.push({ x: timestamp, y: 0 }); // Add placeholder if volume is NaN
                        }
                    } else {
                        console.warn('Invalid market data point:', item);
                    }
                });

                return { ohlc, volume };
            } catch (error) {
                console.error('Error formatting market data:', error);
                return { ohlc: [], volume: [] };
            }
        },

        /**
         * Create HTML for position card
         * @param {Object} position - Formatted position data
         * @returns {string} HTML for position card
         */
        createPositionCardHtml: function(position) {
            // Use Utils for formatting if available
            const formatTradeSideFn = typeof Utils !== 'undefined' ? Utils.formatTradeSide : (side) => side;
            const formatPnLFn = typeof Utils !== 'undefined' ? Utils.formatPnL : (pnl) => pnl;
            const formatColorPercentageFn = typeof Utils !== 'undefined' ? Utils.formatColorPercentage : (perc) => `${perc}%`;

            const pnlValue = parseFloat(position.unrealizedPnl);
            const pnlPercentValue = parseFloat(position.unrealizedPnlPercent);

            return `
            <div class="col-lg-6 col-xl-4 mb-3">
                <div class="card position-card h-100 shadow-sm border-0 ${position.side === 'Buy' ? 'long' : 'short'}">
                    <div class="card-header bg-${position.side === 'Buy' ? 'success' : 'danger'}-soft text-${position.side === 'Buy' ? 'success' : 'danger'} d-flex justify-content-between align-items-center">
                        <h6 class="mb-0 fw-bold">${position.symbol}</h6>
                        ${formatTradeSideFn(position.side)}
                    </div>
                    <div class="card-body p-3">
                        <div class="row g-2">
                            <div class="col-6 small">
                                <p class="mb-1 text-muted">Size:</p>
                                <p class="mb-1 fw-medium">${position.size}</p>
                                <p class="mb-1 text-muted">Entry Price:</p>
                                <p class="mb-1 fw-medium">${position.entryPrice}</p>
                                <p class="mb-1 text-muted">Mark Price:</p>
                                <p class="mb-1 fw-medium">${position.markPrice}</p>
                            </div>
                            <div class="col-6 small">
                                <p class="mb-1 text-muted">PnL:</p>
                                <p class="mb-1 fw-medium">${formatPnLFn(pnlValue)} (${formatColorPercentageFn(pnlPercentValue)})</p>
                                <p class="mb-1 text-muted">Liq. Price:</p>
                                <p class="mb-1 fw-medium">${position.liqPrice !== '0.00' ? position.liqPrice : 'N/A'}</p>
                                <p class="mb-1 text-muted">Leverage:</p>
                                <p class="mb-1 fw-medium">${position.leverage}x</p>
                            </div>
                            <div class="col-12 small">
                                <p class="mb-1 text-muted">Take Profit:</p>
                                <p class="mb-1 fw-medium">${position.takeProfit !== '0.00' ? position.takeProfit : 'None'}</p>
                                <p class="mb-1 text-muted">Stop Loss:</p>
                                <p class="mb-1 fw-medium">${position.stopLoss !== '0.00' ? position.stopLoss : 'None'}</p>
                            </div>
                        </div>
                    </div>
                    <div class="card-footer bg-light border-top-0 p-2 text-end">
                        <button class="btn btn-xs btn-danger close-position-btn" data-symbol="${position.symbol}" title="Close ${position.symbol} position">
                            <i class="fas fa-times me-1"></i>Close
                        </button>
                    </div>
                </div>
            </div>
            `;
        },

        // --- API Request Methods ---

        /**
         * Get bot status
         * @param {Function} callback - Callback function
         */
        getStatus: function(callback) {
            _apiRequest(this.config.baseUrl + this.config.endpoints.status, {}, callback);
        },

        /**
         * Get account balance
         * @param {Function} callback - Callback function
         */
        getBalance: function(callback) {
            _apiRequest(this.config.baseUrl + this.config.endpoints.balance, {}, callback);
        },

        /**
         * Get open positions
         * @param {Function} callback - Callback function
         */
        getPositions: function(callback) {
            _apiRequest(this.config.baseUrl + this.config.endpoints.positions, {}, callback);
        },

        /**
         * Get market data
         * @param {string} symbol - Trading symbol
         * @param {string} timeframe - Timeframe interval
         * @param {Function} callback - Callback function
         */
        getMarketData: function(symbol, timeframe, callback) {
            _apiRequest(`${this.config.baseUrl}${this.config.endpoints.marketData}?symbol=${symbol}&interval=${timeframe}`, {}, callback);
        },

        /**
         * Get performance data
         * @param {Function} callback - Callback function
         */
        getPerformanceData: function(callback) {
            _apiRequest(this.config.baseUrl + this.config.endpoints.performance, {}, callback);
        },

        /**
         * Start the trading bot
         * @param {Function} callback - Callback function
         */
        startBot: function(callback) {
            _apiRequest(this.config.baseUrl + this.config.endpoints.startBot, { method: 'POST' }, callback);
        },

        /**
         * Stop the trading bot
         * @param {Function} callback - Callback function
         */
        stopBot: function(callback) {
            _apiRequest(this.config.baseUrl + this.config.endpoints.stopBot, { method: 'POST' }, callback);
        },

        /**
         * Close a position
         * @param {string} symbol - Trading symbol
         * @param {Function} callback - Callback function
         */
        closePosition: function(symbol, callback) {
            _apiRequest(this.config.baseUrl + this.config.endpoints.closePosition, {
                method: 'POST',
                body: JSON.stringify({ symbol: symbol })
            }, callback);
        },

        /**
         * Export data
         * @param {string} type - Data type to export
         * @param {string} format - Export format
         * @param {Function} callback - Callback function
         */
        exportData: function(type, format, callback) {
            // This might be better handled by directly navigating or using a download library
            // For now, assume backend returns filename/data for frontend download
             _apiRequest(this.config.baseUrl + this.config.endpoints.exportData, {
                 method: 'POST',
                 body: JSON.stringify({ type: type, format: format })
             }, callback);
        },

        /**
         * Get health check data
         * @param {Function} callback - Callback function
         */
        getHealth: function(callback) {
            _apiRequest(this.config.baseUrl + this.config.endpoints.health, {}, callback);
        },

        /**
         * Get health check history
         * @param {number} hours - Number of hours of history to retrieve
         * @param {Function} callback - Callback function
         */
        getHealthHistory: function(hours, callback) {
            _apiRequest(`${this.config.baseUrl}${this.config.endpoints.healthHistory}?hours=${hours}`, {}, callback);
        },

        /**
         * Get performance metrics (potentially redundant if included in tradeHistory)
         * @param {Function} callback - Callback function
         */
        getPerformanceMetrics: function(callback) {
            _apiRequest(this.config.baseUrl + this.config.endpoints.performance, {}, callback);
        },

        /**
         * Update bot settings
         * @param {Object} settings - New settings
         * @param {Function} callback - Callback function
         */
        updateSettings: function(settings, callback) {
            _apiRequest(this.config.baseUrl + this.config.endpoints.updateSettings, {
                method: 'POST',
                body: JSON.stringify(settings)
            }, callback);
        },

        /**
         * Get logs
         * @param {number} limit - Maximum number of logs to retrieve
         * @param {Function} callback - Callback function
         */
        getLogs: function(limit, callback) {
            _apiRequest(`${this.config.baseUrl}${this.config.endpoints.logs}?limit=${limit || 100}`, {}, callback);
        }
    };
})();

// Expose API to global scope (optional, depending on module system)
window.API = API;
