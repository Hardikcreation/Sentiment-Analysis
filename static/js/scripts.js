window.onload = function () {
    // Sentiment Bar Chart
    new Chart(document.getElementById('barChart').getContext('2d'), {
        type: 'bar',
        data: {
            labels: ['Positive', 'Neutral', 'Negative'],
            datasets: [{
                label: 'Tweet Count',
                data: [sentimentData.positive, sentimentData.neutral, sentimentData.negative],
                backgroundColor: ['#28a74588', '#6c757d88', '#dc354588'],
                borderColor: ['#28a745', '#6c757d', '#dc3545'],
                borderWidth: 1,
                borderRadius: 5
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true } }
        }
    });

    // Hashtag Frequency Chart
    new Chart(document.getElementById('hashtagBarChart').getContext('2d'), {
        type: 'bar',
        data: {
            labels: hashtagLabels,
            datasets: [{
                label: "Frequency",
                data: hashtagCounts,
                backgroundColor: "#17a2b8"
            }]
        },
        options: {
            responsive: true,
            indexAxis: 'y',
            plugins: { legend: { display: false } },
            scales: { x: { beginAtZero: true } }
        }
    });

    // Hashtag List
    const list = document.getElementById("hashtagList");
    hashtagLabels.forEach((label, i) => {
        const item = document.createElement("li");
        item.className = "list-group-item d-flex justify-content-between align-items-center";
        item.textContent = label;
        const badge = document.createElement("span");
        badge.className = "badge bg-primary rounded-pill";
        badge.textContent = hashtagCounts[i];
        item.appendChild(badge);
        list.appendChild(item);
    });

    // Engagement Over Time
    new Chart(document.getElementById('lineChart').getContext('2d'), {
        type: 'line',
        data: {
            labels: timeLabels,
            datasets: [{
                label: "Engagement",
                data: timeCounts,
                fill: false,
                borderColor: "#007bff",
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: true, title: { display: true, text: "Time" } },
                y: { display: true, title: { display: true, text: "Count" } }
            }
        }
    });
};
