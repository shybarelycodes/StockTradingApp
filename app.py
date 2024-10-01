from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import yfinance as yf
import requests
import warnings
import json
warnings.filterwarnings("ignore", category=FutureWarning)

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'S0m3V3rYS3cur3&L0ngR@nd0mStr1ng!'  # dis the secure key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
bcrypt = Bcrypt(app)
db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(150), nullable=False)
    last_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    portfolios = db.relationship('Portfolio', backref='owner', lazy=True)

# Portfolio Model
class Portfolio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_symbol = db.Column(db.String(10), nullable=False)
    shares = db.Column(db.Integer, nullable=False)
    avg_price = db.Column(db.Float, nullable=False)

# Watchlist Model
class Watchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_symbol = db.Column(db.String(10), nullable=False)


# Trade Model
class Trade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_symbol = db.Column(db.String(10), nullable=False)
    trade_type = db.Column(db.String(4), nullable=False)  # 'BUY' or 'SELL'
    shares = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Create all tables
with app.app_context():
    db.create_all()


# Helper function to load cash balance from cash_balance.json
def load_cash_balance(user_id):
    try:
        with open('cash_balance.json', 'r') as f:
            cash_data = json.load(f)
        return cash_data.get(str(user_id), 20000)  # Default to 20,000 if no record found
    except FileNotFoundError:
        return 20000  # Default balance if file doesn't exist
    
# Helper function to save cash balance to cash_balance.json
def save_cash_balance(user_id, new_balance):
    try:
        with open('cash_balance.json', 'r') as f:
            cash_data = json.load(f)
    except FileNotFoundError:
        cash_data = {}

    cash_data[str(user_id)] = new_balance  # Update balance for the user
    with open('cash_balance.json', 'w') as f:
        json.dump(cash_data, f)

# Helper function: Calculate portfolio value for a user
def calculate_portfolio_value(user_id):
    portfolios = Portfolio.query.filter_by(user_id=user_id).all()
    total_value = 0
    for portfolio in portfolios:
        stock_price_info = get_real_time_stock_price(portfolio.stock_symbol)  # Fetch real-time stock price
        if stock_price_info:
            stock_value = portfolio.shares * stock_price_info['current_price']
            total_value += stock_value
    return total_value




# Helper function: Get leaderboard rankings
def get_leaderboard():
    users = User.query.all()
    user_portfolio_values = []

    for user in users:
        portfolio_value = calculate_portfolio_value(user.id)
        user_portfolio_values.append((user, portfolio_value))
    
    # Sort users by portfolio value in descending order
    sorted_users = sorted(user_portfolio_values, key=lambda x: x[1], reverse=True)
    
    return sorted_users

# Helper Function: Get Real-Time Stock Price from Yahoo Finance
def get_real_time_stock_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        stock_info = stock.history(period="1d", interval="1m")  # Fetch 1-minute interval data
        current_price = stock_info['Close'].iloc[-1]  # Get the latest close price
        previous_close = stock_info['Close'].iloc[-2] if len(stock_info) > 1 else current_price
        change_percent = round(((current_price - previous_close) / previous_close) * 100, 2)
        return {'current_price': current_price, 'change_percent': change_percent}
    except Exception as e:
        print(f"Error fetching real-time stock price for {ticker}: {e}")
        return None

# Helper Function: Get Market Trend Data (S&P 500 as an example)
def get_market_trends():
    try:
        sp500 = yf.Ticker('^GSPC')  # S&P 500 ticker symbol
        sp500_info = sp500.history(period="1d", interval="1m")  # Fetch 1-minute interval data
        current_price = sp500_info['Close'].iloc[-1]
        previous_close = sp500_info['Close'].iloc[-2] if len(sp500_info) > 1 else current_price
        change_percent = round(((current_price - previous_close) / previous_close) * 100, 2)
        
        return {
            'sp500_price': current_price,
            'sp500_change': change_percent
        }
    except Exception as e:
        print(f"Error fetching market trend data: {e}")
        return None

# Function to fetch finance news from NewsAPI
def get_finance_news():
    api_key = '155bbfb3ae3f4305b308d2f2f16bf5e1'  # NewsAPI key
    url = f'https://newsapi.org/v2/top-headlines?category=business&apiKey={api_key}'
    
    response = requests.get(url)
    data = response.json()
    
    # Get the top 2 headlines
    articles = data.get('articles', [])[:2]  # Fetching only 2 articles (notify me if u want more ig)
    news_list = [{'title': article['title'], 'description': article['description']} for article in articles]
    
    return news_list


