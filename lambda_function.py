import yfinance as yf
import json
import re

# Helper function to build a standardized HTTP response
def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",  # Allow cross-origin requests https://flowdevloping.github.io
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "GET, OPTIONS",  # Allow specific HTTP methods
        },
        "body": json.dumps(body),  # Convert the response body to JSON format
    }


def is_valid_symbol(symbol):
    if symbol=="":
        return False
    return bool(re.match(r"^[A-Z0-9.-]{1,10}$", symbol))

# Main entry point for the Lambda function
def lambda_handler(event, context):
    print(f"Received event: {event}")  # Log the incoming event for debugging
    path = event.get("path")  # Get the API path from the event
    query_params = event.get("queryStringParameters") or {}  # Extract query parameters, or use an empty dict
    stock_symbol = query_params.get('symbol')  # Get the stock symbol from the query parameters

    # Check if the stock symbol is provided; return error if not
    if not is_valid_symbol(stock_symbol):
        return build_response(400, {"error": "Invalid stock symbol"})

    print(f"Processing path: {path} for symbol: {stock_symbol}")  # Log the API path and stock symbol

    # Define the available routes and map them to specific functions
    ROUTES = {
        "/get_price_max": lambda: get_price_data(stock_symbol, "max", "1wk"),
        "/get_price_1y": lambda: get_price_data(stock_symbol, "1y", "1d"),
        "/get_price_3mo": lambda: get_price_data(stock_symbol, period="3mo", interval="1d"),
        "/get_price_1mo": lambda: get_price_data(stock_symbol, period="1mo", interval="1h"),
        "/get_price_5d": lambda: get_price_data(stock_symbol, period="5d", interval="60m"),
        "/get_price_1d": lambda: get_price_data(stock_symbol, period="1d", interval="1m"),
        "/get_price_live": lambda: get_price_live(stock_symbol),
    }

    # Get the handler for the requested path, if it exists
    route_handler = ROUTES.get(path)
    if route_handler:
        return route_handler()  # Execute the corresponding handler function
    else:
        # Return a 404 error if the path is not found
        return build_response(404, {"error": "Route not found"})
    

# Function to get ticker.info and ticker.history data
def fetch_data(stock_symbol, period, interval):
    ticker = yf.Ticker(stock_symbol)
    data = ticker.history(period=period, interval=interval)
    stock_name = ticker.info.get('longName', 'Unknown')
    if data.empty:
        return None, stock_name
    return data, stock_name


# Function to fetch historical price data for a stock
def get_price_data(stock_symbol, period, interval):
    try:
        print(f"Fetching data for {stock_symbol} with period {period} and interval {interval}")  # Log the request details
        data, stock_name = fetch_data(stock_symbol, period, interval)

        # If no data is found, return a 404 error
        if data.empty:
            return build_response(404, {"error": "No data found for the provided stock symbol."})
        
        response = []  # Initialize the response list
        timestamps = data['Close'].keys()  # Get timestamps for the closing prices

        # Loop through the data to build the response objects
        for i in range(0, len(data["Close"])):
            object = {  
                    'date': timestamps[i].strftime("%Y-%m-%d %H:%M:%S"),  # Format timestamp
                    'open': data.iloc[i]['Open'],  # Opening price
                    'high': data.iloc[i]['High'],  # Highest price
                    'low': data.iloc[i]['Low'],  # Lowest price
                    'close': data.iloc[i]['Close'],  # Closing price
                    'volume': data.iloc[i]['Volume'],  # Trade volume
                    'dividends': data.iloc[i].get('Dividends', 0),  # Dividends (default to 0 if not present)
                    'stock_splits': data.iloc[i].get('Stock Splits', 0),  # Stock splits (default to 0 if not present)
                    'name': stock_name,  # Stock name
                    }
            response.append(object)  # Append the object to the response list
        
        print(f"Data fetched successfully for {stock_symbol}")  # Log success
        return build_response(200, response)  # Return the response with HTTP 200 status
    except KeyError as e:
        print(f"Key error: {e}")
        return build_response(400, {"error": f"Missing data field: {e}"})
    except ValueError as e:
        print(f"Value error: {e}")
        return build_response(400, {"error": str(e)})
    except Exception as e:
        print(f"Unexpected error: {e}")
        return build_response(500, {"error": "Internal server error"})


# Function to fetch live (minute-level) price data for a stock
def get_price_live(stock_symbol):
    try:
        print(f"Fetching live data for {stock_symbol}")  # Log the request details
        data, stock_name = fetch_data(stock_symbol, period='1d', interval='1m')

        # If no data is found, return a 404 error
        if data.empty:
            return build_response(404, {"error": "No data found for the provided stock symbol."})

        response = []  # Initialize the response list
        timestamps = data['Close'].keys()  # Get timestamps for the closing prices

        # Create a response object for the latest data point
        object = {
                'date': timestamps[-1].strftime('%Y-%m-%d %H:%M:%S'),  # Format timestamp
                'open': data.iloc[-1]['Open'],  # Latest opening price
                'high': data.iloc[-1]['High'],  # Latest highest price
                'low': data.iloc[-1]['Low'],  # Latest lowest price
                'close': data.iloc[-1]['Close'],  # Latest closing price
                'volume': data.iloc[-1]['Volume'],  # Latest trade volume
                'dividends': data.iloc[-1].get('Dividends', 0),  # Latest dividends
                'stock_splits': data.iloc[-1].get('Stock Splits', 0),  # Latest stock splits
                'name': stock_name,  # Stock name
                }
        response.append(object)  # Append the object to the response list

        print(f"Live data fetched successfully for {stock_symbol}")  # Log success
        return build_response(200, response)  # Return the response with HTTP 200 status
    except Exception as e:
        # Log any exceptions and return a 500 error
        print(f"Error fetching live data for {stock_symbol}: {e}")
        return build_response(500, {"error": "Internal server error"})
