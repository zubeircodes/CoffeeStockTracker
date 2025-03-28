// chart-config.js - Chart configuration for Coffee Shop Inventory Management System

/**
 * Global chart configuration and utility functions
 * for consistent chart styling and functionality across the application
 */

// Default chart.js configuration for dark theme
const darkThemeChartConfig = {
    color: '#f8f9fa',
    scales: {
        x: {
            ticks: {
                color: '#adb5bd'
            },
            grid: {
                color: 'rgba(255, 255, 255, 0.1)'
            }
        },
        y: {
            ticks: {
                color: '#adb5bd'
            },
            grid: {
                color: 'rgba(255, 255, 255, 0.1)'
            }
        }
    },
    plugins: {
        legend: {
            labels: {
                color: '#f8f9fa'
            }
        },
        tooltip: {
            backgroundColor: 'rgba(33, 37, 41, 0.8)',
            titleColor: '#f8f9fa',
            bodyColor: '#f8f9fa',
            borderColor: 'rgba(255, 255, 255, 0.1)',
            borderWidth: 1
        }
    }
};

// Standard color palette that matches the Bootstrap theme
const chartColorPalette = [
    '#4e73df', // primary
    '#1cc88a', // success
    '#36b9cc', // info
    '#f6c23e', // warning
    '#e74a3b', // danger
    '#5a5c69', // secondary
    '#6f42c1', // purple
    '#fd7e14', // orange
    '#20c997', // teal
    '#6610f2'  // indigo
];

/**
 * Creates a properly configured line chart for inventory trends
 * @param {HTMLElement} ctx - Canvas context for the chart
 * @param {Array} labels - X-axis labels (dates, etc.)
 * @param {Array} datasets - Chart datasets
 * @returns {Chart} Configured Chart.js instance
 */
function createInventoryTrendChart(ctx, labels, datasets) {
    // Apply color palette to datasets if not specified
    datasets.forEach((dataset, index) => {
        if (!dataset.borderColor) {
            dataset.borderColor = chartColorPalette[index % chartColorPalette.length];
        }
        if (!dataset.backgroundColor) {
            dataset.backgroundColor = `${dataset.borderColor}33`; // Add transparency
        }
        
        // Default dataset styling
        dataset.tension = 0.3;
        dataset.pointRadius = 3;
        dataset.pointHoverRadius = 5;
        dataset.pointHitRadius = 10;
    });
    
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: Object.assign({}, darkThemeChartConfig, {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Inventory Trends',
                    color: '#f8f9fa',
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                }
            }
        })
    });
}

/**
 * Creates a properly configured pie chart for category distribution
 * @param {HTMLElement} ctx - Canvas context for the chart
 * @param {Array} labels - Category names
 * @param {Array} data - Values for each category
 * @param {String} title - Chart title
 * @returns {Chart} Configured Chart.js instance
 */
function createCategoryPieChart(ctx, labels, data, title = 'Category Distribution') {
    // Generate background colors if not enough
    const backgroundColors = chartColorPalette.slice(0, data.length);
    
    return new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: backgroundColors,
                borderWidth: 1,
                borderColor: '#343a40'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#f8f9fa',
                        padding: 10,
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                },
                title: {
                    display: true,
                    text: title,
                    color: '#f8f9fa',
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.formattedValue;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((context.raw / total) * 100);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Creates a properly configured bar chart for inventory analysis
 * @param {HTMLElement} ctx - Canvas context for the chart
 * @param {Array} labels - X-axis labels
 * @param {Array} datasets - Chart datasets
 * @param {String} title - Chart title
 * @returns {Chart} Configured Chart.js instance
 */
function createInventoryBarChart(ctx, labels, datasets, title = 'Inventory Analysis') {
    // Apply color palette to datasets if not specified
    datasets.forEach((dataset, index) => {
        if (!dataset.backgroundColor) {
            dataset.backgroundColor = chartColorPalette[index % chartColorPalette.length];
        }
        if (!dataset.borderColor) {
            dataset.borderColor = dataset.backgroundColor;
        }
        
        // Default dataset styling
        dataset.borderWidth = 1;
        dataset.borderRadius = 4;
    });
    
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: Object.assign({}, darkThemeChartConfig, {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: title,
                    color: '#f8f9fa',
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                }
            }
        })
    });
}

/**
 * Creates a properly configured doughnut chart
 * @param {HTMLElement} ctx - Canvas context for the chart
 * @param {Array} labels - Category names
 * @param {Array} data - Values for each category
 * @param {String} title - Chart title
 * @returns {Chart} Configured Chart.js instance
 */
function createDoughnutChart(ctx, labels, data, title = 'Distribution') {
    // Generate background colors if not enough
    const backgroundColors = chartColorPalette.slice(0, data.length);
    
    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: backgroundColors,
                borderWidth: 1,
                borderColor: '#343a40'
            }]
        },
        options: {
            responsive: true,
            cutout: '75%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#f8f9fa',
                        padding: 10,
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                },
                title: {
                    display: true,
                    text: title,
                    color: '#f8f9fa',
                    font: {
                        size: 16,
                        weight: 'bold'
                    }
                }
            }
        }
    });
}

/**
 * Initialize dashboard charts
 * This function is called from the dashboard page
 */
function initDashboardCharts() {
    // Category distribution chart (already implemented in dashboard.html)
    
    // We can add additional charts here if needed in the future
    // This is a placeholder for potential future dashboard charts
}

/**
 * Update chart with new data
 * @param {Chart} chart - Chart.js instance to update
 * @param {Array} labels - New labels
 * @param {Array} data - New data array(s)
 */
function updateChartData(chart, labels, data) {
    chart.data.labels = labels;
    
    if (Array.isArray(data[0])) {
        // Multiple datasets
        data.forEach((dataSet, index) => {
            if (chart.data.datasets[index]) {
                chart.data.datasets[index].data = dataSet;
            }
        });
    } else {
        // Single dataset
        chart.data.datasets[0].data = data;
    }
    
    chart.update();
}

/**
 * Convert chart to image for reports
 * @param {Chart} chart - Chart.js instance
 * @param {String} format - Image format ('image/png', 'image/jpeg', etc.)
 * @returns {String} Data URL of the chart image
 */
function chartToImage(chart, format = 'image/png') {
    return chart.toBase64Image(format);
}
