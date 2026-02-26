class FeatureExtractor:
    """Extract ML features from market data"""
    
    @staticmethod
    def get_features(symbol):
        """Extract comprehensive features for ML"""
        try:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 50)
            if rates is None or len(rates) < 20:
                return None
            
            df = pd.DataFrame(rates)
            
            # Price action
            df['ema3'] = df['close'].ewm(span=3, adjust=False).mean()
            df['ema8'] = df['close'].ewm(span=8, adjust=False).mean()
            df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
            df['sma50'] = df['close'].rolling(window=50, min_periods=1).mean()
            
            # RSI - with min_periods
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
            rs = gain / (loss + 1e-10)
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # ATR
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = np.max(ranges, axis=1)
            df['atr'] = true_range.rolling(window=14, min_periods=1).mean()
            
            # ADX
            df['plus_dm'] = df['high'].diff()
            df['minus_dm'] = -df['low'].diff()
            df['plus_dm'] = df['plus_dm'].where((df['plus_dm'] > df['minus_dm']) & (df['plus_dm'] > 0), 0)
            df['minus_dm'] = df['minus_dm'].where((df['minus_dm'] > df['plus_dm']) & (df['minus_dm'] > 0), 0)
            df['adx'] = (df['plus_dm'].rolling(window=14, min_periods=1).mean() / (df['atr'].rolling(window=14, min_periods=1).mean() + 1e-10) * 100).rolling(window=14, min_periods=1).mean()
            
            # Bollinger
            df['bb_middle'] = df['close'].rolling(window=20, min_periods=1).mean()
            df['bb_std'] = df['close'].rolling(window=20, min_periods=1).std()
            df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
            df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
            df['bb_position'] = (df['close'] - df['bb_lower']) / ((df['bb_upper'] - df['bb_lower']) + 1e-10)
            
            # Volume
            df['volume_sma'] = df['tick_volume'].rolling(window=20, min_periods=1).mean()
            df['volume_sma'] = df['volume_sma'].replace(0, 1)
            df['volume_ratio'] = df['tick_volume'] / df['volume_sma']
            
            # Session
            current_hour = datetime.now(timezone.utc).hour
            if 0 <= current_hour < 8:
                session = "Asian"
            elif 8 <= current_hour < 13:
                session = "London"
            elif 13 <= current_hour < 17:
                session = "London_NY_Overlap"
            elif 17 <= current_hour < 22:
                session = "NY"
            else:
                session = "Off_Hours"
            
            latest = df.iloc[-1]
            
            return {
                'close': float(latest['close']),
                'ema3': float(latest['ema3']),
                'ema8': float(latest['ema8']),
                'ema21': float(latest['ema21']),
                'ema_spread': float(latest['ema3'] - latest['ema8']),
                'price_vs_ema21': float((latest['close'] - latest['ema21']) / latest['ema21'] * 100),
                'rsi': float(latest['rsi']),
                'adx': float(latest['adx']) if not pd.isna(latest['adx']) else 20.0,
                'atr': float(latest['atr']),
                'atr_percent': float(latest['atr'] / latest['close'] * 100),
                'bb_position': float(latest['bb_position']),
                'bb_width': float((latest['bb_upper'] - latest['bb_lower']) / latest['bb_middle'] * 100),
                'volume_ratio': float(latest['volume_ratio']),
                'session': session,
                'day_of_week': datetime.now().strftime('%A'),
                'hour': current_hour,
                'trend_5m': 'BULLISH' if latest['ema3'] > latest['ema8'] else 'BEARISH',
                'trend_15m': 'BULLISH' if latest['close'] > latest['ema21'] else 'BEARISH'
            }
        except Exception as e:
            print(f"[ERROR] Feature extraction failed for {symbol}: {e}")
            return None
