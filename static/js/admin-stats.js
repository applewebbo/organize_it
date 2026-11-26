document.addEventListener("DOMContentLoaded", () => {
    const dataEl = document.getElementById("admin-stats-data");
    if (!dataEl || typeof Chart === "undefined") {
        return;
    }

    const stats = JSON.parse(dataEl.textContent);

    const buildBarChart = (canvasId, series, color) => {
        const canvas = document.getElementById(canvasId);
        if (!canvas || !series) {
            return;
        }
        const label = canvas.dataset.label || "";
        new Chart(canvas, {
            type: "bar",
            data: {
                labels: series.labels,
                datasets: [
                    {
                        label,
                        data: series.counts,
                        backgroundColor: color,
                        borderRadius: 6,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 0 },
                    },
                },
            },
        });
    };

    buildBarChart("chart-new-users", stats.new_users_per_month, "rgba(14, 165, 233, 0.75)");
    buildBarChart("chart-trips-per-month", stats.trips_per_month, "rgba(20, 184, 166, 0.75)");

    const statusCanvas = document.getElementById("chart-trips-by-status");
    if (statusCanvas && stats.trips_by_status) {
        new Chart(statusCanvas, {
            type: "doughnut",
            data: {
                labels: stats.trips_by_status.labels,
                datasets: [
                    {
                        label: statusCanvas.dataset.label || "",
                        data: stats.trips_by_status.counts,
                        backgroundColor: [
                            "rgba(59, 130, 246, 0.8)",
                            "rgba(245, 158, 11, 0.8)",
                            "rgba(16, 185, 129, 0.8)",
                            "rgba(99, 102, 241, 0.8)",
                            "rgba(107, 114, 128, 0.8)",
                        ],
                        borderWidth: 0,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "bottom" },
                },
            },
        });
    }
});
