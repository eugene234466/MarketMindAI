/* ============================================================
CHARTS.JS — Global Chart Configuration & Utilities
Handles all Plotly chart rendering across the app
Reusable chart functions called from dashboard & report pages
============================================================ */


/* ── 1. GLOBAL CHART THEME ──────────────────────────────────*/
const chartTheme = {
    paper_bgcolor : "transparent",
    plot_bgcolor  : "transparent",
    font          : {
        family    : "Inter, sans-serif",
        color     : "#ffffff",
        size      : 12
    },
    xaxis         : {
        gridcolor : "rgba(255, 255, 255, 0.1)",
        linecolor : "rgba(255, 255, 255, 0.1)",
        zerolinecolor: "rgba(255, 255, 255, 0.1)"
    },
    yaxis         : {
        gridcolor : "rgba(255, 255, 255, 0.1)",
        linecolor : "rgba(255, 255, 255, 0.1)",
        zerolinecolor: "rgba(255, 255, 255, 0.1)"
    },
    margin        : { t: 30, b: 50, l: 60, r: 20 },
    showlegend    : true,
    legend        : {
        font      : { color: "#ffffff" },
        bgcolor   : "transparent"
    }
};


/* ── 2. COLOR PALETTE ───────────────────────────────────────*/
const colors = {
    cyan    : "#00e5ff",
    navy    : "#0a1628",
    green   : "#00ff64",
    red     : "#ff3232",
    yellow  : "#ffc800",
    white   : "#ffffff",
    muted   : "rgba(255, 255, 255, 0.5)",

    palette : [
        "#00e5ff",
        "#00ff64",
        "#ffc800",
        "#ff3232",
        "#a855f7",
        "#f97316"
    ]
};


/* ── 3. MARKET TRENDS CHART ─────────────────────────────────*/
function renderTrendsChart(elementId, trendsData) {
    const trace = {
        x: trendsData.dates,
        y: trendsData.values,
        type: "scatter",
        mode: "lines+markers",
        name: "Market Interest",
        line: {
            color: colors.cyan,
            width: 3,
            shape: "spline"
        },
        marker: {
            color: colors.cyan,
            size: 6
        },
        fill: "tozeroy",
        fillcolor: "rgba(0, 229, 255, 0.1)"
    };

    const layout = {
        ...chartTheme,
        title: {
            text: "Market Interest Over Time",
            font: { color: colors.cyan, size: 16 }
        },
        xaxis: {
            ...chartTheme.xaxis,
            title: { text: "Date", font: { color: colors.muted } }
        },
        yaxis: {
            ...chartTheme.yaxis,
            title: { text: "Interest Score", font: { color: colors.muted } },
            range: [0, 100]
        }
    };

    Plotly.newPlot(elementId, [trace], layout, { responsive: true });
}


/* ── 4. SALES FORECAST CHART ────────────────────────────────*/
function renderSalesChart(elementId, salesData) {

    const revenueData = salesData.revenue.map(v => Number(v));
    const trendData   = salesData.trend.map(v => Number(v));

    const revenueTrace = {
        x: salesData.months,
        y: revenueData,
        type: "bar",
        name: "Projected Revenue",
        marker: {
            color: salesData.months.map((_, i) =>
                `rgba(0, 229, 255, ${0.4 + (i * 0.05)})`
            ),
            line: { color: colors.cyan, width: 1 }
        }
    };

    const trendTrace = {
        x: salesData.months,
        y: trendData,
        type: "scatter",
        mode: "lines",
        name: "Growth Trend",
        line: {
            color: colors.green,
            width: 2,
            dash: "dot"
        }
    };

    const layout = {
        ...chartTheme,
        title: {
            text: "12-Month Revenue Forecast",
            font: { color: colors.cyan, size: 16 }
        },
        xaxis: {
            ...chartTheme.xaxis,
            title: { text: "Month", font: { color: colors.muted } },
            type: "category"
        },
        yaxis: {
            ...chartTheme.yaxis,
            title: { text: "Revenue (USD)", font: { color: colors.muted } },
            tickprefix: "$",
            rangemode: "tozero",
            range: [0, Math.max(...revenueData) * 1.2]
        },
        barmode: "group"
    };

    Plotly.newPlot(elementId, [revenueTrace, trendTrace], layout, { responsive: true });
}


