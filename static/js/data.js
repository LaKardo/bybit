/**
 * Data Module - Handles data fetching, processing, and chart updates
 * Provides a centralized data management system for the trading bot interface
 */
const DataModule = (function() {
    'use strict';

    // Private variables
    const _config = {
        defaultSymbol: 'BTCUSDT',
        defaultTimeframe: '15',
        autoRefreshInterval: 30000 // 30 seconds
    };

    const _state = {
        currentSymbol: 'BTCUSDT',
        currentTimeframe: '15',
        isAutoRefreshEnabled: false,
        autoRefreshTimer: null,
        charts: {
            price: null,
            indicators: null,
            volume: null,
            equity: null
        },
        lastUpdate: null
    };

    // Private functions

    /**
     * Calculate technical indicators from price data
     * @param {Array} data - Array of price data objects (from API)
     * @param {Object} options - Calculation options (e.g., showIndicators)
     * @returns {Object} Calculated indicators { ema9: [], ema21: [], rsi: [] }
     * @private
     */
    function _calculateIndicators(data, options = {}) {
        if (!data || !data.length) return { ema9: [], ema21: [], rsi: [] };

        const showIndicators = options.showIndicators !== false;
        if (!showIndicators) return { ema9: [], ema21: [], rsi: [] };

        try {
            const ema9 = [];
            const ema21 = [];
            const rsi = [];

            let ema9Value = parseFloat(data[0].close);
            let ema21Value = parseFloat(data[0].close);
            const alpha9 = 2 / (9 + 1);
            const alpha21 = 2 / (21 + 1);
            let gains = [];
            let losses = [];

            data.forEach((item, index) => {
                const timestamp = new Date(item.timestamp).getTime();
                const close = parseFloat(item.close);

                if (index > 0) {
                    const prevClose = parseFloat(data[index-1].close);
                    if (!isNaN(prevClose)) {
                        const change = close - prevClose;
                        gains.push(change > 0 ? change : 0);
                        losses.push(change < 0 ? Math.abs(change) : 0);
                    }

                    // Calculate EMAs
                    ema9Value = (close * alpha9) + (ema9Value * (1 - alpha9));
                    ema21Value = (close * alpha21) + (ema21Value * (1 - alpha21));

                    ema9.push({
                        x: timestamp,
                        y: ema9Value
                    });

                    ema21.push({
                        x: timestamp,
                        y: ema21Value
                    });

                    // Calculate RSI
                    if (gains.length >= 14) {
                        const recentGains = gains.slice(-14);
                        const recentLosses = losses.slice(-14);
                        const avgGain = recentGains.reduce((sum, val) => sum + val, 0) / 14;
                        const avgLoss = recentLosses.reduce((sum, val) => sum + val, 0) / 14;
                        const rs = avgGain / (avgLoss === 0 ? 0.001 : avgLoss);
                        const rsiValue = 100 - (100 / (1 + rs));

                        rsi.push({
                            x: timestamp,
                            y: rsiValue
                        });
                    } else {
                        rsi.push({
                            x: timestamp,
                            y: 50 // Default value when not enough data
                        });
                    }
                }
            });

            return { ema9, ema21, rsi };
        } catch (error) {
            console.error('Error calculating indicators:', error);
            return { ema9: [], ema21: [], rsi: [] };
        }
    }


    function _updateTickerInfo(ticker) {
        if (!ticker) return;

        // Assuming API.formatTickerV5 is available and works
        const formattedTicker = typeof API !== 'undefined' && API.formatTickerV5 ? API.formatTickerV5(ticker) : ticker;

        // Update DOM elements
        const elements = {
            currentPrice: document.getElementById('current-price'),
            priceUpdated: document.getElementById('price-updated'),
            priceChange: document.getElementById('price-change'),
            highPrice: document.getElementById('high-price'),
            lowPrice: document.getElementById('low-price'),
            volume: document.getElementById('volume'),
            volumeUsd: document.getElementById('volume-usd'),
            fundingRate: document.getElementById('funding-rate')
        };

        if (elements.currentPrice) {
            elements.currentPrice.textContent = `$${formattedTicker.lastPrice || 'N/A'}`;
        }

        if (elements.priceUpdated) {
            elements.priceUpdated.textContent = `Updated: ${new Date().toLocaleTimeString()}`;
        }

        if (elements.priceChange) {
            const priceChangeText = formattedTicker.price24hPcnt || 'N/A';
            elements.priceChange.textContent = priceChangeText;
            if (priceChangeText !== 'N/A') {
                 const priceChange = parseFloat(priceChangeText.replace('%', ''));
                 elements.priceChange.className = priceChange > 0 ? 'text-success' :
                                                 priceChange < 0 ? 'text-danger' : '';
            } else {
                 elements.priceChange.className = '';
            }
        }

        if (elements.highPrice) {
            elements.highPrice.textContent = `$${formattedTicker.highPrice24h || 'N/A'}`;
        }

        if (elements.lowPrice) {
            elements.lowPrice.textContent = `$${formattedTicker.lowPrice24h || 'N/A'}`;
        }

        if (elements.volume) {
            elements.volume.textContent = formattedTicker.volume24h || 'N/A';
        }

        if (elements.volumeUsd) {
            elements.volumeUsd.textContent = `$${formattedTicker.turnover24h || 'N/A'}`;
        }

        if (elements.fundingRate && formattedTicker.fundingRate) {
            elements.fundingRate.textContent = formattedTicker.fundingRate;
        }
    }

    // Public API
    return {
        /**
         * Initialize the data module
         * @param {Object} options - Configuration options
         * @returns {Object} The DataModule instance
         */
        init: function(options) {
            if (options) {
                Object.assign(_config, options);
            }

            _state.currentSymbol = _config.defaultSymbol;
            _state.currentTimeframe = _config.defaultTimeframe;

            return this;
        },

        /**
         * Get the current state
         * @returns {Object} Current state
         */
        getState: function() {
            return { ..._state };
        },

        /**
         * Get the current configuration
         * @returns {Object} Current configuration
         */
        getConfig: function() {
            return { ..._config };
        },

        /**
         * Fetch all data
         */
        fetchData: function() {
            if (typeof API === 'undefined') {
                console.error('API module not available.');
                return;
            }
            this.fetchStatus();
            this.fetchBalance();
            this.fetchPositions();
            this.fetchMarketData();
            this.fetchPerformanceData();

            _state.lastUpdate = new Date();
        },

        /**
         * Fetch bot status
         */
        fetchStatus: function() {
            if (typeof API === 'undefined' || typeof UIEnhancements === 'undefined') return;
            API.getStatus(function(data) {
                if (data.status === 'OK') {
                    UIEnhancements.updateBotStatus(data.status_text); // Assuming status_text is the key
                } else {
                    console.error('Error fetching status:', data.message);
                    UIEnhancements.updateBotStatus('unknown');
                }
            });
        },

        /**
         * Fetch account balance
         */
        fetchBalance: function() {
             if (typeof API === 'undefined') return;
            API.getBalance(function(data) {
                if (data.status === 'OK') {
                    // Assuming balance data is in data.balance and API.formatBalanceV5 is available
                    const formattedBalance = typeof API !== 'undefined' && API.formatBalanceV5 ? API.formatBalanceV5(data.balance) : data.balance;

                    const availableBalance = document.getElementById('available-balance');
                    const equity = document.getElementById('equity');
                    const usedMargin = document.getElementById('used-margin');
                    const unrealizedPnl = document.getElementById('unrealized-pnl');

                    if (availableBalance) {
                        availableBalance.textContent = `${formattedBalance.availableBalance || 'N/A'} ${formattedBalance.coin || ''}`;
                    }

                    if (equity) {
                        equity.textContent = `${formattedBalance.equity || 'N/A'} ${formattedBalance.coin || ''}`;
                    }

                    if (usedMargin) {
                        usedMargin.textContent = `${formattedBalance.usedMargin || 'N/A'} ${formattedBalance.coin || ''}`;
                    }

                    if (unrealizedPnl) {
                        unrealizedPnl.textContent = `${formattedBalance.unrealizedPnl || 'N/A'} ${formattedBalance.coin || ''}`;
                    }
                } else {
                    console.error('Error fetching balance:', data.message);
                    // Optionally update UI to show error
                }
            });
        },

        /**
         * Fetch open positions
         */
        fetchPositions: function() {
             if (typeof API === 'undefined') return;
            API.getPositions(function(data) {
                const positionsContainer = document.getElementById('positions-container');
                const positionsTable = document.getElementById('positions-table'); // Assuming this might exist for a table view
                const noPositions = document.getElementById('no-positions');

                if (!positionsContainer) {
                    console.warn('Positions container not found.');
                    return;
                }

                if (data.status === 'OK') {
                    const positions = data.positions || []; // Ensure positions is an array

                    if (positions.length === 0) {
                        positionsContainer.style.display = 'none';
                        if (positionsTable) positionsTable.style.display = 'none';
                        if (noPositions) {
                            noPositions.style.display = 'block';
                            noPositions.innerHTML = `
                                <div class="text-center py-4">
                                    <i class="fas fa-info-circle fa-3x text-muted mb-3"></i>
                                    <p>No open positions</p>
                                </div>
                            `;
                        }
                    } else {
                        positionsContainer.style.display = 'block';
                        if (positionsTable) positionsTable.style.display = 'none'; // Hide table if card view is used
                        if (noPositions) noPositions.style.display = 'none';

                        positionsContainer.innerHTML = ''; // Clear previous positions
                        const row = document.createElement('div');
                        row.className = 'row';
                        positionsContainer.appendChild(row);

                        positions.forEach(function(position) {
                            // Assuming API.formatPositionV5 and API.createPositionCardHtml are available
                            const formattedPosition = typeof API !== 'undefined' && API.formatPositionV5 ? API.formatPositionV5(position) : position;
                            const positionCardHtml = typeof API !== 'undefined' && API.createPositionCardHtml ? API.createPositionCardHtml(formattedPosition) : ''; // Fallback

                            if (positionCardHtml) {
                                row.insertAdjacentHTML('beforeend', positionCardHtml);
                            }
                        });

                        // Add event listeners to close position buttons
                        document.querySelectorAll('.close-position-btn').forEach(button => {
                            button.addEventListener('click', function() {
                                const symbol = this.getAttribute('data-symbol');
                                if (typeof Utils !== 'undefined' && Utils.confirmAction) {
                                    Utils.confirmAction(`Are you sure you want to close your ${symbol} position?`, function() {
                                         if (typeof API !== 'undefined' && API.closePosition) {
                                            API.closePosition(symbol, function(response) {
                                                if (response.status === 'OK') {
                                                    if (typeof showToast === 'function') showToast(`${symbol} position closed successfully`, 'success');
                                                    DataModule.fetchPositions(); // Refresh positions after closing
                                                } else {
                                                    if (typeof showToast === 'function') showToast(`Error closing position: ${response.message}`, 'error');
                                                }
                                            });
                                         } else {
                                             console.error('API or closePosition function not available.');
                                         }
                                    });
                                } else {
                                    // Fallback to simple confirm if Utils is not available
                                    if (confirm(`Are you sure you want to close your ${symbol} position?`)) {
                                         if (typeof API !== 'undefined' && API.closePosition) {
                                            API.closePosition(symbol, function(response) {
                                                if (response.status === 'OK') {
                                                    if (typeof showToast === 'function') showToast(`${symbol} position closed successfully`, 'success');
                                                    DataModule.fetchPositions(); // Refresh positions after closing
                                                } else {
                                                    if (typeof showToast === 'function') showToast(`Error closing position: ${response.message}`, 'error');
                                                }
                                            });
                                         } else {
                                             console.error('API or closePosition function not available.');
                                         }
                                    }
                                }
                            });
                        });
                    }
                } else {
                    console.error('Error fetching positions:', data.message);

                    // Display error message
                    positionsContainer.style.display = 'none';
                    if (positionsTable) positionsTable.style.display = 'none';
                    if (noPositions) {
                        noPositions.style.display = 'block';
                        noPositions.innerHTML = `
                            <div class="text-center py-4">
                                <i class="fas fa-exclamation-circle fa-3x text-danger mb-3"></i>
                                <p>Error loading positions: ${data.message || 'Unknown error'}</p>
                            </div>
                        `;
                    }
                }
            });
        },

        /**
         * Fetch market data
         * @param {string} timeframe - Optional timeframe to fetch
         */
        fetchMarketData: function(timeframe) {
            if (typeof API === 'undefined') {
                console.error('API module not available.');
                return;
            }

            const tradingPairElement = document.getElementById('trading-pair');
            let symbol = tradingPairElement ? tradingPairElement.textContent : null;

            if (!symbol || symbol === 'Loading...') {
                symbol = _state.currentSymbol;
            }

            const tf = timeframe || _state.currentTimeframe;

            API.getMarketData(symbol, tf, function(data) {
                if (data.status === 'OK') {
                    _updateTickerInfo(data.ticker);
                    // Pass raw market data to update charts, indicator calculation is done there
                    DataModule.updatePriceChart(data.market_data);
                    DataModule.updateIndicatorsChart(data.market_data);
                    DataModule.updateVolumeChart(data.market_data);
                } else {
                    console.error('Error fetching market data:', data.message);
                    // Optionally update UI to show error
                }
            });
        },

        /**
         * Fetch performance data
         */
        fetchPerformanceData: function() {
             if (typeof API === 'undefined') return;
            API.getTradeHistory(function(data) {
                if (data.status === 'OK') {
                    // Assuming performance data is in data.performance
                    DataModule.updatePerformanceMetrics(data.performance);
                    // Assuming equity curve is in data.performance.equity_curve
                    DataModule.updateEquityChart(data.performance.equity_curve);
                } else {
                    console.error('Error fetching performance data:', data.message);
                    // Optionally update UI to show error
                }
            });
        },
        /**
         * Update price chart with market data
         * @param {Array} marketData - Market data to update chart with
         */
        updatePriceChart: function(marketData) {
            if (!marketData || marketData.length === 0) {
                console.warn('No market data available for price chart');
                // Optionally clear or show message on chart canvas
                return;
            }

            try {
                // Format data for chart, excluding indicators
                const chartData = typeof API !== 'undefined' && API.formatMarketDataForChartV5 ? API.formatMarketDataForChartV5(marketData) : { ohlc: [], volume: [] };
                const chartCanvas = document.getElementById('price-chart');

                if (!chartCanvas) {
                    console.warn('Price chart canvas not found');
                    return;
                }

                if (_state.charts.price) {
                    _state.charts.price.destroy();
                }

                const ctx = chartCanvas.getContext('2d');
                // Check if Chart and candlestick controller are available
                const useCandlestick = typeof Chart !== 'undefined' && typeof Chart.controllers.candlestick !== 'undefined';
                const chartType = typeof ChartSettings !== 'undefined' ? ChartSettings.getPreference('chartType', 'candlestick') : 'candlestick';


                if (useCandlestick && chartType === 'candlestick') {
                    _state.charts.price = new Chart(ctx, {
                        type: 'candlestick',
                        data: {
                            datasets: [{
                                label: 'OHLC',
                                data: chartData.ohlc,
                                color: {
                                    up: 'rgba(75, 192, 192, 1)',
                                    down: 'rgba(255, 99, 132, 1)',
                                    unchanged: 'rgba(110, 110, 110, 1)',
                                }
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            interaction: {
                                mode: 'index',
                                intersect: false
                            },
                            scales: {
                                x: {
                                    type: 'time',
                                    time: {
                                        unit: 'hour', // Adjust unit based on timeframe
                                        displayFormats: {
                                            hour: 'MMM d, HH:mm'
                                        }
                                    },
                                    title: {
                                        display: true,
                                        text: 'Time'
                                    }
                                },
                                y: {
                                    title: {
                                        display: true,
                                        text: 'Price'
                                    }
                                }
                            },
                            plugins: {
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            const item = context.raw;
                                            return [
                                                `Open: ${item.o}`,
                                                `High: ${item.h}`,
                                                `Low: ${item.l}`,
                                                `Close: ${item.c}`
                                            ];
                                        }
                                    }
                                },
                                zoom: {
                                    pan: {
                                        enabled: true,
                                        mode: 'x'
                                    },
                                    zoom: {
                                        wheel: {
                                            enabled: true,
                                        },
                                        pinch: {
                                            enabled: true
                                        },
                                        mode: 'x'
                                    }
                                }
                            }
                        }
                    });
                } else {
                    console.warn('Candlestick chart not available or line chart preferred, falling back to line chart');
                    const closeData = chartData.ohlc.map(item => ({
                        x: item.x,
                        y: item.c
                    }));

                    _state.charts.price = new Chart(ctx, {
                        type: 'line',
                        data: {
                            datasets: [{
                                label: 'Price',
                                data: closeData,
                                borderColor: 'rgba(75, 192, 192, 1)',
                                borderWidth: 2,
                                fill: false,
                                tension: 0.1
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            interaction: {
                                mode: 'index',
                                intersect: false
                            },
                            scales: {
                                x: {
                                    type: 'time',
                                    time: {
                                        unit: 'hour', // Adjust unit based on timeframe
                                        displayFormats: {
                                            hour: 'MMM d, HH:mm'
                                        }
                                    },
                                    title: {
                                        display: true,
                                        text: 'Time'
                                    }
                                },
                                y: {
                                    title: {
                                        display: true,
                                        text: 'Price'
                                    }
                                }
                            },
                            plugins: {
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            return `Price: ${context.parsed.y}`;
                                        }
                                    }
                                },
                                zoom: {
                                    pan: {
                                        enabled: true,
                                        mode: 'x'
                                    },
                                    zoom: {
                                        wheel: {
                                            enabled: true,
                                        },
                                        pinch: {
                                            enabled: true
                                        },
                                        mode: 'x'
                                    }
                                }
                            }
                        }
                    });
                }

                // Update chart enhancements if available
                if (typeof ChartEnhancements !== 'undefined') {
                    ChartEnhancements.setChartInstances(
                        _state.charts.price,
                        _state.charts.indicators,
                        _state.charts.volume
                    );
                     // Apply settings like theme after chart creation
                    if (typeof ChartSettings !== 'undefined') {
                         ChartSettings.applyToCharts(_state.charts.price, _state.charts.indicators, _state.charts.volume);
                    }
                }
            } catch (error) {
                console.error('Error updating price chart:', error);
            }
        },
        /**
         * Update indicators chart with market data
         * @param {Array} marketData - Market data to update chart with
         */
        updateIndicatorsChart: function(marketData) {
            if (!marketData || marketData.length === 0) {
                console.warn('No market data available for indicators chart');
                 // Optionally clear or show message on chart canvas
                return;
            }

            try {
                // Calculate indicators using the private function
                const chartSettings = typeof ChartSettings !== 'undefined' ? ChartSettings.current : null;
                const showIndicators = chartSettings ? chartSettings.indicators.ema : true; // Assuming EMA visibility controls all indicators here

                const indicatorsData = _calculateIndicators(marketData, { showIndicators });
                const chartCanvas = document.getElementById('indicators-chart');

                if (!chartCanvas) {
                    console.warn('Indicators chart canvas not found');
                    return;
                }

                if (_state.charts.indicators) {
                    _state.charts.indicators.destroy();
                }

                const ctx = chartCanvas.getContext('2d');
                 // Assuming Chart is available
                if (typeof Chart === 'undefined') {
                     console.error('Chart.js not available.');
                     return;
                }

                _state.charts.indicators = new Chart(ctx, {
                    type: 'line', // Indicators are typically line charts
                    data: {
                        datasets: [
                            {
                                label: 'EMA 9',
                                data: indicatorsData.ema9,
                                borderColor: 'rgba(255, 99, 132, 1)',
                                borderWidth: 2,
                                fill: false,
                                tension: 0.1,
                                hidden: !showIndicators // Hide if indicators are toggled off
                            },
                            {
                                label: 'EMA 21',
                                data: indicatorsData.ema21,
                                borderColor: 'rgba(54, 162, 235, 1)',
                                borderWidth: 2,
                                fill: false,
                                tension: 0.1,
                                hidden: !showIndicators // Hide if indicators are toggled off
                            },
                            // Optionally add price overlay for context
                            // {
                            //     label: 'Price',
                            //     data: marketData.map(item => ({ x: new Date(item.timestamp).getTime(), y: parseFloat(item.close) })),
                            //     borderColor: 'rgba(75, 192, 192, 0.5)',
                            //     borderWidth: 1,
                            //     fill: false,
                            //     pointRadius: 0,
                            //     hidden: !showIndicators // Hide if indicators are toggled off
                            // },
                            {
                                label: 'RSI',
                                data: indicatorsData.rsi,
                                borderColor: 'rgba(255, 206, 86, 1)',
                                borderWidth: 2,
                                fill: false,
                                tension: 0.1,
                                yAxisID: 'rsi',
                                hidden: !showIndicators // Hide if indicators are toggled off
                            }
                        ].filter(dataset => !dataset.hidden) // Filter out hidden datasets initially
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {
                            mode: 'index',
                            intersect: false
                        },
                        scales: {
                            x: {
                                type: 'time',
                                time: {
                                    unit: 'hour', // Adjust unit based on timeframe
                                    displayFormats: {
                                        hour: 'MMM d, HH:mm'
                                    }
                                },
                                title: {
                                    display: true,
                                    text: 'Time'
                                }
                            },
                            y: {
                                title: {
                                    display: true,
                                    text: 'Price' // Or 'Indicator Value'
                                }
                            },
                            rsi: {
                                position: 'right',
                                min: 0,
                                max: 100,
                                title: {
                                    display: true,
                                    text: 'RSI'
                                },
                                grid: {
                                    drawOnChartArea: false
                                }
                            }
                        },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const label = context.dataset.label || '';
                                        const value = context.parsed.y;
                                        return `${label}: ${value.toFixed(2)}`;
                                    }
                                }
                            },
                            zoom: {
                                pan: {
                                    enabled: true,
                                    mode: 'x'
                                },
                                zoom: {
                                    wheel: {
                                        enabled: true,
                                    },
                                    pinch: {
                                        enabled: true
                                    },
                                    mode: 'x'
                                }
                            }
                        }
                    }
                });

                 // Update chart enhancements if available
                if (typeof ChartEnhancements !== 'undefined') {
                    ChartEnhancements.setChartInstances(
                        _state.charts.price,
                        _state.charts.indicators,
                        _state.charts.volume
                    );
                     // Apply settings like theme after chart creation
                    if (typeof ChartSettings !== 'undefined') {
                         ChartSettings.applyToCharts(_state.charts.price, _state.charts.indicators, _state.charts.volume);
                    }
                }

            } catch (error) {
                console.error('Error updating indicators chart:', error);
            }
        },
        /**
         * Update volume chart with market data
         * @param {Array} marketData - Market data to update chart with
         */
        updateVolumeChart: function(marketData) {
            if (!marketData || marketData.length === 0) {
                console.warn('No market data available for volume chart');
                 // Optionally clear or show message on chart canvas
                return;
            }

            try {
                // Format data for chart, excluding indicators
                const chartData = typeof API !== 'undefined' && API.formatMarketDataForChartV5 ? API.formatMarketDataForChartV5(marketData) : { ohlc: [], volume: [] };
                const chartCanvas = document.getElementById('volume-chart');

                if (!chartCanvas) {
                    console.warn('Volume chart canvas not found');
                    return;
                }

                if (_state.charts.volume) {
                    _state.charts.volume.destroy();
                }

                const ctx = chartCanvas.getContext('2d');
                 // Assuming Chart is available
                if (typeof Chart === 'undefined') {
                     console.error('Chart.js not available.');
                     return;
                }

                const volumeData = chartData.volume.map((item, index) => {
                    const ohlcPoint = chartData.ohlc[index];
                    // Color volume bars based on price change
                    const barColor = ohlcPoint && ohlcPoint.c >= ohlcPoint.o ? 'rgba(75, 192, 192, 0.5)' : 'rgba(255, 99, 132, 0.5)';
                    const borderColor = ohlcPoint && ohlcPoint.c >= ohlcPoint.o ? 'rgba(75, 192, 192, 1)' : 'rgba(255, 99, 132, 1)';

                    return {
                        x: item.x,
                        y: item.y,
                        backgroundColor: barColor,
                        borderColor: borderColor
                    };
                });

                _state.charts.volume = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        datasets: [{
                            label: 'Volume',
                            data: volumeData,
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        interaction: {
                            mode: 'index',
                            intersect: false
                        },
                        scales: {
                            x: {
                                type: 'time',
                                time: {
                                    unit: 'hour', // Adjust unit based on timeframe
                                    displayFormats: {
                                        hour: 'MMM d, HH:mm'
                                    }
                                },
                                title: {
                                    display: true,
                                    text: 'Time'
                                }
                            },
                            y: {
                                title: {
                                    display: true,
                                    text: 'Volume'
                                },
                                beginAtZero: true
                            }
                        },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const value = context.parsed.y;
                                        // Use Utils for formatting if available
                                        const formatNumberFn = typeof Utils !== 'undefined' ? Utils.formatNumber : (num) => num.toLocaleString();
                                        return `Volume: ${formatNumberFn(value)}`;
                                    }
                                }
                            },
                            zoom: {
                                pan: {
                                    enabled: true,
                                    mode: 'x'
                                },
                                zoom: {
                                    wheel: {
                                        enabled: true,
                                    },
                                    pinch: {
                                        enabled: true
                                    },
                                    mode: 'x'
                                }
                            }
                        }
                    }
                });

                 // Update chart enhancements if available
                if (typeof ChartEnhancements !== 'undefined') {
                    ChartEnhancements.setChartInstances(
                        _state.charts.price,
                        _state.charts.indicators,
                        _state.charts.volume
                    );
                     // Apply settings like theme after chart creation
                    if (typeof ChartSettings !== 'undefined') {
                         ChartSettings.applyToCharts(_state.charts.price, _state.charts.indicators, _state.charts.volume);
                    }
                }

            } catch (error) {
                console.error('Error updating volume chart:', error);
            }
        },
        /**
         * Update performance metrics display
         * @param {Object} performance - Performance data
         */
        updatePerformanceMetrics: function(performance) {
            if (!performance) return;

            const elements = {
                totalTrades: document.getElementById('total-trades'),
                winRate: document.getElementById('win-rate'),
                profitFactor: document.getElementById('profit-factor'),
                totalPnl: document.getElementById('total-pnl')
            };

            const totalTrades = performance.total_trades || 0;
            const winRate = performance.win_rate || 0;
            const profitFactor = performance.profit_factor || 0;
            const totalPnl = performance.total_pnl || 0;

            // Use Utils for formatting if available
            const formatPercentageFn = typeof Utils !== 'undefined' ? Utils.formatPercentage : (num, dec = 2) => `${num.toFixed(dec)}%`;
            const formatCurrencyFn = typeof Utils !== 'undefined' ? Utils.formatCurrency : (num, dec = 2) => num.toFixed(dec);

            if (elements.totalTrades) {
                elements.totalTrades.textContent = totalTrades;
            }

            if (elements.winRate) {
                elements.winRate.textContent = formatPercentageFn(winRate);
                elements.winRate.className = winRate > 50 ? 'performance-value positive-value' :
                                            winRate < 50 ? 'performance-value negative-value' :
                                            'performance-value neutral-value';
            }

            if (elements.profitFactor) {
                elements.profitFactor.textContent = profitFactor.toFixed(2);
                elements.profitFactor.className = profitFactor > 1 ? 'performance-value positive-value' :
                                                profitFactor < 1 ? 'performance-value negative-value' :
                                                'performance-value neutral-value';
            }

            if (elements.totalPnl) {
                elements.totalPnl.textContent = `${formatCurrencyFn(totalPnl)} USDT`;
                elements.totalPnl.className = totalPnl > 0 ? 'performance-value positive-value' :
                                             totalPnl < 0 ? 'performance-value negative-value' :
                                             'performance-value neutral-value';
            }
        },

        /**
         * Update equity chart with equity curve data
         * @param {Array} equityCurve - Equity curve data [{ date: 'YYYY-MM-DD', equity: 1000 }]
         */
        updateEquityChart: function(equityCurve) {
            if (!equityCurve || equityCurve.length === 0) {
                 console.warn('No equity curve data available.');
                 // Optionally clear or show message on chart canvas
                 return;
            }

            const chartCanvas = document.getElementById('equity-chart');

            if (!chartCanvas) {
                console.warn('Equity chart canvas not found');
                return;
            }

            if (_state.charts.equity) {
                _state.charts.equity.destroy();
            }

            const ctx = chartCanvas.getContext('2d');
             // Assuming Chart is available
            if (typeof Chart === 'undefined') {
                 console.error('Chart.js not available.');
                 return;
            }

            _state.charts.equity = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: equityCurve.map(item => item.date), // Assuming date is in a format Chart.js can handle or needs parsing
                    datasets: [{
                        label: 'Equity Curve',
                        data: equityCurve.map(item => item.equity),
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 2,
                        tension: 0.1,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            type: 'category', // Use 'category' for date strings if not using time scale
                            title: {
                                display: true,
                                text: 'Date'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Equity (USDT)'
                            },
                            beginAtZero: false
                        }
                    },
                     plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.dataset.label || '';
                                    const value = context.parsed.y;
                                     // Use Utils for formatting if available
                                    const formatCurrencyFn = typeof Utils !== 'undefined' ? Utils.formatCurrency : (num, dec = 2) => num.toFixed(dec);
                                    return `${label}: ${formatCurrencyFn(value)} USDT`;
                                }
                            }
                        }
                    }
                }
            });
             // Apply settings like theme after chart creation
            if (typeof ChartSettings !== 'undefined') {
                 ChartSettings.applyToCharts(_state.charts.price, _state.charts.indicators, _state.charts.volume, _state.charts.equity);
            }
        },

        /**
         * Set the current timeframe and fetch new data
         * @param {string} timeframe - Timeframe to set
         */
        setTimeframe: function(timeframe) {
            _state.currentTimeframe = timeframe;
            this.fetchMarketData();
        },

        /**
         * Set the current symbol and fetch new data
         * @param {string} symbol - Symbol to set
         */
        setSymbol: function(symbol) {
            _state.currentSymbol = symbol;
            this.fetchMarketData();
        },

        /**
         * Enable auto-refresh of data
         */
        enableAutoRefresh: function() {
            if (_state.autoRefreshTimer) {
                clearInterval(_state.autoRefreshTimer);
            }

            _state.isAutoRefreshEnabled = true;
            _state.autoRefreshTimer = setInterval(() => {
                this.fetchData();
            }, _config.autoRefreshInterval);

        },

        /**
         * Disable auto-refresh of data
         */
        disableAutoRefresh: function() {
            if (_state.autoRefreshTimer) {
                clearInterval(_state.autoRefreshTimer);
                _state.autoRefreshTimer = null;
            }

            _state.isAutoRefreshEnabled = false;
        },

        /**
         * Toggle auto-refresh of data
         * @returns {boolean} New auto-refresh state
         */
        toggleAutoRefresh: function() {
            if (_state.isAutoRefreshEnabled) {
                this.disableAutoRefresh();
            } else {
                this.enableAutoRefresh();
            }
            return _state.isAutoRefreshEnabled;
        },

        /**
         * Get chart instances
         * @returns {Object} Chart instances
         */
        getCharts: function() {
            return { ..._state.charts };
        },

        /**
         * Set chart instances (used by UI module)
         * @param {Object} priceChart - Price chart instance
         * @param {Object} indicatorsChart - Indicators chart instance
         * @param {Object} volumeChart - Volume chart instance
         * @param {Object} equityChart - Equity chart instance
         */
        setChartInstances: function(priceChart, indicatorsChart, volumeChart, equityChart) {
             _state.charts.price = priceChart;
             _state.charts.indicators = indicatorsChart;
             _state.charts.volume = volumeChart;
             _state.charts.equity = equityChart;
        }
    };
})();

// Expose DataModule to global scope (optional, depending on module system)
window.DataModule = DataModule;


    // --- Initialization ---
    function init() {
        // Load initial data or setup connections if needed
    }
