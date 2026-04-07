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
    
    // CRITICAL FIX: Extract only the month name (first 3 characters) from any date format
    const monthLabels = salesData.months.map(month => {
        // If it's a string that contains a date
        if (typeof month === 'string') {
            // Try to extract just the month abbreviation (Jan, Feb, etc.)
            const monthMatch = month.match(/^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/i);
            if (monthMatch) {
                return monthMatch[0]; // Return just the month abbreviation
            }
            // If no month abbreviation found, return as-is but ensure it's a string
            return String(month);
        }
        // If it's a Date object
        if (month instanceof Date) {
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            return months[month.getMonth()];
        }
        // Fallback: convert to string and take first 3 characters
        return String(month).substring(0, 3);
    });

    const revenueTrace = {
        x: monthLabels,
        y: revenueData,
        type: "bar",
        name: "Revenue",
        marker: {
            color: monthLabels.map((_, i) =>
                `rgba(0,229,255,${0.4 + i * 0.05})`
            ),
            line: { color: colors.cyan, width: 1 }
        },
        text: revenueData.map(value => `$${value.toLocaleString()}`),
        textposition: "auto",
        textfont: { color: colors.white, size: 10 }
    };

    const trendTrace = {
        x: monthLabels,
        y: trendData,
        type: "scatter",
        mode: "lines+markers",
        name: "Trend",
        line: {
            color: colors.green,
            width: 3,
            shape: "spline"
        },
        marker: {
            color: colors.green,
            size: 6,
            symbol: "circle"
        }
    };

    const layout = {
        ...chartTheme,
        title: {
            text: "12-Month Sales Forecast",
            font: { color: colors.cyan, size: 16 }
        },
        xaxis: {
            title: { text: "Month", font: { color: colors.muted } },
            type: "category",
            tickangle: -45,
            tickfont: { size: 11, color: colors.white },
            tickmode: "array",
            tickvals: monthLabels,
            ticktext: monthLabels,
            gridcolor: "rgba(255, 255, 255, 0.1)",
            linecolor: "rgba(255, 255, 255, 0.1)",
            zerolinecolor: "rgba(255, 255, 255, 0.1)"
        },
        yaxis: {
            title: { text: "Revenue (USD)", font: { color: colors.muted } },
            tickprefix: "$",
            tickformat: ",.0f",
            rangemode: "tozero",
            range: [0, Math.max(...revenueData, ...trendData) * 1.15],
            gridcolor: "rgba(255, 255, 255, 0.15)",
            linecolor: "rgba(255, 255, 255, 0.1)",
            zerolinecolor: "rgba(255, 255, 255, 0.1)"
        },
        bargap: 0.2,
        bargroupgap: 0.1,
        hovermode: "closest",
        plot_bgcolor: "rgba(0, 0, 0, 0.2)"
    };

    const config = {
        responsive: true,
        displayModeBar: true,
        displaylogo: false,
        modeBarButtonsToRemove: ['lasso2d', 'select2d']
    };

    Plotly.newPlot(elementId, [revenueTrace, trendTrace], layout, config);
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
