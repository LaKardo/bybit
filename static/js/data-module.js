/**
 * DataModule - Handles data fetching, processing, and chart updates
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
    function _updateTickerInfo(ticker) {
        if (!ticker) return;

        const formattedTicker = API.formatTickerV5(ticker);

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
            elements.currentPrice.textContent = `$${formattedTicker.lastPrice}`;
        }

        if (elements.priceUpdated) {
            elements.priceUpdated.textContent = `Updated: ${new Date().toLocaleTimeString()}`;
        }

        if (elements.priceChange) {
            elements.priceChange.textContent = formattedTicker.price24hPcnt;
            const priceChange = parseFloat(formattedTicker.price24hPcnt);
            elements.priceChange.className = priceChange > 0 ? 'text-success' :
                                            priceChange < 0 ? 'text-danger' : '';
        }

        if (elements.highPrice) {
            elements.highPrice.textContent = `$${formattedTicker.highPrice24h}`;
        }

        if (elements.lowPrice) {
            elements.lowPrice.textContent = `$${formattedTicker.lowPrice24h}`;
        }

        if (elements.volume) {
            elements.volume.textContent = formattedTicker.volume24h;
        }

        if (elements.volumeUsd) {
            elements.volumeUsd.textContent = `$${formattedTicker.turnover24h}`;
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
            API.getStatus(function(data) {
                if (typeof UIEnhancements !== 'undefined' && UIEnhancements.updateStatus) {
                    UIEnhancements.updateStatus(data);
                }
            });
        },

        /**
         * Fetch account balance
         */
        fetchBalance: function() {
            API.getBalance(function(data) {
                if (data.status === 'OK') {
                    const formattedBalance = API.formatBalanceV5(data.balance);

                    const availableBalance = document.getElementById('available-balance');
                    const equity = document.getElementById('equity');
                    const usedMargin = document.getElementById('used-margin');
                    const unrealizedPnl = document.getElementById('unrealized-pnl');

                    if (availableBalance) {
                        availableBalance.textContent = `${formattedBalance.availableBalance} ${formattedBalance.coin}`;
                    }

                    if (equity) {
                        equity.textContent = `${formattedBalance.equity} ${formattedBalance.coin}`;
                    }

                    if (usedMargin) {
                        usedMargin.textContent = `${formattedBalance.usedMargin} ${formattedBalance.coin}`;
                    }

                    if (unrealizedPnl) {
                        unrealizedPnl.textContent = `${formattedBalance.unrealizedPnl} ${formattedBalance.coin}`;
                    }
                } else {
                    console.error('Error fetching balance:', data.message);
                }
            });
        },

        /**
         * Fetch open positions
         */
        fetchPositions: function() {
            API.getPositions(function(data) {
                if (data.status === 'OK') {
                    const positions = data.positions;
                    const positionsContainer = document.getElementById('positions-container');
                    const positionsTable = document.getElementById('positions-table');
                    const noPositions = document.getElementById('no-positions');

                    if (!positionsContainer) return;

                    if (positions.length === 0) {
                        if (positionsContainer) positionsContainer.style.display = 'none';
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
                        if (positionsContainer) positionsContainer.style.display = 'block';
                        if (positionsTable) positionsTable.style.display = 'none';
                        if (noPositions) noPositions.style.display = 'none';

                        positionsContainer.innerHTML = '';
                        const row = document.createElement('div');
                        row.className = 'row';
                        positionsContainer.appendChild(row);

                        positions.forEach(function(position) {
                            const formattedPosition = API.formatPositionV5(position);
                            const positionCard = API.createPositionCardHtml(formattedPosition);
                            row.insertAdjacentHTML('beforeend', positionCard);
                        });

                        // Add event listeners to close position buttons
                        document.querySelectorAll('.close-position-btn').forEach(button => {
                            button.addEventListener('click', function() {
                                const symbol = this.getAttribute('data-symbol');
                                if (confirm(`Are you sure you want to close your ${symbol} position?`)) {
                                    API.closePosition(symbol, function(response) {
                                        if (response.status === 'OK') {
                                            showToast(`${symbol} position closed successfully`, 'success');
                                            DataModule.fetchPositions();
                                        } else {
                                            showToast(`Error closing position: ${response.message}`, 'error');
                                        }
                                    });
                                }
                            });
                        });
                    }
                } else {
                    console.error('Error fetching positions:', data.message);

                    const positionsContainer = document.getElementById('positions-container');
                    const positionsTable = document.getElementById('positions-table');
                    const noPositions = document.getElementById('no-positions');

                    if (positionsContainer) positionsContainer.style.display = 'none';
                    if (positionsTable) positionsTable.style.display = 'none';
                    if (noPositions) {
                        noPositions.style.display = 'block';
                        noPositions.innerHTML = `
                            <div class="text-center py-4">
                                <i class="fas fa-exclamation-circle fa-3x text-danger mb-3"></i>
                                <p>Error loading positions: ${data.message}</p>
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
            const tradingPairElement = document.getElementById('trading-pair');
            let symbol = tradingPairElement ? tradingPairElement.textContent : null;

            if (!symbol || symbol === 'Loading...') {
                symbol = _state.currentSymbol;
            }

            const tf = timeframe || _state.currentTimeframe;

            API.getMarketData(symbol, tf, function(data) {
                if (data.status === 'OK') {
                    _updateTickerInfo(data.ticker);
                    DataModule.updatePriceChart(data.market_data);
                    DataModule.updateIndicatorsChart(data.market_data);
                    DataModule.updateVolumeChart(data.market_data);
                } else {
                    console.error('Error fetching market data:', data.message);
                }
            });
        },

        /**
         * Fetch performance data
         */
        fetchPerformanceData: function() {
            API.getPerformanceData(function(data) {
                if (data.status === 'OK') {
                    DataModule.updatePerformanceMetrics(data.performance);
                    DataModule.updateEquityChart(data.performance.equity_curve);
                } else {
                    console.error('Error fetching performance data:', data.message);
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
                return;
            }

            try {
                const chartData = API.formatMarketDataForChartV5(marketData);
                const chartCanvas = document.getElementById('price-chart');

                if (!chartCanvas) {
                    console.warn('Price chart canvas not found');
                    return;
                }

                if (_state.charts.price) {
                    _state.charts.price.destroy();
                }

                const ctx = chartCanvas.getContext('2d');
                const useCandlestick = typeof Chart.controllers.candlestick !== 'undefined';

                if (useCandlestick) {
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
                                        unit: 'hour',
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
                    console.warn('Candlestick chart not available, falling back to line chart');
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
                                        unit: 'hour',
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
                return;
            }

            try {
                const chartData = API.formatMarketDataForChartV5(marketData);
                const chartCanvas = document.getElementById('indicators-chart');

                if (!chartCanvas) {
                    console.warn('Indicators chart canvas not found');
                    return;
                }

                if (_state.charts.indicators) {
                    _state.charts.indicators.destroy();
                }

                const ctx = chartCanvas.getContext('2d');
                const priceData = chartData.ohlc.map(item => ({ x: item.x, y: item.c }));

                _state.charts.indicators = new Chart(ctx, {
                    type: 'line',
                    data: {
                        datasets: [
                            {
                                label: 'EMA 9',
                                data: chartData.ema9,
                                borderColor: 'rgba(255, 99, 132, 1)',
                                borderWidth: 2,
                                fill: false,
                                tension: 0.1
                            },
                            {
                                label: 'EMA 21',
                                data: chartData.ema21,
                                borderColor: 'rgba(54, 162, 235, 1)',
                                borderWidth: 2,
                                fill: false,
                                tension: 0.1
                            },
                            {
                                label: 'Price',
                                data: priceData,
                                borderColor: 'rgba(75, 192, 192, 0.5)',
                                borderWidth: 1,
                                fill: false,
                                pointRadius: 0
                            },
                            {
                                label: 'RSI',
                                data: chartData.rsi,
                                borderColor: 'rgba(255, 206, 86, 1)',
                                borderWidth: 2,
                                fill: false,
                                tension: 0.1,
                                yAxisID: 'rsi'
                            }
                        ]
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
                                    unit: 'hour',
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
                return;
            }

            try {
                const chartData = API.formatMarketDataForChartV5(marketData);
                const chartCanvas = document.getElementById('volume-chart');

                if (!chartCanvas) {
                    console.warn('Volume chart canvas not found');
                    return;
                }

                if (_state.charts.volume) {
                    _state.charts.volume.destroy();
                }

                const ctx = chartCanvas.getContext('2d');
                const volumeData = chartData.volume.map((item, index) => {
                    const ohlcPoint = chartData.ohlc[index];
                    return {
                        x: item.x,
                        y: item.y,
                        backgroundColor: ohlcPoint.c >= ohlcPoint.o ? 'rgba(75, 192, 192, 0.5)' : 'rgba(255, 99, 132, 0.5)',
                        borderColor: ohlcPoint.c >= ohlcPoint.o ? 'rgba(75, 192, 192, 1)' : 'rgba(255, 99, 132, 1)'
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
                                    unit: 'hour',
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
                                        return `Volume: ${value.toLocaleString()}`;
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

            const totalTrades = performance.total_trades;
            const winRate = performance.win_rate;
            const profitFactor = performance.profit_factor;
            const totalPnl = performance.total_pnl;

            if (elements.totalTrades) {
                elements.totalTrades.textContent = totalTrades;
            }

            if (elements.winRate) {
                elements.winRate.textContent = `${winRate.toFixed(2)}%`;
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
                elements.totalPnl.textContent = `${totalPnl.toFixed(2)} USDT`;
                elements.totalPnl.className = totalPnl > 0 ? 'performance-value positive-value' :
                                             totalPnl < 0 ? 'performance-value negative-value' :
                                             'performance-value neutral-value';
            }
        },

        /**
         * Update equity chart with equity curve data
         * @param {Array} equityCurve - Equity curve data
         */
        updateEquityChart: function(equityCurve) {
            if (!equityCurve || equityCurve.length === 0) return;

            const chartCanvas = document.getElementById('equity-chart');

            if (!chartCanvas) {
                console.warn('Equity chart canvas not found');
                return;
            }

            if (_state.charts.equity) {
                _state.charts.equity.destroy();
            }

            const ctx = chartCanvas.getContext('2d');

            _state.charts.equity = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: equityCurve.map(item => item.date),
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
                    }
                }
            });
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
        }
    };
})();
