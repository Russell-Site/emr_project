/* ============================================================
   analytics.js - Disease Trend Analytics Charts
   Naglo-load at nagre-render ng lahat ng Chart.js visualizations
   para sa Disease Trend Analytics section
   ============================================================ */

// I-store ang mga chart instances para ma-destroy bago gumawa ng bago
let analyticsLineInst = null;
let analyticsBarInst  = null;
let analyticsPieInst  = null;

/**
 * I-load ang lahat ng charts sa Analytics section.
 * Tinatawag kapag pinili ang Analytics sa sidebar.
 */
async function loadAnalyticsCharts() {
    const year      = parseInt(document.getElementById('analyticsYear')?.value      || new Date().getFullYear());
    const barangay  = document.getElementById('analyticsBarangay')?.value  || '';

    // I-load ang tatlong charts nang sabay-sabay para mas mabilis
    await Promise.all([
        loadAnalyticsLineChart(year, barangay),
        loadAnalyticsBarChart(year, barangay),
        loadAnalyticsPieChart(year, barangay)
    ]);
}

/**
 * I-load ang monthly trend line chart sa Analytics section.
 * Ipinapakita ang bawat sakit bilang isang linya sa chart.
 */
async function loadAnalyticsLineChart(year, barangayId = '') {
    let url = `/api/analytics/disease-trends?year=${year}`;
    if (barangayId) url += `&barangay_id=${barangayId}`;

    const data = await apiGet(url);
    const ctx  = document.getElementById('analyticsLineChart');
    if (!ctx || !data) return;

    // I-destroy ang lumang chart para maiwasan ang memory leak
    if (analyticsLineInst) analyticsLineInst.destroy();

    if (!data.datasets || data.datasets.length === 0) {
        // Walang datos para sa napiling filter
        ctx.getContext('2d').clearRect(0, 0, ctx.width, ctx.height);
        showEmptyChart(ctx, 'No disease trend data available for the selected filters.');
        return;
    }

    analyticsLineInst = new Chart(ctx, {
        type: 'line',
        data: {
            labels:   data.labels,
            datasets: data.datasets.map(ds => ({
                ...ds,
                pointBackgroundColor: ds.borderColor,
                pointBorderColor:     '#fff',
                pointBorderWidth:     2,
                borderWidth:          2.5
            }))
        },
        options: {
            responsive:          true,
            maintainAspectRatio: false,
            interaction: {
                mode:      'index',
                intersect: false
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth:  14,
                        font:      { size: 11, family: 'DM Sans' },
                        padding:   12,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(10, 25, 47, 0.92)',
                    titleFont:   { size: 12, weight: 'bold' },
                    bodyFont:    { size: 11 },
                    padding:     12,
                    cornerRadius: 8
                },
                title: {
                    display: true,
                    text:    `Monthly Disease Cases — ${year}`,
                    font:    { size: 13, weight: 'bold', family: 'Sora' },
                    color:   '#1a1a2e',
                    padding: { bottom: 12 }
                }
            },
            scales: {
                x: {
                    grid:  { display: false },
                    ticks: { font: { size: 10 } }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(0,0,0,0.05)', drawBorder: false },
                    ticks: {
                        font:     { size: 10 },
                        stepSize: 1,
                        callback: (val) => Number.isInteger(val) ? val : null
                    }
                }
            },
            animation: {
                duration: 800,
                easing:   'easeInOutQuart'
            }
        }
    });
}

/**
 * I-load ang cases per barangay horizontal bar chart.
 */
