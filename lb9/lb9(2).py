from typing import List
from pydantic import BaseModel, validator, constr, Field
import logging
import requests
from datetime import datetime, timedelta
import pandas as pd
import mplfinance as mpf

class PairModel(BaseModel):
    symbol: constr(min_length=6, max_length=6) = Field(..., description="The trading pair symbol")
    base_asset: constr(max_length=10) = Field(..., description="The base asset of the trading pair")
    quote_asset: constr(max_length=10) = Field(..., description="The quote asset of the trading pair")
    
    @validator('symbol')
    def validate_symbol_length(cls, v):
        if len(v) != 6:
            raise ValueError('Symbol length must be 6 characters')
        return v
    
    @validator('base_asset', 'quote_asset')
    def validate_asset_case(cls, v):
        if not v.isupper():
            raise ValueError('Asset symbols must be uppercase')
        return v
    
    @validator('symbol')
    def validate_symbol_format(cls, v):
        if not v.isalnum():
            raise ValueError('Symbol must contain only alphanumeric characters')
        return v
    
    class Config:
        allow_mutation = False
        
    class Meta:
        arbitrary_types_allowed = True
        json_encoders = {
            bytes: lambda v: v.decode(),
            bytearray: lambda v: v.decode(),
        }
    
    class PairModelConfig:
        min_length = 3
        max_length = 10
        anystr_strip_whitespace = True

    class SymbolConfig:
        min_length = 6
        max_length = 6

class HistoricalData(BaseModel):
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: int
    quote_asset_volume: float
    num_trades: int
    taker_buy_base_asset_volume: float
    taker_buy_quote_asset_volume: float
    ignore: float

class CustomFormatter(logging.Formatter):
    def format(self, record):
        record.msg = "CUSTOM: " + record.msg
        return super().format(record)

baseloader_logger = logging.getLogger('baseloader')
binanceloader_logger = logging.getLogger('binanceloader')

formatter = CustomFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

file_handler = logging.FileHandler('logfile.log')
file_handler.setFormatter(formatter)

baseloader_logger.addHandler(console_handler)
baseloader_logger.addHandler(file_handler)
binanceloader_logger.addHandler(console_handler)
binanceloader_logger.addHandler(file_handler)

baseloader_logger.setLevel(logging.INFO)
binanceloader_logger.setLevel(logging.INFO)

def get_pairs() -> List[PairModel]:
    url = 'https://api.binance.com/api/v3/exchangeInfo'
    response = requests.get(url)
    data = response.json()
    pairs = []
    for pair_data in data['symbols']:
        pairs.append(PairModel(symbol=pair_data['symbol'], base_asset=pair_data['baseAsset'], quote_asset=pair_data['quoteAsset']))
    return pairs

def get_historical_data(symbol: str, interval: str, start_time: int, end_time: int) -> List[HistoricalData]:
    base_url = 'https://api.binance.com/api/v1/klines'
    params = {
        'symbol': symbol,
        'interval': interval,
        'startTime': start_time,
        'endTime': end_time
    }
    response = requests.get(base_url, params=params)
    data = response.json()
    historical_data = []
    for candle in data:
        historical_data.append(HistoricalData(
            open_time=candle[0],
            open=float(candle[1]),
            high=float(candle[2]),
            low=float(candle[3]),
            close=float(candle[4]),
            volume=float(candle[5]),
            close_time=candle[6],
            quote_asset_volume=float(candle[7]),
            num_trades=candle[8],
            taker_buy_base_asset_volume=float(candle[9]),
            taker_buy_quote_asset_volume=float(candle[10]),
            ignore=float(candle[11])
        ))
    return historical_data

def get_products():
    url = 'https://api.binance.com/api/v3/exchangeInfo'
    response = requests.get(url)
    data = response.json()
    products = [product['symbol'] for product in data['symbols']]
    products_df = pd.DataFrame(products, columns=['Product'])
    return products_df

def plot_candlestick(data, title):
    mpf.plot(data, type='line', style='charles', volume=True, ylabel='Price', ylabel_lower='Volume', title=title, show_nontrading=True)

print("Список доступних продуктів:")
products_df = get_products()
print(products_df)

selected_products = ['BTCUSDT', 'ETHUSDT', 'LTCUSDT']

interval = '1d'  # щоденно
end_time = datetime.now()
start_time_day = end_time - timedelta(days=1)
start_time_month = end_time - timedelta(days=30)
start_time_year = end_time - timedelta(days=365)

for product in selected_products:
    print(f"\nІсторичні дані для продукту {product}:")
    
    print("\nЗа останній день:")
    historical_data_day = get_historical_data(product, interval, int(start_time_day.timestamp())*1000, int(end_time.timestamp())*1000)
    historical_data_day_df = pd.DataFrame([candle.dict() for candle in historical_data_day])  # Перетворюємо на DataFrame
    historical_data_day_df.index = pd.to_datetime(historical_data_day_df['open_time'], unit='ms')  # Перетворюємо індекс у тип DatetimeIndex
    print(historical_data_day_df)
    
    print("\nЗа останній місяць:")
    historical_data_month = get_historical_data(product, interval, int(start_time_month.timestamp())*1000, int(end_time.timestamp())*1000)
    historical_data_month_df = pd.DataFrame([candle.dict() for candle in historical_data_month])  # Перетворюємо на DataFrame
    historical_data_month_df.index = pd.to_datetime(historical_data_month_df['open_time'], unit='ms')  # Перетворюємо індекс у тип DatetimeIndex
    print(historical_data_month_df)
    
    print("\nЗа останній рік:")
    historical_data_year = get_historical_data(product, interval, int(start_time_year.timestamp())*1000, int(end_time.timestamp())*1000)
    historical_data_year_df = pd.DataFrame([candle.dict() for candle in historical_data_year])  # Перетворюємо на DataFrame
    historical_data_year_df.index = pd.to_datetime(historical_data_year_df['open_time'], unit='ms')  # Перетворюємо індекс у тип DatetimeIndex
    print(historical_data_year_df)
    
    print(f"\nГрафіки для продукту {product}:")
    
    print("\nГрафік за останній день:")
    plot_candlestick(historical_data_day_df, f"{product} - Last Day")
    
    print("\nГрафік за останній місяць:")
    plot_candlestick(historical_data_month_df, f"{product} - Last Month")
    
    print("\nГрафік за останній рік:")
    plot_candlestick(historical_data_year_df, f"{product} - Last Year")