/* ── 5. COMPETITOR PIE CHART ────────────────────────────────*/
function renderCompetitorChart(elementId, competitorData) {
    const trace = {
        labels: competitorData.map(c => c.name),
        values: competitorData.map(c => c.market_share),
        type: "pie",
        hole: 0.4,
        marker: {
            colors: colors.palette,
            line: { color: colors.navy, width: 2 }
        },
        textinfo: "label+percent",
        textfont: { color: colors.white }
    };

    const layout = {
        ...chartTheme,
        title: {
            text: "Market Share Distribution",
            font: { color: colors.cyan, size: 16 }
        }
    };

    Plotly.newPlot(elementId, [trace], layout, { responsive: true });
}


/* ── 6. NICHE SCORE RADAR CHART ─────────────────────────────*/
function renderNicheRadar(elementId, nicheData) {
    const traces = nicheData.map((niche, i) => ({
        type: "scatterpolar",
        r: [
            niche.profitability,
            niche.competition,
            niche.demand,
            niche.growth,
            niche.accessibility
        ],
        theta: [
            "Profitability",
            "Low Competition",
            "Demand",
            "Growth",
            "Accessibility"
        ],
        fill: "toself",
        name: niche.name,
        line: { color: colors.palette[i] },
        fillcolor: `${colors.palette[i]}33`
    }));

    const layout = {
        ...chartTheme,
        title: {
            text: "Niche Opportunity Radar",
            font: { color: colors.cyan, size: 16 }
        },
        polar: {
            bgcolor: "transparent",
            radialaxis: {
                visible: true,
                range: [0, 100],
                gridcolor: "rgba(255,255,255,0.1)",
                color: colors.muted
            },
            angularaxis: {
                gridcolor: "rgba(255,255,255,0.1)",
                color: colors.white
            }
        }
    };

    Plotly.newPlot(elementId, traces, layout, { responsive: true });
}


/* ── 7. TREND COMPARISON CHART ──────────────────────────────*/
function renderTrendComparison(elementId, trendsData) {
    const traces = trendsData.map((trend, i) => ({
        x: trend.dates,
        y: trend.values,
        type: "scatter",
        mode: "lines",
        name: trend.keyword,
        line: {
            color: colors.palette[i],
            width: 2,
            shape: "spline"
        }
    }));

    const layout = {
        ...chartTheme,
        title: {
            text: "Trend Comparison",
            font: { color: colors.cyan, size: 16 }
        },
        xaxis: {
            ...chartTheme.xaxis,
            title: { text: "Date", font: { color: colors.muted } }
        },
        yaxis: {
            ...chartTheme.yaxis,
            title: { text: "Interest", font: { color: colors.muted } },
            range: [0, 100]
        }
    };

    Plotly.newPlot(elementId, traces, layout, { responsive: true });
}


/* ── 8. UTILITY FUNCTIONS ───────────────────────────────────*/

window.addEventListener("resize", function() {
    const charts = document.querySelectorAll(".chart-container");
    charts.forEach(function(chart) {
        Plotly.relayout(chart.id, {
            width: chart.offsetWidth
        });
    });
});

function showChartLoading(elementId) {
    document.getElementById(elementId).innerHTML = `
        <div style="display:flex; align-items:center;
                    justify-content:center; height:100%;
                    color: rgba(0,229,255,0.5);">
            <div class="spinner-custom me-3"></div>
            Loading chart data...
        </div>
    `;
}

function showChartError(elementId, message) {
    document.getElementById(elementId).innerHTML = `
        <div style="display:flex; align-items:center;
                    justify-content:center; height:100%;
                    color: rgba(255,50,50,0.7);">
            <i class="fas fa-exclamation-triangle me-2"></i>
            ${message || "Failed to load chart"}
        </div>
    `;
}