async function loadAnalyticsBarChart(year, barangayId = '') {
    let url = `/api/analytics/disease-per-barangay?year=${year}`;
    if (barangayId) url += `&barangay_id=${barangayId}`;

    const data = await apiGet(url);
    const ctx  = document.getElementById('analyticsBarChart');
    if (!ctx || !data) return;

    if (analyticsBarInst) analyticsBarInst.destroy();

    if (!data.labels || data.labels.length === 0) {
        showEmptyChart(ctx, 'No barangay data available.');
        return;
    }

    analyticsBarInst = new Chart(ctx, {
        type: 'bar',
        data: {
            labels:   data.labels,
            datasets: [{
                label:           'Total Disease Cases',
                data:            data.data,
                backgroundColor: data.backgroundColor,
                borderRadius:    8,
                borderSkipped:   false,
                borderWidth:     0
            }]
        },
        options: {
            responsive:          true,
            maintainAspectRatio: false,
            indexAxis:           'y',  // Horizontal bar para mas madaling basahin ang barangay names
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(10,25,47,0.92)',
                    callbacks: {
                        // Idagdag ang "cases" sa tooltip
                        label: (ctx) => ` ${ctx.raw} case${ctx.raw !== 1 ? 's' : ''}`
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: { color: 'rgba(0,0,0,0.05)' },
                    ticks: { font: { size: 10 } }
                },
                y: {
                    grid: { display: false },
                    ticks: { font: { size: 11 } }
                }
            },
            animation: { duration: 700, easing: 'easeOutQuart' }
        }
    });
}

/**
 * I-load ang top diseases doughnut/pie chart.
 */
async function loadAnalyticsPieChart(year, barangayId = '') {
    let url = `/api/analytics/top-diseases?limit=8`;
    if (year)       url += `&year=${year}`;
    if (barangayId) url += `&barangay_id=${barangayId}`;

    const data = await apiGet(url);
    const ctx  = document.getElementById('analyticsPieChart');
    if (!ctx || !data) return;

    if (analyticsPieInst) analyticsPieInst.destroy();

    if (!data.labels || data.labels.length === 0) {
        showEmptyChart(ctx, 'No disease data available.');
        return;
    }

    // Kalkulahin ang total para sa percentage labels
    const total = data.data.reduce((sum, val) => sum + val, 0);

    analyticsPieInst = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels:   data.labels,
            datasets: [{
                data:            data.data,
                backgroundColor: data.backgroundColor,
                borderWidth:     3,
                borderColor:     '#ffffff',
                hoverOffset:     8,
                hoverBorderWidth: 4
            }]
        },
        options: {
            responsive:          true,
            maintainAspectRatio: false,
            cutout:              '60%',
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        boxWidth:      14,
                        font:          { size: 11 },
                        padding:       10,
                        usePointStyle: true,
                        // Idagdag ang percentage sa legend labels
                        generateLabels: (chart) => {
                            const datasets = chart.data.datasets;
                            return chart.data.labels.map((label, i) => {
                                const value   = datasets[0].data[i];
                                const pct     = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return {
                                    text:            `${label} (${pct}%)`,
                                    fillStyle:       datasets[0].backgroundColor[i],
                                    strokeStyle:     datasets[0].backgroundColor[i],
                                    pointStyle:      'circle',
                                    index:           i
                                };
                            });
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(10,25,47,0.92)',
                    callbacks: {
                        label: (ctx) => {
                            const pct = total > 0 ? ((ctx.raw / total) * 100).toFixed(1) : 0;
                            return ` ${ctx.raw} cases (${pct}%)`;
                        }
                    }
                }
            },
            animation: { duration: 900, easing: 'easeInOutCubic' }
        }
    });
}

/**
 * Magpakita ng empty state message sa loob ng canvas.
 * Ginagamit kapag walang datos para sa napiling filter.
 */
function showEmptyChart(canvas, message) {
    const ctx = canvas.getContext('2d');
    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw na semi-transparent na background
    ctx.fillStyle = 'rgba(240, 244, 248, 0.7)';
    ctx.roundRect(10, 10, canvas.width - 20, canvas.height - 20, 10);
    ctx.fill();

    // I-draw ang empty state icon at text
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;

    ctx.font    = '32px serif';
    ctx.fillStyle = 'rgba(107,123,141,0.5)';
    ctx.fillText('📊', cx, cy - 24);

    ctx.font      = 'bold 13px "DM Sans", sans-serif';
    ctx.fillStyle = 'rgba(107,123,141,0.8)';
    ctx.fillText(message, cx, cy + 16);

    ctx.restore();
}