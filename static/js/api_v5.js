/**
 * API V5 utilities for Bybit Trading Bot Web Interface
 * This file contains functions for handling Bybit API V5 data
 */

// Helper function to format numbers with commas
function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return parseFloat(num).toLocaleString();
}

// Helper function to format dates
function formatDate(dateStr) {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        return date.toLocaleString();
    } catch (e) {
        return dateStr;
    }
}

// Format balance data from API V5
function formatBalanceV5(balance) {
    if (!balance) return {};

    return {
        availableBalance: parseFloat(balance.available_balance || 0).toFixed(4),
        walletBalance: parseFloat(balance.wallet_balance || 0).toFixed(4),
        unrealizedPnl: parseFloat(balance.unrealized_pnl || 0).toFixed(4),
        equity: parseFloat(balance.equity || 0).toFixed(4),
        usedMargin: parseFloat(balance.used_margin || 0).toFixed(4),
        usedMarginRate: parseFloat(balance.used_margin_rate || 0).toFixed(2),
        marginRatio: parseFloat(balance.margin_ratio || 0).toFixed(2),
        freeMargin: parseFloat(balance.free_margin || 0).toFixed(4),
        coin: balance.coin || 'USDT'
    };
}

// Format position data from API V5
function formatPositionV5(position) {
    if (!position) return {};

    return {
        symbol: position.symbol || '',
        side: position.side || '',
        size: parseFloat(position.size || 0).toFixed(4),
        positionValue: parseFloat(position.position_value || 0).toFixed(2),
        entryPrice: parseFloat(position.entry_price || 0).toFixed(2),
        markPrice: parseFloat(position.mark_price || 0).toFixed(2),
        unrealizedPnl: parseFloat(position.unrealized_pnl || 0).toFixed(4),
        unrealizedPnlPercent: position.entry_price ?
            (parseFloat(position.unrealized_pnl || 0) / (parseFloat(position.position_value || 0)) * 100).toFixed(2) :
            '0.00',
        leverage: parseFloat(position.leverage || 0).toFixed(0),
        liqPrice: parseFloat(position.liq_price || 0).toFixed(2),
        takeProfit: parseFloat(position.take_profit || 0).toFixed(2),
        stopLoss: parseFloat(position.stop_loss || 0).toFixed(2),
        trailingStop: parseFloat(position.trailing_stop || 0).toFixed(2),
        createdTime: formatDate(position.created_time || ''),
        updatedTime: formatDate(position.updated_time || '')
    };
}

// Format ticker data from API V5
function formatTickerV5(ticker) {
    if (!ticker) return {};

    return {
        symbol: ticker.symbol || '',
        lastPrice: parseFloat(ticker.lastPrice || 0).toFixed(2),
        markPrice: parseFloat(ticker.markPrice || 0).toFixed(2),
        indexPrice: parseFloat(ticker.indexPrice || 0).toFixed(2),
        highPrice24h: parseFloat(ticker.highPrice24h || 0).toFixed(2),
        lowPrice24h: parseFloat(ticker.lowPrice24h || 0).toFixed(2),
        volume24h: formatNumber(parseFloat(ticker.volume24h || 0).toFixed(2)),
        turnover24h: formatNumber(parseFloat(ticker.turnover24h || 0).toFixed(2)),
        price24hPcnt: (parseFloat(ticker.price24hPcnt || 0) * 100).toFixed(2) + '%',
        openInterest: formatNumber(parseFloat(ticker.openInterest || 0).toFixed(2)),
        fundingRate: (parseFloat(ticker.fundingRate || 0) * 100).toFixed(4) + '%',
        nextFundingTime: formatDate(ticker.nextFundingTime || '')
    };
}

