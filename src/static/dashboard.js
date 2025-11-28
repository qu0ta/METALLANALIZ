let priceChart = null;
let currentCompany = '';
let currentProduct = '';

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('current-date').textContent = new Date().toLocaleDateString('ru-RU');

    const today = new Date();
    const yearAgo = new Date(today.getFullYear() - 1, today.getMonth(), today.getDate());

    document.getElementById('end-date').value = today.toISOString().split('T')[0];
    document.getElementById('start-date').value = yearAgo.toISOString().split('T')[0];

    loadGlobalStats();
    initEmptyChart();
});

async function loadGlobalStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();

        document.getElementById('stats-info').textContent =
            `${stats.total_companies} компаний, ${stats.total_products} продуктов, ${stats.total_records.toLocaleString()} записей`;
    } catch {
        // silent error
    }
}

async function onCompanyChange() {
    const companySelect = document.getElementById('company-select');
    const productSelect = document.getElementById('product-select');

    currentCompany = companySelect.value;

    if (!currentCompany) {
        productSelect.disabled = true;
        productSelect.innerHTML = '<option value="">-- Сначала выберите компанию --</option>';
        return;
    }

    try {
        const response = await fetch(`/api/products?company=${encodeURIComponent(currentCompany)}`);
        const products = await response.json();

        productSelect.disabled = false;
        productSelect.innerHTML = '<option value="">-- Выберите продукт --</option>';

        products.forEach(product => {
            const option = document.createElement('option');
            option.value = product;
            option.textContent = product;
            productSelect.appendChild(option);
        });
    } catch {
        // silent error
    }
}

function onProductChange() {
    currentProduct = document.getElementById('product-select').value;
}

function initEmptyChart() {
    const ctx = document.getElementById('priceChart').getContext('2d');

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Цена',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                tension: 0.1,
                fill: true,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return 'Цена: ' + context.parsed.y.toLocaleString('ru-RU') + ' руб.';
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Дата'
                    }
                },
                y: {
                    display: true,
                    title: {
                        display: true,
                        text: 'Цена (руб.)'
                    }
                }
            }
        }
    });
}

async function updateChart() {
    if (!currentCompany || !currentProduct) {
        alert('Пожалуйста, выберите компанию и продукт');
        return;
    }

    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;

    const loadBtn = document.getElementById('load-btn');
    loadBtn.disabled = true;
    loadBtn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Загрузка...';

    try {
        const params = new URLSearchParams({
            company: currentCompany,
            product: currentProduct,
            start_date: startDate,
            end_date: endDate
        });

        const response = await fetch(`/api/prices?${params}`);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        if (priceChart) {
            priceChart.destroy();
        }

        initEmptyChart();

        priceChart.data.labels = data.dates;
        priceChart.data.datasets[0].data = data.prices;
        priceChart.data.datasets[0].label = `${currentProduct} (${currentCompany})`;
        priceChart.update();

        document.getElementById('chart-subtitle').textContent =
            `${currentProduct} | ${data.dates.length} точек`;

        updateStats(data.stats);
        document.getElementById('stats-cards').style.display = 'flex';

    } catch (error) {
        alert('Ошибка загрузки данных: ' + error.message);
    } finally {
        loadBtn.disabled = false;
        loadBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i> Обновить';
    }
}

function updateStats(stats) {
    document.getElementById('min-price').textContent = stats.min.toLocaleString('ru-RU') + ' руб.';
    document.getElementById('max-price').textContent = stats.max.toLocaleString('ru-RU') + ' руб.';
    document.getElementById('avg-price').textContent = Math.round(stats.avg).toLocaleString('ru-RU') + ' руб.';
    document.getElementById('data-points').textContent = stats.count.toLocaleString('ru-RU');
}

async function exportData() {
    if (!currentCompany || !currentProduct) {
        alert('Выберите компанию и продукт для экспорта');
        return;
    }

    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;

    const params = new URLSearchParams({
        company: currentCompany,
        product: currentProduct,
        start_date: startDate,
        end_date: endDate
    });

    window.location.href = `/api/export?${params}`;
}