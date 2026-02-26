//+------------------------------------------------------------------+
//|                                          SimpleAIBot_EA.mq5      |
//|                        Copyright 2026, MetaTrader 5              |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026"
#property link      "https://www.mql5.com"
#property version   "1.00"

// Input parameters
input group "=== Risk Management ==="
input double   RiskPercent = 1.0;        // Risk per trade (%) - FTMO Conservative
input int      MaxPositions = 3;         // Max concurrent positions
input double   StopLossPips = 50;        // Stop Loss (pips)
input double   TakeProfitPips = 100;     // Take Profit (pips)

input group "=== JSON Export ==="
input string   JsonExportPath = "C:\\Users\\Claw\\.openclaw\\workspace\\mt5_trader\\live_ftmo_status.json";
input string   SymbolsToScan = "EURUSD,GBPUSD,USDJPY,EURJPY,GBPJPY,AUDJPY,EURGBP,XAUUSD";

input group "=== Trading Settings ==="
input int      MagicNumber = 234000;     // Magic Number
input int      Slippage = 10;            // Max slippage (points)
input bool     UseTrailingStop = true;   // Use Trailing Stop

input group "=== Strategy Settings ==="
input int      FastMAPeriod = 20;        // Fast MA Period
input int      SlowMAPeriod = 50;        // Slow MA Period
input int      RSIPeriod = 14;           // RSI Period
input int      RSIBuyLevel = 30;         // RSI Buy Level
input int      RSISellLevel = 70;        // RSI Sell Level

// Global variables
int fastMAHandle;
int slowMAHandle;
int rsiHandle;
int adxHandle;
int bbHandle;
datetime lastBarTime = 0;
datetime lastExportTime = 0;

// Symbol scanning array
string g_symbols[];

// Signal structure
struct Signal
{
   string symbol;
   string strategy;
   string signal;
   string strength;
   double entry;
   double sl;
   double tp;
};

// Position structure  
struct PositionInfo
{
   string symbol;
   string type;
   double profit;
};

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   // Initialize indicators
   fastMAHandle = iMA(_Symbol, PERIOD_M15, FastMAPeriod, 0, MODE_SMA, PRICE_CLOSE);
   slowMAHandle = iMA(_Symbol, PERIOD_M15, SlowMAPeriod, 0, MODE_SMA, PRICE_CLOSE);
   rsiHandle = iRSI(_Symbol, PERIOD_M15, RSIPeriod, PRICE_CLOSE);
   adxHandle = iADX(_Symbol, PERIOD_M15, 14);
   bbHandle = iBands(_Symbol, PERIOD_M15, 20, 0, 2, PRICE_CLOSE);
   
   if(fastMAHandle == INVALID_HANDLE || slowMAHandle == INVALID_HANDLE || 
      rsiHandle == INVALID_HANDLE || adxHandle == INVALID_HANDLE || bbHandle == INVALID_HANDLE)
   {
      Print("Error creating indicators");
      return(INIT_FAILED);
   }
   
   // Parse symbols string into array
   StringSplit(SymbolsToScan, ',', g_symbols);
   Print("Scanning symbols: ", ArraySize(g_symbols));
   
   Print("AI Bot initialized successfully (Low-Token Mode)");
   Print("Account Balance: ", AccountInfoDouble(ACCOUNT_BALANCE));
   Print("Account Equity: ", AccountInfoDouble(ACCOUNT_EQUITY));
   
   // Export initial signals
   ExportSignalsToJSON();
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(fastMAHandle);
   IndicatorRelease(slowMAHandle);
   IndicatorRelease(rsiHandle);
   IndicatorRelease(adxHandle);
   IndicatorRelease(bbHandle);
   Print("AI Bot stopped");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   datetime currentBarTime = iTime(_Symbol, PERIOD_M15, 0);
   
   // Only check on new bar
   if(currentBarTime == lastBarTime)
   {
      CheckTrailingStops();
      return;
   }
   
   lastBarTime = currentBarTime;
   
   // Export signals to JSON (Low-Token Mode - calculated in EA, not Python)
   ExportSignalsToJSON();
   
   // Check if we can open new positions
   if(CountOpenPositions() >= MaxPositions)
      return;
   
   // Get indicator values
   double fastMA[], slowMA[], rsi[];
   ArraySetAsSeries(fastMA, true);
   ArraySetAsSeries(slowMA, true);
   ArraySetAsSeries(rsi, true);
   
   if(CopyBuffer(fastMAHandle, 0, 0, 3, fastMA) < 3) return;
   if(CopyBuffer(slowMAHandle, 0, 0, 3, slowMA) < 3) return;
   if(CopyBuffer(rsiHandle, 0, 0, 2, rsi) < 2) return;
   
   double close = iClose(_Symbol, PERIOD_M15, 1);
   double prevClose = iClose(_Symbol, PERIOD_M15, 2);
   
   // Trading logic - Trend Following + RSI filter
   bool buySignal = (close > fastMA[1] && fastMA[1] > slowMA[1] && 
                     prevClose < fastMA[2] && rsi[0] < RSISellLevel && rsi[0] > RSIBuyLevel);
   
   bool sellSignal = (close < fastMA[1] && fastMA[1] < slowMA[1] && 
                      prevClose > fastMA[2] && rsi[0] > RSIBuyLevel && rsi[0] < RSISellLevel);
   
   if(buySignal && !HasOpenPosition(ORDER_TYPE_BUY))
   {
      OpenBuyOrder();
   }
   else if(sellSignal && !HasOpenPosition(ORDER_TYPE_SELL))
   {
      OpenSellOrder();
   }
}

