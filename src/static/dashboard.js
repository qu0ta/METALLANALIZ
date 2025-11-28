
let priceChart = null;
let selectedCompanies = [];
let currentProduct = '';
let companiesData = [];


document.addEventListener('DOMContentLoaded', function() {

    document.getElementById('current-date').textContent = new Date().toLocaleDateString('ru-RU');


    const today = new Date();
    const yearAgo = new Date(today.getFullYear() - 1, today.getMonth(), today.getDate());
    document.getElementById('end-date').value = today.toISOString().split('T')[0];
    document.getElementById('start-date').value = yearAgo.toISOString().split('T')[0];

    loadCompanies();
    initEmptyChart();
});


async function loadCompanies() {
    console.log('=== LOAD COMPANIES ===');

    try {
        const response = await fetch('/api/companies');
        const companies = await response.json();

        console.log('Companies loaded:', companies);

        companiesData = companies;


        const select = document.getElementById('companies-select');
        if (!select) {
            console.error('❌ Element companies-select not found!');
            return;
        }


        select.innerHTML = '';

        companies.forEach((company, index) => {
            const option = document.createElement('option');
            option.value = company.company;
            option.textContent = `${company.company} (${company.product_count} продуктов)`;
            select.appendChild(option);
        });

        console.log('✅ Companies loaded successfully');

    } catch (error) {
        console.error('❌ Error loading companies:', error);
    }
}


function onCompanyChange() {
    console.log('=== ON COMPANY CHANGE ===');

    const select = document.getElementById('companies-select');
    if (!select) {
        console.error('❌ companies-select element not found');
        return;
    }


    selectedCompanies = Array.from(select.selectedOptions).map(option => option.value);

    console.log('Selected companies:', selectedCompanies);


    const productSelect = document.getElementById('product-select');
    if (selectedCompanies.length === 0) {
        productSelect.innerHTML = '<option value="">-- Select companies first --</option>';
        productSelect.disabled = true;
        return;
    }

    productSelect.disabled = false;
    updateProductSelect();
}


async function updateProductSelect() {
    console.log('=== UPDATE PRODUCT SELECT ===');

    if (selectedCompanies.length === 0) return;

    try {

        const response = await fetch(`/api/products?company=${encodeURIComponent(selectedCompanies[0])}`);
        const products = await response.json();

        console.log('Products loaded:', products);

        const productSelect = document.getElementById('product-select');
        productSelect.innerHTML = '<option value="">-- Select product --</option>';

        products.forEach(product => {
            const option = document.createElement('option');
            option.value = product;
            option.textContent = product;
            productSelect.appendChild(option);
        });

    } catch (error) {
        console.error('❌ Error loading products:', error);
    }
}

// Initialize empty chart
function initEmptyChart() {
    const ctx = document.getElementById('priceChart');
    if (!ctx) {
        console.error('❌ priceChart canvas not found');
        return;
    }

    if (priceChart) {
        priceChart.destroy();
    }

    priceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: []
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: 'top' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' +
                                   context.parsed.y.toLocaleString('ru-RU') + ' руб.';
                        }
                    }
                }
            },
            scales: {
                x: { display: true, title: { display: true, text: 'Дата' } },
                y: { display: true, title: { display: true, text: 'Цена (руб.)' } }
            }
        }
    });
}


function onProductChange() {
    currentProduct = document.getElementById('product-select').value;
}


async function updateChart() {
    console.log('=== UPDATE CHART ===');

    if (selectedCompanies.length === 0 || !currentProduct) {
        alert('Выберите компании и продукт');
        return;
    }

    console.log('Companies:', selectedCompanies);
    console.log('Product:', currentProduct);

    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;

    const colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'];

    try {
        const datasets = [];

        for (let i = 0; i < selectedCompanies.length; i++) {
            const company = selectedCompanies[i];

            const params = new URLSearchParams({
                company: company,
                product: currentProduct,
                start_date: startDate,
                end_date: endDate
            });

            const response = await fetch(`/api/prices?${params}`);
            const data = await response.json();

            console.log(`Data for ${company}:`, data);

            datasets.push({
                label: company,
                data: data.prices,
                borderColor: colors[i % colors.length],
                backgroundColor: colors[i % colors.length] + '20',
                tension: 0.1,
                fill: false,
                pointRadius: 4,
                pointHoverRadius: 6
            });

            if (i === 0) {
                priceChart.data.labels = data.dates;
            }
        }

        if (priceChart) {
            priceChart.destroy();
        }

        initEmptyChart();
        priceChart.data.datasets = datasets;
        priceChart.update();

        console.log('✅ Chart updated successfully');

    } catch (error) {
        console.error('❌ Error updating chart:', error);
    }
}


async function exportData() {
    if (selectedCompanies.length === 0 || !currentProduct) {
        alert('Выберите компании и продукт для экспорта');
        return;
    }

    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;

    const params = new URLSearchParams();
    params.append('product', currentProduct);
    params.append('start_date', startDate);
    params.append('end_date', endDate);
    selectedCompanies.forEach(company => params.append('company', company));

    window.location.href = `/api/export?${params.toString()}`;
}