def get_stock_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        stock_info = stock.history(period="1d")  # Fetches data for the last day
        print(stock_info)  # Print the stock info to check what is returned
        current_price = stock_info['Close'][0]
        previous_close = stock_info['Close'][-2] if len(stock_info) > 1 else current_price
        change_percent = round(((current_price - previous_close) / previous_close) * 100, 2)
        return {'current_price': current_price, 'change_percent': change_percent}
    except Exception as e:
        print(f"Error fetching stock price for {ticker}: {e}")
        return None

def get_stock_history(stock_symbol):
    try:
        stock = yf.Ticker(stock_symbol)
        # Fetch historical data without dividends
        stock_history = stock.history(period="1y", actions=False)  # Disable dividends and splits
        return stock_history['Close'].tolist()  # Return closing prices as a list
    except Exception as e:
        print(f"Error fetching stock history for {stock_symbol}: {e}")
        return []
    


# Fetch company profile and financial data
def get_company_profile(ticker):
    stock = yf.Ticker(ticker)
    # Fetch company info
    profile = stock.info
    financials = stock.financials
    balance_sheet = stock.balance_sheet
    cashflow = stock.cashflow
    
    company_profile = {
        'name': profile.get('longName'),
        'industry': profile.get('industry'),
        'sector': profile.get('sector'),
        'ceo': profile.get('ceo'),
        'employees': profile.get('fullTimeEmployees'),
        'market_cap': profile.get('marketCap'),
        'pe_ratio': profile.get('trailingPE'),
        'eps': profile.get('trailingEps'),
        'summary': profile.get('longBusinessSummary'),
    }

    return company_profile, financials, balance_sheet, cashflow
    

# Route: Login/Signup Page
@app.route('/login_signup')
def login_signup():
    return render_template('login_signup.html')

