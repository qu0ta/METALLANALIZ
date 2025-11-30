from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
from datetime import datetime, timedelta
import io
import sys
import os
import json
import plotly
import plotly.express as px
import plotly.graph_objects as go

app = Flask(__name__)
app.config['CSV_FILE'] = 'data/metal_prices_history.csv'

class PriceDashboard:
    def __init__(self, csv_path: str):
        try:
            self.df = pd.read_csv(csv_path)
            self.df['date'] = pd.to_datetime(self.df['date'])
            print(f"✅ Данные загружены: {len(self.df)} записей, {self.df['company'].nunique()} компаний")
            print(f"📊 Уникальные продукты: {self.df['product'].unique()}")
        except Exception as e:
            print(f"❌ Ошибка загрузки CSV: {e}")
            sys.exit(1)

    def get_companies(self) -> list:
        company_stats = self.df.groupby('company').agg({
            'product': 'nunique',
            'price': ['min', 'max', 'mean']
        }).reset_index()
        company_stats.columns = ['company', 'product_count', 'min_price', 'max_price', 'avg_price']
        company_stats = company_stats.sort_values('product_count', ascending=False)
        return company_stats.to_dict('records')

    def get_products(self, company: str = None) -> list:
        if company:
            products = self.df[self.df['company'] == company]['product'].unique()
        else:
            products = self.df['product'].unique()
        return sorted(list(products))

    def get_price_data(self, company: str, product: str, start_date: str = None, end_date: str = None) -> dict:
        mask = (self.df['company'] == company) & (self.df['product'] == product)

        if start_date:
            mask &= (self.df['date'] >= pd.to_datetime(start_date))
        if end_date:
            mask &= (self.df['date'] <= pd.to_datetime(end_date))

        filtered = self.df[mask].copy()
        filtered = filtered.sort_values('date')

        if len(filtered) == 0:
            return {
                'dates': [],
                'prices': [],
                'stats': {'min': 0, 'max': 0, 'avg': 0, 'count': 0, 'last_price': 0}
            }

        stats = {
            'min': float(filtered['price'].min()),
            'max': float(filtered['price'].max()),
            'avg': float(filtered['price'].mean()),
            'count': len(filtered),
            'last_price': float(filtered['price'].iloc[-1])
        }

        return {
            'dates': filtered['date'].dt.strftime('%Y-%m-%d').tolist(),
            'prices': [float(price) for price in filtered['price'].tolist()],
            'stats': stats
        }

    def create_price_chart(self, company: str, product: str, start_date: str = None, end_date: str = None) -> str:
        data = self.get_price_data(company, product, start_date, end_date)
        
        if not data['dates']:
            return None
            
        # Создаем график с Plotly
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=data['dates'],
            y=data['prices'],
            mode='lines+markers',
            name=f'{product}',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=6, color='#1f77b4')
        ))
        
        # Настройка layout
        fig.update_layout(
            title={
                'text': f'Динамика цен: {company}<br><sub>{product}</sub>',
                'x': 0.5,
                'xanchor': 'center'
            },
            xaxis_title='Дата',
            yaxis_title='Цена (руб)',
            template='plotly_white',
            height=500,
            showlegend=False,
            font=dict(size=12)
        )
        
        # Добавляем линию среднего значения
        if data['stats']['avg'] > 0:
            fig.add_hline(
                y=data['stats']['avg'],
                line_dash="dash",
                line_color="red",
                annotation_text=f"Средняя: {data['stats']['avg']:.2f} руб"
            )
        
        return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

# Инициализация дашборда
dashboard = PriceDashboard(app.config['CSV_FILE'])

@app.route('/')
def index():
    companies = dashboard.get_companies()
    products = dashboard.get_products()
    
    # Получаем статистику для отображения
    total_companies = len(companies)
    total_products = len(products)
    total_records = len(dashboard.df)
    
    return render_template('dashboard.html', 
                         companies=companies, 
                         products=products,
                         total_companies=total_companies,
                         total_products=total_products,
                         total_records=total_records)

@app.route('/api/products')
def api_products():
    company = request.args.get('company')
    products = dashboard.get_products(company)
    return jsonify(products)

@app.route('/api/prices')
def api_prices():
    company = request.args.get('company')
    product = request.args.get('product')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not company or not product:
        return jsonify({'error': 'Необходимо указать company и product'}), 400

    data = dashboard.get_price_data(company, product, start_date, end_date)
    return jsonify(data)

@app.route('/api/chart')
def api_chart():
    company = request.args.get('company')
    product = request.args.get('product')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if not company or not product:
        return jsonify({'error': 'Необходимо указать company и product'}), 400

    chart_json = dashboard.create_price_chart(company, product, start_date, end_date)
    if chart_json:
        return chart_json
    else:
        return jsonify({'error': 'Нет данных для построения графика'}), 404

@app.route('/api/export')
def export_csv():
    company = request.args.get('company')
    product = request.args.get('product')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    mask = pd.Series(True, index=dashboard.df.index)

    if company:
        mask &= (dashboard.df['company'] == company)
    if product:
        mask &= (dashboard.df['product'] == product)
    if start_date:
        mask &= (dashboard.df['date'] >= pd.to_datetime(start_date))
    if end_date:
        mask &= (dashboard.df['date'] <= pd.to_datetime(end_date))

    filtered = dashboard.df[mask].copy()
    filtered['date'] = filtered['date'].dt.strftime('%Y-%m-%d')

    buffer = io.StringIO()
    filtered.to_csv(buffer, index=False, encoding='utf-8')
    buffer.seek(0)

    filename = f"metal_prices_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return send_file(
        io.BytesIO(buffer.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/companies')
def api_companies():
    companies = dashboard.get_companies()
    return jsonify(companies)

@app.route('/api/stats')
def api_stats():
    total_records = len(dashboard.df)
    total_companies = dashboard.df['company'].nunique()
    total_products = dashboard.df['product'].nunique()
    date_range = f"{dashboard.df['date'].min().strftime('%Y-%m-%d')} - {dashboard.df['date'].max().strftime('%Y-%m-%d')}"

    return jsonify({
        'total_records': total_records,
        'total_companies': total_companies,
        'total_products': total_products,
        'date_range': date_range
    })

if __name__ == '__main__':
    if not os.path.exists(app.config['CSV_FILE']):
        print(f"❌ CSV файл не найден: {app.config['CSV_FILE']}")
        print("🚀 Запустите pipeline сначала: python main.py")
        sys.exit(1)

    print(f"✅ Flask приложение запускается с {dashboard.df['company'].nunique()} компаниями")
    print(f"📊 Доступно продуктов: {len(dashboard.get_products())}")
    app.run(debug=True, host='0.0.0.0', port=5000)