// Format market data for charts from API V5
function formatMarketDataForChartV5(data) {
    console.log('Formatting market data:', data);

    if (!data || !data.length) {
        console.warn('No data to format');
        return { ohlc: [], volume: [], ema9: [], ema21: [], rsi: [] };
    }

    try {
        const ohlc = [];
        const volume = [];
        const ema9 = [];
        const ema21 = [];
        const rsi = [];

        // Get chart settings if available
        const chartSettings = window.ChartSettings ? window.ChartSettings.current : null;
        const showIndicators = chartSettings ? chartSettings.indicators.ema : true;
        const showVolume = chartSettings ? chartSettings.indicators.volume : true;

        // Calculate simple EMAs for demonstration
        // In a real implementation, you would use proper EMA calculation
        let ema9Value = parseFloat(data[0].close);
        let ema21Value = parseFloat(data[0].close);
        const alpha9 = 2 / (9 + 1);
        const alpha21 = 2 / (21 + 1);

        // Calculate simple RSI for demonstration
        let gains = [];
        let losses = [];

        data.forEach((item, index) => {
            try {
                // Parse values safely
                const timestamp = new Date(item.timestamp).getTime();
                const open = parseFloat(item.open);
                const high = parseFloat(item.high);
                const low = parseFloat(item.low);
                const close = parseFloat(item.close);
                const vol = parseFloat(item.volume);

                if (isNaN(timestamp) || isNaN(open) || isNaN(high) || isNaN(low) || isNaN(close) || isNaN(vol)) {
                    console.warn('Invalid data point:', item);
                    return; // Skip this data point
                }

                // OHLC data for candlestick chart
                ohlc.push({
                    x: timestamp,
                    o: open,
                    h: high,
                    l: low,
                    c: close
                });

                // Volume data if enabled
                if (showVolume) {
                    volume.push({
                        x: timestamp,
                        y: vol
                    });
                }

                // Calculate EMAs if indicators are enabled
                if (showIndicators && index > 0) {
                    const prevClose = parseFloat(data[index-1].close);
                    if (!isNaN(prevClose)) {
                        // Calculate price change for RSI
                        const change = close - prevClose;
                        gains.push(change > 0 ? change : 0);
                        losses.push(change < 0 ? Math.abs(change) : 0);
                    }

                    // Simple EMA calculation
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

                    // Calculate RSI if we have enough data
                    if (gains.length >= 14) {
                        // Get the last 14 values
                        const recentGains = gains.slice(-14);
                        const recentLosses = losses.slice(-14);

                        // Calculate average gain and loss
                        const avgGain = recentGains.reduce((sum, val) => sum + val, 0) / 14;
                        const avgLoss = recentLosses.reduce((sum, val) => sum + val, 0) / 14;

                        // Calculate RS and RSI
                        const rs = avgGain / (avgLoss === 0 ? 0.001 : avgLoss); // Avoid division by zero
                        const rsiValue = 100 - (100 / (1 + rs));

                        rsi.push({
                            x: timestamp,
                            y: rsiValue
                        });
                    } else {
                        // Not enough data for RSI, use 50 as neutral value
                        rsi.push({
                            x: timestamp,
                            y: 50
                        });
                    }
                }
            } catch (err) {
                console.error('Error processing data point:', err, item);
            }
        });

        // If indicators are disabled, clear the arrays
        if (!showIndicators) {
            ema9.length = 0;
            ema21.length = 0;
            rsi.length = 0;
        }

        // If volume is disabled, clear the array
        if (!showVolume) {
            volume.length = 0;
        }

        console.log('Formatted data:', {
            ohlcCount: ohlc.length,
            volumeCount: volume.length,
            ema9Count: ema9.length,
            ema21Count: ema21.length,
            showIndicators: showIndicators,
            showVolume: showVolume
        });

        return { ohlc, volume, ema9, ema21, rsi };
    } catch (error) {
        console.error('Error formatting market data:', error);
        return { ohlc: [], volume: [], ema9: [], ema21: [], rsi: [] };
    }
}