# Route: Sign-up Logic
@app.route('/signup', methods=['POST'])
def signup():
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']
    password = request.form['password']

    # Check if the email already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash('Email already registered. Please log in.', 'danger')
        return redirect(url_for('login_signup'))

    # Hash the password
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    # Add new user to the database
    new_user = User(first_name=first_name, last_name=last_name, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    flash('Registration successful! Please log in.', 'success')
    return redirect(url_for('login_signup'))

# Route: Login Logic
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    # Find the user by email
    user = User.query.filter_by(email=email).first()

    # Check if the user exists and verify password
    if user and bcrypt.check_password_hash(user.password, password):
        session['user_id'] = user.id  # Store the user ID in session
        flash('Login successful!', 'success')
        return redirect(url_for('dashboard'))  # Redirect to dashboard after login
    else:
        flash('Invalid email or password. Please try again.', 'danger')
        return redirect(url_for('login_signup'))  # Go back to login page if failed

@app.route('/trading')
def trading():
    return render_template('trading.html')

@app.route('/confirm_order', methods=['POST'])
def confirm_order():
    # Logic for confirming and executing the order goes here.
    # For now, we can redirect to the dashboard or show a success message.

    flash('Order confirmed!', 'success')
    return redirect(url_for('dashboard'))

# Route: Dashboard (combines portfolio and dashboard info)
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access the dashboard.', 'warning')
        return redirect(url_for('login_signup'))

    user_id = session['user_id']
    user = User.query.get(user_id)

    portfolios = Portfolio.query.filter_by(user_id=user_id).all()
    stock_history_data = {stock.stock_symbol: get_stock_history(stock.stock_symbol) for stock in portfolios}

    # Fetch watchlist items
    watchlist = Watchlist.query.filter_by(user_id=user_id).all()
    
    # Fetch stock prices for each watchlist item
    watchlist_data = []
    for item in watchlist:
        stock_info = get_real_time_stock_price(item.stock_symbol)
        if stock_info:
            watchlist_data.append({
                'stock_symbol': item.stock_symbol,
                'current_price': stock_info['current_price'],
                'change_percent': stock_info['change_percent']
            })

    portfolio_value = calculate_portfolio_value(user_id)
    leaderboard = get_leaderboard()
    total_users = len(leaderboard)
    ranking = next((i + 1 for i, entry in enumerate(leaderboard) if entry[0].id == user_id), total_users)
    news_list = get_finance_news()
    market_trends = get_market_trends()
    cash_balance = load_cash_balance(user_id)

    return render_template('dashboard.html', 
                           user=user, 
                           portfolios=portfolios, 
                           portfolio_value=portfolio_value, 
                           cash_balance=cash_balance,
                           ranking=ranking, 
                           total_users=total_users, 
                           news_list=news_list, 
                           leaderboard=leaderboard, 
                           market_trends=market_trends,
                           stock_history_data=stock_history_data,
                           watchlist=watchlist_data)
@app.route('/add_to_watchlist', methods=['POST'])
def add_to_watchlist():
    if 'user_id' not in session:
        flash('Please log in to add stocks to your watchlist.', 'danger')
        return redirect(url_for('login_signup'))

    stock_symbol = request.form['stock_symbol'].upper()
    
    # Fetch stock data to validate if the symbol is correct
    stock_info = get_real_time_stock_price(stock_symbol)
    if stock_info is None:
        flash('Invalid stock symbol. Please try again.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if the stock is already in the watchlist
    user_id = session['user_id']
    existing_stock = Watchlist.query.filter_by(user_id=user_id, stock_symbol=stock_symbol).first()
    
    if existing_stock:
        flash(f'{stock_symbol} is already in your watchlist.', 'info')
    else:
        # Add the stock to the watchlist
        new_watchlist_item = Watchlist(user_id=user_id, stock_symbol=stock_symbol)
        db.session.add(new_watchlist_item)
        db.session.commit()
        flash(f'{stock_symbol} has been added to your watchlist.', 'success')

    return redirect(url_for('dashboard'))

# Route: Buy Stock Logic
@app.route('/buy_stock', methods=['POST'])
def buy_stock():
    if 'user_id' not in session:
        flash('Please log in to buy stocks.', 'danger')
        return redirect(url_for('login_signup'))

    try:
        # Capture form data
        user_id = session['user_id']
        stock_symbol = request.form['stock_symbol'].upper()  # Stock symbol
        action = request.form['action']  # Buy or Sell
        quantity = int(request.form['quantity'])  # Number of shares
        order_type = request.form['order_type']  # Market, Limit, or Stop order
        duration = request.form['duration']  # Day or Good Till Cancelled

        # Validate input
        if not stock_symbol or not action or not quantity or not order_type or not duration:
            flash('Please fill in all fields correctly.', 'danger')
            return redirect(url_for('trading'))

        # Fetch stock data
        stock_info = get_real_time_stock_price(stock_symbol)
        if stock_info is None:
            flash(f'Invalid stock symbol: {stock_symbol}', 'danger')
            return redirect(url_for('trading'))

        # Execute trade
        price = stock_info['current_price']  # Assume this is returned by get_real_time_stock_price
        total_cost = price * quantity
        cash_balance = load_cash_balance(user_id)
        if action.lower() == 'buy':
            if total_cost > cash_balance:
                flash('Insufficient cash balance to buy stocks.', 'danger')
                return redirect(url_for('trading'))
            else:
                cash_balance -= total_cost
                flash(f'Successfully bought {quantity} shares of {stock_symbol}', 'success')
        elif action.lower() == 'sell':
            cash_balance += total_cost
            flash(f'Successfully sold {quantity} shares of {stock_symbol}', 'success')

        save_cash_balance(user_id, cash_balance)





        # Record the trade
        new_trade = Trade(user_id=user_id, stock_symbol=stock_symbol, trade_type=action.upper(),
                          shares=quantity, price=price)
        db.session.add(new_trade)

        # Update the portfolio
        portfolio = Portfolio.query.filter_by(user_id=user_id, stock_symbol=stock_symbol).first()
        if portfolio:
            total_shares = portfolio.shares + quantity if action.lower() == 'buy' else portfolio.shares - quantity
            portfolio.avg_price = (portfolio.shares * portfolio.avg_price + quantity * price) / total_shares
            portfolio.shares = total_shares
        else:
            new_portfolio = Portfolio(user_id=user_id, stock_symbol=stock_symbol, shares=quantity, avg_price=price)
            db.session.add(new_portfolio)

        db.session.commit()

        flash(f'Successfully executed {action} for {quantity} shares of {stock_symbol}', 'success')
        return redirect(url_for('portfolio'))

    except Exception as e:
        flash(f'Error while processing the order: {str(e)}', 'danger')
        return redirect(url_for('trading'))

@app.route('/portfolio')
def portfolio():
    if 'user_id' not in session:
        flash('Please log in to access your portfolio.', 'danger')
        return redirect(url_for('login_signup'))

    user_id = session['user_id']
    user = User.query.get(user_id)

    # Fetch portfolio data
    portfolios = Portfolio.query.filter_by(user_id=user_id).all()

    portfolio_value = 0  # Initialize portfolio value
    cash_balance = 20000  # Starting cash balance or fetched from user data

    # Initialize an empty dictionary for stock data
    stock_history_data = {}

    # Iterate over each stock in the portfolio and update the necessary data
    for stock in portfolios:
        stock_info = get_stock_price(stock.stock_symbol)  # Fetch real-time price info
        if stock_info:
            # Round the values to ensure better presentation
            stock.current_price = round(stock_info['current_price'], 2)  # Round to 2 decimal places
            stock.todays_change = round(stock_info['change_percent'], 2)  # Round to 2 decimal places
            stock.total_value = round(stock.shares * stock.current_price, 2)  # Calculate and round total value
            stock.total_gain = round(((stock.current_price - stock.avg_price) / stock.avg_price) * 100, 2)  # Calculate and round total gain
            portfolio_value += stock.total_value  # Add stock value to portfolio total

            # Add stock price history to the stock_history_data
            stock_history = get_stock_history(stock.stock_symbol)  # Fetch stock history
            stock_history_data[stock.stock_symbol] = stock_history  # Assuming this returns a list of prices
            cash_balance = load_cash_balance(user_id)

    # Ensure stock_history_data is not None or empty
    if not stock_history_data:
        stock_history_data = {}

    # Fetch leaderboard data
    leaderboard = get_leaderboard()
    total_users = len(leaderboard)

    # Find current user's ranking
    ranking = next((i + 1 for i, entry in enumerate(leaderboard) if entry[0].id == user_id), total_users)

    # Fetch trade history for the user
    trade_history = Trade.query.filter_by(user_id=user_id).order_by(Trade.timestamp.desc()).all()

    # Fetch market trends (if applicable)
    market_trends = get_market_trends()

    # Render the portfolio template and pass all necessary variables, including stock_history_data

    return render_template('portfolio.html', 
                           user=user, 
                           portfolios=portfolios, 
                           portfolio_value=portfolio_value, 
                           cash_balance=cash_balance,  # Pass cash balance here
                           ranking=ranking, 
                           total_users=total_users,
                           trade_history=trade_history,
                           market_trends=market_trends,
                           stock_history_data=stock_history_data)

@app.route('/leaderboard')
def leaderboard():
    # Get leaderboard data
    leaderboard_data = get_leaderboard()  # Assuming you already have the get_leaderboard() function
    
    return render_template('leaderboard.html', leaderboard=leaderboard_data)

@app.route('/research', methods=['GET'])
def research():
    ticker = request.args.get('ticker')
    
    # If no ticker is provided, redirect back to the dashboard
    if not ticker:
        flash('Please enter a stock symbol.', 'warning')
        return redirect(url_for('dashboard'))

    # Fetch the stock info
    try:
        stock = yf.Ticker(ticker)

        # Gather the necessary company data
        company_name = stock.info.get('longName', 'N/A')
        # Fetch other necessary information and prepare it for the template
        
        # Fetch stock price and history for chart
        stock_history = stock.history(period="1y")
        stock_dates = stock_history.index.strftime('%Y-%m-%d').tolist()
        stock_prices = stock_history['Close'].tolist()

        # Render the research template with data
        return render_template('research.html', 
                               company_name=company_name,
                               # Include other variables
                               stock_history={'dates': stock_dates, 'prices': stock_prices})
    except Exception as e:
        flash(f"Error fetching stock data for {ticker}: {str(e)}", 'danger')
        return redirect(url_for('dashboard'))


@app.route('/get_stock_suggestions', methods=['GET'])
def get_stock_suggestions():
    query = request.args.get('query', '').upper()

    # Example static list of stocks (this can be replaced with an API or database query)
    stocks = [
    {'symbol': 'AAPL', 'name': 'Apple Inc.'},
    {'symbol': 'AMZN', 'name': 'Amazon.com, Inc.'},
    {'symbol': 'GOOG', 'name': 'Alphabet Inc. - Class C'},
    {'symbol': 'GOOGL', 'name': 'Alphabet Inc. - Class A'},
    {'symbol': 'META', 'name': 'Meta Platforms, Inc.'},
    {'symbol': 'MSFT', 'name': 'Microsoft Corporation'},
    {'symbol': 'TSLA', 'name': 'Tesla, Inc.'},
    {'symbol': 'BRK.A', 'name': 'Berkshire Hathaway Inc. - Class A'},
    {'symbol': 'BRK.B', 'name': 'Berkshire Hathaway Inc. - Class B'},
    {'symbol': 'NVDA', 'name': 'NVIDIA Corporation'},
    {'symbol': 'JNJ', 'name': 'Johnson & Johnson'},
    {'symbol': 'V', 'name': 'Visa Inc.'},
    {'symbol': 'WMT', 'name': 'Walmart Inc.'},
    {'symbol': 'PG', 'name': 'Procter & Gamble Co.'},
    {'symbol': 'JPM', 'name': 'JPMorgan Chase & Co.'},
    {'symbol': 'UNH', 'name': 'UnitedHealth Group Incorporated'},
    {'symbol': 'HD', 'name': 'The Home Depot, Inc.'},
    {'symbol': 'MA', 'name': 'Mastercard Incorporated'},
    {'symbol': 'XOM', 'name': 'Exxon Mobil Corporation'},
    {'symbol': 'PFE', 'name': 'Pfizer Inc.'},
    {'symbol': 'VZ', 'name': 'Verizon Communications Inc.'},
    {'symbol': 'DIS', 'name': 'The Walt Disney Company'},
    {'symbol': 'NFLX', 'name': 'Netflix, Inc.'},
    {'symbol': 'KO', 'name': 'The Coca-Cola Company'},
    {'symbol': 'PEP', 'name': 'PepsiCo, Inc.'},
    {'symbol': 'CSCO', 'name': 'Cisco Systems, Inc.'},
    {'symbol': 'INTC', 'name': 'Intel Corporation'},
    {'symbol': 'BA', 'name': 'The Boeing Company'},
    {'symbol': 'MRK', 'name': 'Merck & Co., Inc.'},
    {'symbol': 'C', 'name': 'Citigroup Inc.'},
    {'symbol': 'T', 'name': 'AT&T Inc.'},
    {'symbol': 'BABA', 'name': 'Alibaba Group Holding Limited'},
    {'symbol': 'PYPL', 'name': 'PayPal Holdings, Inc.'},
    {'symbol': 'ORCL', 'name': 'Oracle Corporation'},
    {'symbol': 'ADBE', 'name': 'Adobe Inc.'},
    {'symbol': 'CRM', 'name': 'Salesforce, Inc.'},
    {'symbol': 'NKE', 'name': 'Nike, Inc.'},
    {'symbol': 'SPG', 'name': 'Simon Property Group, Inc.'},
    {'symbol': 'SBUX', 'name': 'Starbucks Corporation'},
    {'symbol': 'IBM', 'name': 'International Business Machines Corporation'},
    {'symbol': 'WFC', 'name': 'Wells Fargo & Company'},
    {'symbol': 'GS', 'name': 'The Goldman Sachs Group, Inc.'},
    {'symbol': 'CVX', 'name': 'Chevron Corporation'},
    {'symbol': 'MDT', 'name': 'Medtronic plc'},
    {'symbol': 'MCD', 'name': 'McDonald’s Corporation'},
    {'symbol': 'MO', 'name': 'Altria Group, Inc.'},
    {'symbol': 'AMGN', 'name': 'Amgen Inc.'},
    {'symbol': 'GILD', 'name': 'Gilead Sciences, Inc.'},
    {'symbol': 'LLY', 'name': 'Eli Lilly and Company'},
    {'symbol': 'UPS', 'name': 'United Parcel Service, Inc.'},
    {'symbol': 'FDX', 'name': 'FedEx Corporation'}
    ]

    # Filter stocks based on the query
    results = [stock for stock in stocks if stock['symbol'].startswith(query) or stock['name'].lower().startswith(query.lower())]
    
    return jsonify(results)

# Route to get stock details (price and change) for the selected stock symbol
@app.route('/get_stock_details', methods=['GET'])
def get_stock_details():
    symbol = request.args.get('symbol')
    stock = yf.Ticker(symbol)
    history = stock.history(period="1y")
    
    if history.empty:
        return jsonify({'error': 'Stock data not found'}), 404

    dates = history.index.strftime('%Y-%m-%d').tolist()
    prices = history['Close'].tolist()

    return jsonify({
        'company_name': stock.info.get('longName', 'N/A'),
        'price': stock.info.get('previousClose', 0),
        'change': stock.info.get('regularMarketChangePercent', 0),
        'dates': dates,
        'prices': prices
    })

# Route: Logout Logic
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login_signup'))

# Helper function: Get leaderboard rankings
def get_leaderboard():
    users = User.query.all()
    user_portfolio_values = []

    for user in users:
        portfolio_value = calculate_portfolio_value(user.id)
        user_portfolio_values.append((user, portfolio_value))
    
    # Sort users by portfolio value in descending order
    sorted_users = sorted(user_portfolio_values, key=lambda x: x[1], reverse=True)
    
    return sorted_users

# Run the app
if __name__ == '__main__':
    app.run(debug=True)