//+------------------------------------------------------------------+
//| Open Buy Order                                                   |
//+------------------------------------------------------------------+
void OpenBuyOrder()
{
   double lotSize = CalculateLotSize(StopLossPips);
   double price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double sl = NormalizeDouble(price - StopLossPips * _Point, _Digits);
   double tp = NormalizeDouble(price + TakeProfitPips * _Point, _Digits);
   
   MqlTradeRequest request;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(result);
   
   request.action = TRADE_ACTION_DEAL;
   request.symbol = _Symbol;
   request.volume = lotSize;
   request.type = ORDER_TYPE_BUY;
   request.price = price;
   request.sl = sl;
   request.tp = tp;
   request.deviation = Slippage;
   request.magic = MagicNumber;
   request.comment = "AI Bot BUY";
   request.type_filling = GetFillingMode();
   
   if(!OrderSend(request, result))
   {
      Print("OrderSend error: ", GetLastError());
   }
   else
   {
      Print("Buy order opened: ", result.order, " Volume: ", lotSize);
   }
}

//+------------------------------------------------------------------+
//| Open Sell Order                                                  |
//+------------------------------------------------------------------+
void OpenSellOrder()
{
   double lotSize = CalculateLotSize(StopLossPips);
   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl = NormalizeDouble(price + StopLossPips * _Point, _Digits);
   double tp = NormalizeDouble(price - TakeProfitPips * _Point, _Digits);
   
   MqlTradeRequest request;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(result);
   
   request.action = TRADE_ACTION_DEAL;
   request.symbol = _Symbol;
   request.volume = lotSize;
   request.type = ORDER_TYPE_SELL;
   request.price = price;
   request.sl = sl;
   request.tp = tp;
   request.deviation = Slippage;
   request.magic = MagicNumber;
   request.comment = "AI Bot SELL";
   request.type_filling = GetFillingMode();
   
   if(!OrderSend(request, result))
   {
      Print("OrderSend error: ", GetLastError());
   }
   else
   {
      Print("Sell order opened: ", result.order, " Volume: ", lotSize);
   }
}

