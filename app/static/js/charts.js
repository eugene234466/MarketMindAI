/* ============================================================
CHARTS.JS — Global Chart Configuration & Utilities
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
    xaxis : {
        gridcolor : "rgba(255, 255, 255, 0.1)",
        linecolor : "rgba(255, 255, 255, 0.1)",
        zerolinecolor: "rgba(255, 255, 255, 0.1)"
    },
    yaxis : {
        gridcolor : "rgba(255, 255, 255, 0.1)",
        linecolor : "rgba(255, 255, 255, 0.1)",
        zerolinecolor: "rgba(255, 255, 255, 0.1)"
    },
    margin     : { t: 30, b: 50, l: 60, r: 20 },
    showlegend : true,
    legend     : {
        font    : { color: "#ffffff" },
        bgcolor : "transparent"
    }
};


/* ── 2. COLORS ─────────────────────────────────────────────*/
const colors = {
    cyan   : "#00e5ff",
    navy   : "#0a1628",
    green  : "#00ff64",
    red    : "#ff3232",
    yellow : "#ffc800",
    white  : "#ffffff",
    muted  : "rgba(255,255,255,0.5)",
    palette: ["#00e5ff","#00ff64","#ffc800","#ff3232","#a855f7","#f97316"]
};


/* ── 3. SALES CHART (FIXED) ────────────────────────────────*/
function renderSalesChart(elementId, salesData) {

    const revenueData = salesData.revenue.map(Number);
    const trendData   = salesData.trend.map(Number);

    const revenueTrace = {
        x: salesData.months,
        y: revenueData,
        type: "bar",
        name: "Revenue",
        marker: {
            color: salesData.months.map((_, i) =>
                `rgba(0,229,255,${0.4 + i * 0.05})`
            ),
            line: { color: colors.cyan, width: 1 }
        }
    };

    const trendTrace = {
        x: salesData.months,
        y: trendData,
        type: "scatter",
        mode: "lines",
        name: "Trend",
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
            font: { color: colors.cyan }
        },
        xaxis: {
            ...chartTheme.xaxis,
            title: { text: "Month", font: { color: colors.muted } },
            type: "category" // 🔥 fixes Jan 2000 issue
        },
        yaxis: {
            ...chartTheme.yaxis,
            title: { text: "Revenue (USD)", font: { color: colors.muted } },
            tickprefix: "$",
            rangemode: "tozero",
            range: [0, Math.max(...revenueData) * 1.2]
        }
    };

    Plotly.newPlot(elementId, [revenueTrace, trendTrace], layout, {
        responsive: true,
        displayModeBar: false
    });
}


/* ── 4. SAFE RESIZE (FIXED) ────────────────────────────────*/
window.addEventListener("resize", function() {
    document.querySelectorAll(".chart-container").forEach(chart => {
        Plotly.Plots.resize(chart);
    });
});


/* ── 5. LOADING / ERROR ────────────────────────────────────*/
function showChartLoading(id) {
    document.getElementById(id).innerHTML =
        "<div style='text-align:center;color:#00e5ff;'>Loading...</div>";
}

function showChartError(id, msg) {
    document.getElementById(id).innerHTML =
        `<div style='color:red;text-align:center;'>${msg}</div>`;
}