// Update dashboard with API V5 data
function updateDashboardWithV5Data(data) {
    if (!data) return;

    // Update balance
    if (data.balance) {
        const formattedBalance = formatBalanceV5(data.balance);
        $('#wallet-balance').text(formattedBalance.walletBalance + ' ' + formattedBalance.coin);
        $('#available-balance').text(formattedBalance.availableBalance + ' ' + formattedBalance.coin);
        $('#unrealized-pnl').text(formattedBalance.unrealizedPnl + ' ' + formattedBalance.coin);

        // Update margin info if available
        if (formattedBalance.usedMargin) {
            $('#margin-info').show();
            $('#used-margin').text(formattedBalance.usedMargin + ' ' + formattedBalance.coin);
            $('#margin-ratio').text(formattedBalance.marginRatio + '%');
        } else {
            $('#margin-info').hide();
        }
    }

    // Update positions
    if (data.positions && data.positions.length) {
        const positionsContainer = $('#positions-container');
        positionsContainer.empty();

        data.positions.forEach(position => {
            const formattedPosition = formatPositionV5(position);
            const positionHtml = createPositionCardHtml(formattedPosition);
            positionsContainer.append(positionHtml);
        });

        $('#no-positions').hide();
        $('#positions-container').show();
    } else {
        $('#no-positions').show();
        $('#positions-container').hide();
    }

    // Update ticker
    if (data.ticker) {
        const formattedTicker = formatTickerV5(data.ticker);
        $('#last-price').text(formattedTicker.lastPrice);
        $('#mark-price').text(formattedTicker.markPrice);
        $('#funding-rate').text(formattedTicker.fundingRate);
        $('#24h-change').text(formattedTicker.price24hPcnt);

        // Set color based on 24h change
        const change24h = parseFloat(formattedTicker.price24hPcnt);
        if (change24h > 0) {
            $('#24h-change').removeClass('text-danger').addClass('text-success');
        } else if (change24h < 0) {
            $('#24h-change').removeClass('text-success').addClass('text-danger');
        } else {
            $('#24h-change').removeClass('text-success text-danger');
        }

        // Update additional ticker info
        $('#24h-high').text(formattedTicker.highPrice24h);
        $('#24h-low').text(formattedTicker.lowPrice24h);
        $('#24h-volume').text(formattedTicker.volume24h);
    }
}

// Create HTML for position card
function createPositionCardHtml(position) {
    const isProfitable = parseFloat(position.unrealizedPnl) > 0;
    const profitClass = isProfitable ? 'text-success' : 'text-danger';

    return `
    <div class="col-md-6 mb-3">
        <div class="card position-card">
            <div class="card-header bg-${position.side === 'Buy' ? 'success' : 'danger'} text-white">
                <h5 class="mb-0">${position.symbol} - ${position.side}</h5>
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
                    <button class="btn btn-sm btn-danger close-position-btn" data-symbol="${position.symbol}">Close Position</button>
                </div>
            </div>
        </div>
    </div>
    `;
}

// Initialize close position buttons
function initClosePositionButtons() {
    $(document).on('click', '.close-position-btn', function() {
        const symbol = $(this).data('symbol');

        if (confirm(`Are you sure you want to close your ${symbol} position?`)) {
            $.ajax({
                url: '/api/close_position',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ symbol: symbol }),
                success: function(data) {
                    if (data.status === 'OK') {
                        addLogEntry(`Position closed: ${symbol}`, 'info', new Date().toISOString().replace('T', ' ').substring(0, 19));
                        // Refresh data
                        fetchData();
                    } else {
                        addLogEntry(`Failed to close position: ${data.message}`, 'error', new Date().toISOString().replace('T', ' ').substring(0, 19));
                    }
                },
                error: function(xhr, status, error) {
                    addLogEntry(`Error closing position: ${error}`, 'error', new Date().toISOString().replace('T', ' ').substring(0, 19));
                }
            });
        }
    });
}

// Document ready
$(document).ready(function() {
    // Initialize close position buttons
    initClosePositionButtons();
});