//+------------------------------------------------------------------+
//| Calculate Lot Size                                               |
//+------------------------------------------------------------------+
double CalculateLotSize(double stopLossPips)
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmount = balance * RiskPercent / 100;
   
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   
   if(tickSize == 0) return minLot;
   
   double lossPerLot = (stopLossPips * _Point / tickSize) * tickValue;
   if(lossPerLot == 0) return minLot;
   
   double lotSize = NormalizeDouble(riskAmount / lossPerLot, 2);
   
   // Apply constraints
   lotSize = MathMax(minLot, MathMin(maxLot, lotSize));
   lotSize = MathFloor(lotSize / lotStep) * lotStep;
   
   return lotSize;
}

//+------------------------------------------------------------------+
//| Count Open Positions                                             |
//+------------------------------------------------------------------+
int CountOpenPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) == MagicNumber)
         count++;
   }
   return count;
}

//+------------------------------------------------------------------+
//| Check if position type exists                                    |
//+------------------------------------------------------------------+
bool HasOpenPosition(ENUM_ORDER_TYPE type)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) == MagicNumber && 
         PositionGetInteger(POSITION_TYPE) == type)
         return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Check and apply trailing stops                                   |
//+------------------------------------------------------------------+
void CheckTrailingStops()
{
   if(!UseTrailingStop) return;
   
   double trailingStopPips = StopLossPips / 2;
   
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double currentSL = PositionGetDouble(POSITION_SL);
      double currentTP = PositionGetDouble(POSITION_TP);
      ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      
      double newSL = currentSL;
      
      if(posType == POSITION_TYPE_BUY)
      {
         double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         if(price > openPrice + trailingStopPips * _Point)
         {
            newSL = NormalizeDouble(price - trailingStopPips * _Point, _Digits);
            if(newSL > currentSL)
            {
               ModifyPosition(ticket, newSL, currentTP);
            }
         }
      }
      else if(posType == POSITION_TYPE_SELL)
      {
         double price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         if(price < openPrice - trailingStopPips * _Point)
         {
            newSL = NormalizeDouble(price + trailingStopPips * _Point, _Digits);
            if(newSL < currentSL || currentSL == 0)
            {
               ModifyPosition(ticket, newSL, currentTP);
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Modify position                                                  |
//+------------------------------------------------------------------+
void ModifyPosition(ulong ticket, double sl, double tp)
{
   MqlTradeRequest request;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(result);
   
   request.action = TRADE_ACTION_SLTP;
   request.position = ticket;
   request.symbol = _Symbol;
   request.sl = sl;
   request.tp = tp;
   
   if(!OrderSend(request, result))
   {
      Print("Modify position error: ", GetLastError());
   }
}

//+------------------------------------------------------------------+
//| Get Filling Mode                                                 |
//+------------------------------------------------------------------+
ENUM_ORDER_TYPE_FILLING GetFillingMode()
{
   uint filling = (uint)SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   
   if((filling & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK)
      return ORDER_FILLING_FOK;
   
   if((filling & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC)
      return ORDER_FILLING_IOC;
   
   return ORDER_FILLING_RETURN;
}

//+------------------------------------------------------------------+
//| Calculate RSI                                                    |
//+------------------------------------------------------------------+
double CalculateRSI(string symbol, int period)
{
   double rsi[];
   ArraySetAsSeries(rsi, true);
   int handle = iRSI(symbol, PERIOD_M15, period, PRICE_CLOSE);
   if(handle == INVALID_HANDLE) return 50.0;
   if(CopyBuffer(handle, 0, 0, 1, rsi) < 1) return 50.0;
   IndicatorRelease(handle);
   return rsi[0];
}

//+------------------------------------------------------------------+
//| Calculate MA                                                     |
//+------------------------------------------------------------------+
double CalculateMA(string symbol, int period)
{
   double ma[];
   ArraySetAsSeries(ma, true);
   int handle = iMA(symbol, PERIOD_M15, period, 0, MODE_SMA, PRICE_CLOSE);
   if(handle == INVALID_HANDLE) return 0.0;
   if(CopyBuffer(handle, 0, 0, 1, ma) < 1) return 0.0;
   IndicatorRelease(handle);
   return ma[0];
}

//+------------------------------------------------------------------+
//| Calculate ADX                                                    |
//+------------------------------------------------------------------+
double CalculateADX(string symbol)
{
   double adx[];
   ArraySetAsSeries(adx, true);
   int handle = iADX(symbol, PERIOD_M15, 14);
   if(handle == INVALID_HANDLE) return 25.0;
   if(CopyBuffer(handle, 0, 0, 1, adx) < 1) return 25.0;
   IndicatorRelease(handle);
   return adx[0];
}

//+------------------------------------------------------------------+
//| Calculate Bollinger Bands                                        |
//+------------------------------------------------------------------+
void CalculateBB(string symbol, double &upper, double &lower, double &middle)
{
   double upper_band[], lower_band[], middle_band[];
   ArraySetAsSeries(upper_band, true);
   ArraySetAsSeries(lower_band, true);
   ArraySetAsSeries(middle_band, true);
   
   int handle = iBands(symbol, PERIOD_M15, 20, 0, 2, PRICE_CLOSE);
   if(handle == INVALID_HANDLE) return;
   
   if(CopyBuffer(handle, 0, 0, 1, middle_band) < 1) return;
   if(CopyBuffer(handle, 1, 0, 1, upper_band) < 1) return;
   if(CopyBuffer(handle, 2, 0, 1, lower_band) < 1) return;
   
   middle = middle_band[0];
   upper = upper_band[0];
   lower = lower_band[0];
   
   IndicatorRelease(handle);
}

//+------------------------------------------------------------------+
//| Get SL/TP in price terms                                         |
//+------------------------------------------------------------------+
void GetSLTP(string symbol, double &sl_pips, double &tp_pips)
{
   if(symbol == "XAUUSD")
   {
      sl_pips = 5.0;
      tp_pips = 10.0;
   }
   else if(StringFind(symbol, "JPY") != -1)
   {
      sl_pips = 0.50;
      tp_pips = 1.00;
   }
   else
   {
      sl_pips = 0.0050;
      tp_pips = 0.0100;
   }
}

//+------------------------------------------------------------------+
//| Analyze TREND Strategy                                           |
//+------------------------------------------------------------------+
bool AnalyzeTrend(string symbol, Signal &signal)
{
   double ma20 = CalculateMA(symbol, 20);
   double ma50 = CalculateMA(symbol, 50);
   double rsi = CalculateRSI(symbol, 14);
   double close = iClose(symbol, PERIOD_M15, 1);
   double prevClose = iClose(symbol, PERIOD_M15, 2);
   
   if(ma20 == 0 || ma50 == 0) return false;
   
   double sl_pips, tp_pips;
   GetSLTP(symbol, sl_pips, tp_pips);
   
   // Trend + RSI filter
   if(close > ma20 && ma20 > ma50)
   {
      if(prevClose < CalculateMA(symbol, 20) && 30 < rsi && rsi < 70)
      {
         signal.symbol = symbol;
         signal.strategy = "TREND";
         signal.signal = "BUY";
         signal.strength = (rsi > 50) ? "STRONG" : "MODERATE";
         signal.entry = close;
         signal.sl = close - sl_pips;
         signal.tp = close + tp_pips;
         return true;
      }
   }
   else if(close < ma20 && ma20 < ma50)
   {
      if(prevClose > CalculateMA(symbol, 20) && 30 < rsi && rsi < 70)
      {
         signal.symbol = symbol;
         signal.strategy = "TREND";
         signal.signal = "SELL";
         signal.strength = (rsi < 50) ? "STRONG" : "MODERATE";
         signal.entry = close;
         signal.sl = close + sl_pips;
         signal.tp = close - tp_pips;
         return true;
      }
   }
   return false;
}

//+------------------------------------------------------------------+
//| Analyze RANGE Strategy                                           |
//+------------------------------------------------------------------+
bool AnalyzeRange(string symbol, Signal &signal)
{
   double adx = CalculateADX(symbol);
   if(adx > 25) return false;  // Trending market
   
   double close = iClose(symbol, PERIOD_M15, 1);
   double upper_bb, lower_bb, middle_bb;
   CalculateBB(symbol, upper_bb, lower_bb, middle_bb);
   
   // Get H1 range
   double range_high = iHigh(symbol, PERIOD_H1, iHighest(symbol, PERIOD_H1, MODE_HIGH, 24, 1));
   double range_low = iLow(symbol, PERIOD_H1, iLowest(symbol, PERIOD_H1, MODE_LOW, 24, 1));
   
   if(close <= lower_bb * 1.001)
   {
      signal.symbol = symbol;
      signal.strategy = "RANGE";
      signal.signal = "BUY";
      signal.strength = "RANGE_BOUNCE";
      signal.entry = close;
      signal.sl = range_low - 0.0010;
      signal.tp = (range_high + range_low) / 2;
      return true;
   }
   
   if(close >= upper_bb * 0.999)
   {
      signal.symbol = symbol;
      signal.strategy = "RANGE";
      signal.signal = "SELL";
      signal.strength = "RANGE_BOUNCE";
      signal.entry = close;
      signal.sl = range_high + 0.0010;
      signal.tp = (range_high + range_low) / 2;
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Analyze BREAKOUT Strategy                                        |
//+------------------------------------------------------------------+
bool AnalyzeBreakout(string symbol, Signal &signal)
{
   // Get recent range (6 candles ago to 1 candle ago)
   double recent_high = iHigh(symbol, PERIOD_H1, iHighest(symbol, PERIOD_H1, MODE_HIGH, 6, 1));
   double recent_low = iLow(symbol, PERIOD_H1, iLowest(symbol, PERIOD_H1, MODE_LOW, 6, 1));
   
   double close = iClose(symbol, PERIOD_H1, 1);
   double prev_volume = iVolume(symbol, PERIOD_H1, 1);
   
   // Simple volume average
   double avg_volume = 0;
   for(int i = 2; i < 8; i++)
      avg_volume += iVolume(symbol, PERIOD_H1, i);
   avg_volume /= 6;
   
   double breakout_threshold = 0.0002;
   double range = recent_high - recent_low;
   
   if(close > recent_high + breakout_threshold && prev_volume > avg_volume * 1.2)
   {
      signal.symbol = symbol;
      signal.strategy = "BREAKOUT";
      signal.signal = "BUY";
      signal.strength = "BREAKOUT";
      signal.entry = close;
      signal.sl = recent_low;
      signal.tp = close + range;
      return true;
   }
   
   if(close < recent_low - breakout_threshold && prev_volume > avg_volume * 1.2)
   {
      signal.symbol = symbol;
      signal.strategy = "BREAKOUT";
      signal.signal = "SELL";
      signal.strength = "BREAKOUT";
      signal.entry = close;
      signal.sl = recent_high;
      signal.tp = close - range;
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Get Current Positions for JSON                                   |
//+------------------------------------------------------------------+
void GetCurrentPositions(PositionInfo &positions[])
{
   int count = 0;
   for(int i = 0; i < PositionsTotal(); i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      
      ArrayResize(positions, count + 1);
      positions[count].symbol = PositionGetString(POSITION_SYMBOL);
      positions[count].type = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      positions[count].profit = PositionGetDouble(POSITION_PROFIT);
      count++;
   }
}

//+------------------------------------------------------------------+
//| Export Signals to JSON                                           |
//+------------------------------------------------------------------+
void ExportSignalsToJSON()
{
   string filename = JsonExportPath;
   int file = FileOpen(filename, FILE_WRITE|FILE_TXT|FILE_COMMON|FILE_SHARE_WRITE);
   if(file == INVALID_HANDLE)
   {
      // Try without FILE_SHARE_WRITE for older MT5
      file = FileOpen(filename, FILE_WRITE|FILE_TXT|FILE_COMMON);
   }
   if(file == INVALID_HANDLE)
   {
      Print("Cannot open file for writing: ", filename, " Error: ", GetLastError());
      return;
   }
   
   // Build JSON string
   string json = "{\n";
   
   // Timestamp
   datetime now = TimeCurrent();
   json += "  \"timestamp\": \"" + TimeToString(now, TIME_DATE|TIME_SECONDS) + "\",\n";
   
   // Account info
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   json += "  \"account\": {\"balance\": " + DoubleToString(balance, 2) + ", \"equity\": " + DoubleToString(equity, 2) + "},\n";
   
   // Signals array
   json += "  \"signals\": [\n";
   
   bool firstSignal = true;
   for(int i = 0; i < ArraySize(g_symbols); i++)
   {
      Signal sig;
      
      // Try each strategy
      if(AnalyzeTrend(g_symbols[i], sig))
      {
         if(!firstSignal) json += ",\n";
         firstSignal = false;
         json += "    {\"symbol\": \"" + sig.symbol + "\", \"strategy\": \"" + sig.strategy + "\", ";
         json += "\"signal\": \"" + sig.signal + "\", \"strength\": \"" + sig.strength + "\", ";
         json += "\"entry\": " + DoubleToString(sig.entry, 5) + ", ";
         json += "\"sl\": " + DoubleToString(sig.sl, 5) + ", ";
         json += "\"tp\": " + DoubleToString(sig.tp, 5) + "}";
      }
      else if(AnalyzeRange(g_symbols[i], sig))
      {
         if(!firstSignal) json += ",\n";
         firstSignal = false;
         json += "    {\"symbol\": \"" + sig.symbol + "\", \"strategy\": \"" + sig.strategy + "\", ";
         json += "\"signal\": \"" + sig.signal + "\", \"strength\": \"" + sig.strength + "\", ";
         json += "\"entry\": " + DoubleToString(sig.entry, 5) + ", ";
         json += "\"sl\": " + DoubleToString(sig.sl, 5) + ", ";
         json += "\"tp\": " + DoubleToString(sig.tp, 5) + "}";
      }
      else if(AnalyzeBreakout(g_symbols[i], sig))
      {
         if(!firstSignal) json += ",\n";
         firstSignal = false;
         json += "    {\"symbol\": \"" + sig.symbol + "\", \"strategy\": \"" + sig.strategy + "\", ";
         json += "\"signal\": \"" + sig.signal + "\", \"strength\": \"" + sig.strength + "\", ";
         json += "\"entry\": " + DoubleToString(sig.entry, 5) + ", ";
         json += "\"sl\": " + DoubleToString(sig.sl, 5) + ", ";
         json += "\"tp\": " + DoubleToString(sig.tp, 5) + "}";
      }
   }
   
   json += "\n  ],\n";
   
   // Positions array
   PositionInfo positions[];
   GetCurrentPositions(positions);
   
   json += "  \"positions\": [\n";
   for(int i = 0; i < ArraySize(positions); i++)
   {
      if(i > 0) json += ",\n";
      json += "    {\"symbol\": \"" + positions[i].symbol + "\", ";
      json += "\"type\": \"" + positions[i].type + "\", ";
      json += "\"profit\": " + DoubleToString(positions[i].profit, 2) + "}";
   }
   json += "\n  ]\n";
   
   json += "}";
   
   FileWriteString(file, json);
   FileClose(file);
   
   Print("Signals exported to: ", filename);
   lastExportTime = now;
}
//+------------------------------------------------------------------+
