//+------------------------------------------------------------------+
//|                                      SimpleAIBot_EA_v2.mq5       |
//|                     Zev Orchestrated Trading System v2.0          |
//|                     Multi-Symbol | ATR-Based | Session-Aware      |
//+------------------------------------------------------------------+
#property copyright "Zev Trading Systems 2026"
#property version   "2.00"
#property description "Multi-symbol EA with session filter, ATR-based risk, correlation management, and detailed trade logging."

//+------------------------------------------------------------------+
//| INPUT PARAMETERS                                                  |
//+------------------------------------------------------------------+
input group "=== Risk Management ==="
input double   RiskPercent = 0.75;          // Risk per trade (%)
input int      MaxPositions = 3;            // Max concurrent positions
input double   MaxLotSize = 0.50;           // Max lot size per trade (hard cap)
input double   ATR_SL_Multiplier = 1.5;     // SL = ATR * this
input double   ATR_TP_Multiplier = 3.0;     // TP = ATR * this
input double   ATR_Trailing_Mult = 1.0;     // Trailing stop = ATR * this
input double   ATR_Breakeven_Mult = 1.0;    // Move SL to breakeven when profit >= ATR * this
input int      ATR_Period = 14;             // ATR period
input ENUM_TIMEFRAMES ATR_Timeframe = PERIOD_H1; // ATR timeframe

input group "=== Session Filter (GMT Hours) ==="
input int      SessionStartGMT = 7;        // Trading start (GMT) - London open
input int      SessionEndGMT = 21;          // Trading end (GMT) - NY close
input bool     UseSessionFilter = true;     // Enable session filter

input group "=== Strategy Settings ==="
input int      FastMAPeriod = 20;           // Fast MA Period
input int      SlowMAPeriod = 50;           // Slow MA Period
input int      RSIPeriod = 14;              // RSI Period
input double   MinConfidence = 65.0;        // Min confidence to trade (0-100)
input bool     UseTrendStrategy = true;     // Enable Trend strategy
input bool     UseRangeStrategy = true;     // Enable Range strategy
input bool     UseBreakoutStrategy = true;  // Enable Breakout strategy

input group "=== FTMO Settings ==="
input double   FTMO_MaxDailyLossPct = 4.0;  // Max daily loss % (FTMO=5, buffer=4)
input double   FTMO_MaxTotalLossPct = 8.0;  // Max total loss % (FTMO=10, buffer=8)
input double   FTMO_ProfitTarget = 10.0;    // Profit target %
input double   StartingBalance = 10000.0;   // Starting balance for FTMO tracking

input group "=== Symbols (comma-separated) ==="
input string   SymbolsList = "EURUSD,GBPUSD,USDJPY,USDCHF,AUDUSD,USDCAD,NZDUSD,EURGBP,EURJPY,GBPJPY,AUDJPY,EURAUD,GBPAUD,NZDJPY,XAUUSD";

input group "=== General ==="
input int      MagicNumber = 234000;        // Magic Number
input int      Slippage = 10;               // Max slippage (points)
input double   MaxSpreadPips = 3.0;         // Max spread to enter (pips)

//+------------------------------------------------------------------+
//| CONSTANTS & ENUMS                                                 |
//+------------------------------------------------------------------+
#define MAX_SYMBOLS 20
#define CORRELATION_GROUPS 6

enum ENUM_STRATEGY
{
   STRAT_TREND,
   STRAT_RANGE,
   STRAT_BREAKOUT,
   STRAT_NONE
};

enum ENUM_CORR_GROUP
{
   GROUP_EUR = 0,    // EURUSD, EURGBP, EURJPY, EURAUD
   GROUP_GBP = 1,    // GBPUSD, GBPJPY, GBPAUD
   GROUP_AUD = 2,    // AUDUSD, AUDJPY
   GROUP_USD = 3,    // USDJPY, USDCHF, USDCAD
   GROUP_NZD = 4,    // NZDUSD, NZDJPY
   GROUP_XAU = 5     // XAUUSD
};

//+------------------------------------------------------------------+
//| STRUCTURES                                                        |
//+------------------------------------------------------------------+
struct SymbolData
{
   string symbol;
   int    corrGroup;
   int    handleMA_Fast;
   int    handleMA_Slow;
   int    handleRSI;
   int    handleADX;
   int    handleBB;
   int    handleATR;
   datetime lastBarTime;
};

struct TradeSignal
{
   string         symbol;
   ENUM_STRATEGY  strategy;
   string         direction;   // "BUY" or "SELL"
   double         confidence;
   string         entryLogic;
   double         entryPrice;
   double         sl;
   double         tp;
   double         lotSize;
   double         atrValue;
   double         spread;
   string         session;
};

//+------------------------------------------------------------------+
//| LIVE CONFIG (overridden by ZevBot_Config.ini)                     |
//+------------------------------------------------------------------+
double   g_RiskPercent;
double   g_MaxLotSize;
int      g_MaxPositions;
bool     g_UseTrend;
bool     g_UseRange;
bool     g_UseBreakout;
double   g_MinConfidence;
double   g_HighConfThreshold;
int      g_SessionStartGMT;
int      g_SessionEndGMT;
bool     g_UseSessionFilter;
double   g_ATR_SL_Mult;
double   g_ATR_TP_Mult;
double   g_ATR_Trail_Mult;
double   g_ATR_BE_Mult;
double   g_FTMO_MaxDailyLoss;
double   g_FTMO_MaxTotalLoss;
double   g_StartingBalance;
bool     g_PairEnabled[MAX_SYMBOLS];
string   g_configFile = "ZevBot_Config.ini";
datetime g_lastConfigLoad = 0;

//+------------------------------------------------------------------+
//| GLOBAL VARIABLES                                                  |
//+------------------------------------------------------------------+
SymbolData g_symbols[];
int g_symbolCount = 0;
double g_dailyStartEquity = 0;
datetime g_dailyResetTime = 0;
int g_timerSeconds = 5;
string g_logFile = "ZevBot_TradeLog.csv";
string g_statusFile = "ZevBot_Status.json";
bool g_initialized = false;

//+------------------------------------------------------------------+
//| Expert initialization                                             |
//+------------------------------------------------------------------+
int OnInit()
{
   // Parse symbols
   string symbolParts[];
   g_symbolCount = StringSplit(SymbolsList, ',', symbolParts);
   if(g_symbolCount > MAX_SYMBOLS) g_symbolCount = MAX_SYMBOLS;
   
   ArrayResize(g_symbols, g_symbolCount);
   
   for(int i = 0; i < g_symbolCount; i++)
   {
      StringTrimLeft(symbolParts[i]);
      StringTrimRight(symbolParts[i]);
      g_symbols[i].symbol = symbolParts[i];
      g_symbols[i].corrGroup = GetCorrelationGroup(symbolParts[i]);
      g_symbols[i].lastBarTime = 0;
      
      // Create indicator handles for this symbol
      g_symbols[i].handleMA_Fast = iMA(symbolParts[i], PERIOD_M15, FastMAPeriod, 0, MODE_SMA, PRICE_CLOSE);
      g_symbols[i].handleMA_Slow = iMA(symbolParts[i], PERIOD_M15, SlowMAPeriod, 0, MODE_SMA, PRICE_CLOSE);
      g_symbols[i].handleRSI = iRSI(symbolParts[i], PERIOD_M15, RSIPeriod, PRICE_CLOSE);
      g_symbols[i].handleADX = iADX(symbolParts[i], PERIOD_M15, 14);
      g_symbols[i].handleBB = iBands(symbolParts[i], PERIOD_M15, 20, 0, 2, PRICE_CLOSE);
      g_symbols[i].handleATR = iATR(symbolParts[i], ATR_Timeframe, ATR_Period);
      
      if(g_symbols[i].handleMA_Fast == INVALID_HANDLE || 
         g_symbols[i].handleMA_Slow == INVALID_HANDLE ||
         g_symbols[i].handleRSI == INVALID_HANDLE ||
         g_symbols[i].handleADX == INVALID_HANDLE ||
         g_symbols[i].handleATR == INVALID_HANDLE)
      {
         PrintFormat("WARNING: Failed to create indicators for %s (may not be available on this server)", symbolParts[i]);
      }
      else
      {
         PrintFormat("Initialized: %s (Group %d)", symbolParts[i], g_symbols[i].corrGroup);
      }
   }
   
   // Initialize daily tracking
   g_dailyStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   g_dailyResetTime = GetDayStart();
   
   // Timer for periodic checks (trailing stops, status export)
   EventSetTimer(g_timerSeconds);
   
   // Write CSV header if file doesn't exist
   InitTradeLog();
   
   PrintFormat("=== Zev Trading System v2.0 - PROTECTION MODE ===");
   PrintFormat("Entry DISABLED - Python bot_controller.py handles entries");
   PrintFormat("EA manages trailing/breakeven on all positions");
   PrintFormat("Symbols: %d | MaxPos: %d | MinConfidence: %.0f%%", g_symbolCount, MaxPositions, MinConfidence);
   PrintFormat("ATR: SL=%.1fx TP=%.1fx Trail=%.1fx BE=%.1fx", ATR_SL_Multiplier, ATR_TP_Multiplier, ATR_Trailing_Mult, ATR_Breakeven_Mult);
   PrintFormat("Session: %02d:00-%02d:00 GMT | FTMO DailyMax: %.1f%% TotalMax: %.1f%%", SessionStartGMT, SessionEndGMT, FTMO_MaxDailyLossPct, FTMO_MaxTotalLossPct);
   PrintFormat("Balance: %.2f | Equity: %.2f", AccountInfoDouble(ACCOUNT_BALANCE), AccountInfoDouble(ACCOUNT_EQUITY));
   
   // Load dynamic config (overrides input parameters)
   LoadConfig();
   
   g_initialized = true;
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                           |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   
   for(int i = 0; i < g_symbolCount; i++)
   {
      if(g_symbols[i].handleMA_Fast != INVALID_HANDLE) IndicatorRelease(g_symbols[i].handleMA_Fast);
      if(g_symbols[i].handleMA_Slow != INVALID_HANDLE) IndicatorRelease(g_symbols[i].handleMA_Slow);
      if(g_symbols[i].handleRSI != INVALID_HANDLE) IndicatorRelease(g_symbols[i].handleRSI);
      if(g_symbols[i].handleADX != INVALID_HANDLE) IndicatorRelease(g_symbols[i].handleADX);
      if(g_symbols[i].handleBB != INVALID_HANDLE) IndicatorRelease(g_symbols[i].handleBB);
      if(g_symbols[i].handleATR != INVALID_HANDLE) IndicatorRelease(g_symbols[i].handleATR);
   }
   
   Print("Zev Trading System stopped. Reason: ", reason);
}

//+------------------------------------------------------------------+
//| Timer function — trailing stops + status export                   |
//+------------------------------------------------------------------+
void OnTimer()
{
   if(!g_initialized) return;
   
   // Reload config every 5 minutes
   if(TimeCurrent() - g_lastConfigLoad >= 300)
      LoadConfig();
   
   // Manage trailing stops and breakeven for ALL positions
   ManageAllPositions();
   
   // Daily equity reset check
   CheckDailyReset();
   
   // Export status (every 60 seconds effectively, timer fires every 5s)
   static datetime lastExport = 0;
   if(TimeCurrent() - lastExport >= 60)
   {
      ExportStatus();
      lastExport = TimeCurrent();
   }
}

//+------------------------------------------------------------------+
//| Tick function — signal scanning                                   |
//+------------------------------------------------------------------+
void OnTick()
{
   if(!g_initialized) return;
   
   // Check FTMO daily loss limit
   if(IsDailyLossLimitHit())
      return;
   
   // Check FTMO total loss limit
   if(IsTotalLossLimitHit())
      return;
   
   // Session filter
   if(g_UseSessionFilter && !IsWithinSession())
      return;
   
   // Position limit
   if(CountMyPositions() >= g_MaxPositions)
      return;
   
   // Scan each symbol for new bar signals
   for(int i = 0; i < g_symbolCount; i++)
   {
      // Check for new M15 bar on this symbol
      datetime barTime = iTime(g_symbols[i].symbol, PERIOD_M15, 0);
      if(barTime == 0 || barTime == g_symbols[i].lastBarTime)
         continue;
      
      g_symbols[i].lastBarTime = barTime;
      
      // Skip disabled pairs
      if(i < MAX_SYMBOLS && !g_PairEnabled[i])
         continue;
      
      // Skip if we already have a position on this symbol
      if(HasPositionOnSymbol(g_symbols[i].symbol))
         continue;
      
      // Skip if correlation group already has a position
      if(HasPositionInGroup(g_symbols[i].corrGroup))
         continue;
      
      // Re-check position limit (may have been filled while scanning)
      if(CountMyPositions() >= g_MaxPositions)
         break;
      
      // Check spread
      double spread = GetSpreadPips(g_symbols[i].symbol);
      if(spread > MaxSpreadPips)
         continue;
      
      // Get ATR for this symbol
      double atr = GetATR(i);
      if(atr <= 0) continue;
      
      // Try strategies in priority order: Trend > Breakout > Range
      TradeSignal signal;
      bool hasSignal = false;
      
      if(g_UseTrend && !hasSignal)
         hasSignal = AnalyzeTrendSignal(i, atr, spread, signal);
      
      if(g_UseBreakout && !hasSignal)
         hasSignal = AnalyzeBreakoutSignal(i, atr, spread, signal);
      
      if(g_UseRange && !hasSignal)
         hasSignal = AnalyzeRangeSignal(i, atr, spread, signal);
      
      // ENTRY DISABLED - Python v1 bot_controller.py handles entries
      // EA v2 = protection only (trailing/breakeven)
      // int openCount = CountMyPositions();
      // double requiredConfidence = (openCount >= 3) ? g_HighConfThreshold : g_MinConfidence;
      // if(hasSignal && signal.confidence >= requiredConfidence)
      // {
      //    ExecuteSignal(signal);
      // }
   }
}

//+------------------------------------------------------------------+
//| STRATEGY: Trend Following (MA Crossover + RSI + ADX)             |
//+------------------------------------------------------------------+
bool AnalyzeTrendSignal(int symIdx, double atr, double spread, TradeSignal &signal)
{
   string sym = g_symbols[symIdx].symbol;
   
   double fastMA[], slowMA[], rsi[], adx[];
   ArraySetAsSeries(fastMA, true);
   ArraySetAsSeries(slowMA, true);
   ArraySetAsSeries(rsi, true);
   ArraySetAsSeries(adx, true);
   
   if(CopyBuffer(g_symbols[symIdx].handleMA_Fast, 0, 0, 3, fastMA) < 3) return false;
   if(CopyBuffer(g_symbols[symIdx].handleMA_Slow, 0, 0, 3, slowMA) < 3) return false;
   if(CopyBuffer(g_symbols[symIdx].handleRSI, 0, 0, 2, rsi) < 2) return false;
   if(CopyBuffer(g_symbols[symIdx].handleADX, 0, 0, 2, adx) < 2) return false;
   
   double close1 = iClose(sym, PERIOD_M15, 1);
   double close2 = iClose(sym, PERIOD_M15, 2);
   if(close1 == 0 || close2 == 0) return false;
   
   // Check for BUY: price above both MAs, MAs aligned, price crossed above fast MA
   bool buySetup = (close1 > fastMA[1] && fastMA[1] > slowMA[1] && close2 < fastMA[2]);
   // Check for SELL: price below both MAs, MAs aligned, price crossed below fast MA
   bool sellSetup = (close1 < fastMA[1] && fastMA[1] < slowMA[1] && close2 > fastMA[2]);
   
   if(!buySetup && !sellSetup) return false;
   
   // RSI filter: must be in neutral zone (avoid overbought/oversold entries)
   if(rsi[0] < 25 || rsi[0] > 75) return false;
   
   // Build confidence score
   double confidence = 50.0;
   string logic = "";
   
   if(buySetup)
   {
      signal.direction = "BUY";
      logic = StringFormat("TREND BUY: MA%d(%.5f)>MA%d(%.5f), cross above, ", 
                           FastMAPeriod, fastMA[1], SlowMAPeriod, slowMA[1]);
      
      // RSI confirmation
      if(rsi[0] > 45 && rsi[0] < 65) { confidence += 10; logic += StringFormat("RSI=%.0f(confirm), ", rsi[0]); }
      else { logic += StringFormat("RSI=%.0f(neutral), ", rsi[0]); }
      
      // Momentum: close moving in trend direction
      if(close1 > close2) { confidence += 5; logic += "momentum+, "; }
   }
   else // sellSetup
   {
      signal.direction = "SELL";
      logic = StringFormat("TREND SELL: MA%d(%.5f)<MA%d(%.5f), cross below, ", 
                           FastMAPeriod, fastMA[1], SlowMAPeriod, slowMA[1]);
      
      if(rsi[0] > 35 && rsi[0] < 55) { confidence += 10; logic += StringFormat("RSI=%.0f(confirm), ", rsi[0]); }
      else { logic += StringFormat("RSI=%.0f(neutral), ", rsi[0]); }
      
      if(close1 < close2) { confidence += 5; logic += "momentum+, "; }
   }
   
   // ADX strength
   if(adx[0] > 25) { confidence += 15; logic += StringFormat("ADX=%.0f(strong), ", adx[0]); }
   else if(adx[0] > 20) { confidence += 5; logic += StringFormat("ADX=%.0f(moderate), ", adx[0]); }
   else { confidence -= 15; logic += StringFormat("ADX=%.0f(WEAK), ", adx[0]); }
   
   if(adx[0] > 40) { confidence += 5; logic += "veryStrong, "; }
   
   // ADX rising (trend strengthening)
   if(adx[0] > adx[1]) { confidence += 5; logic += "ADX rising, "; }
   
   // Session bonus
   string sess = GetCurrentSession();
   if(sess == "London" || sess == "Overlap") { confidence += 5; logic += "session=" + sess + ", "; }
   else { logic += "session=" + sess + ", "; }
   
   // Spread penalty
   if(spread > 2.0) { confidence -= 5; logic += StringFormat("highSpread=%.1f, ", spread); }
   
   // End of session penalty
   int gmtHour = GetGMTHour();
   if(gmtHour >= (g_SessionEndGMT - 2)) { confidence -= 10; logic += "endOfSession, "; }
   
   // Cap confidence
   confidence = MathMax(0, MathMin(100, confidence));
   
   // Calculate SL/TP based on ATR
   double point = SymbolInfoDouble(sym, SYMBOL_POINT);
   double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
   double bid = SymbolInfoDouble(sym, SYMBOL_BID);
   
   if(signal.direction == "BUY")
   {
      signal.entryPrice = ask;
      signal.sl = NormalizeDouble(ask - atr * g_ATR_SL_Mult, (int)SymbolInfoInteger(sym, SYMBOL_DIGITS));
      signal.tp = NormalizeDouble(ask + atr * g_ATR_TP_Mult, (int)SymbolInfoInteger(sym, SYMBOL_DIGITS));
   }
   else
   {
      signal.entryPrice = bid;
      signal.sl = NormalizeDouble(bid + atr * g_ATR_SL_Mult, (int)SymbolInfoInteger(sym, SYMBOL_DIGITS));
      signal.tp = NormalizeDouble(bid - atr * g_ATR_TP_Mult, (int)SymbolInfoInteger(sym, SYMBOL_DIGITS));
   }
   
   signal.symbol = sym;
   signal.strategy = STRAT_TREND;
   signal.confidence = confidence;
   signal.entryLogic = logic;
   signal.lotSize = CalculateLotSize(sym, atr * g_ATR_SL_Mult);
   signal.atrValue = atr;
   signal.spread = spread;
   signal.session = sess;
   
   return true;
}

//+------------------------------------------------------------------+
//| STRATEGY: Breakout                                                |
//+------------------------------------------------------------------+
bool AnalyzeBreakoutSignal(int symIdx, double atr, double spread, TradeSignal &signal)
{
   string sym = g_symbols[symIdx].symbol;
   
   // Recent H1 range (last 6 bars)
   double recentHigh = iHigh(sym, PERIOD_H1, iHighest(sym, PERIOD_H1, MODE_HIGH, 6, 1));
   double recentLow = iLow(sym, PERIOD_H1, iLowest(sym, PERIOD_H1, MODE_LOW, 6, 1));
   
   if(recentHigh == 0 || recentLow == 0) return false;
   
   double close = iClose(sym, PERIOD_H1, 1);
   if(close == 0) return false;
   
   double range = recentHigh - recentLow;
   
   // Breakout threshold: minimum 0.5 * ATR (not fixed pips!)
   double threshold = atr * 0.5;
   
   // Volume analysis
   long prevVol = iVolume(sym, PERIOD_H1, 1);
   long avgVol = 0;
   for(int i = 2; i < 8; i++) avgVol += iVolume(sym, PERIOD_H1, i);
   avgVol /= 6;
   
   bool buyBreakout = (close > recentHigh + threshold);
   bool sellBreakout = (close < recentLow - threshold);
   
   if(!buyBreakout && !sellBreakout) return false;
   
   double confidence = 50.0;
   string logic = "";
   
   double adx[];
   ArraySetAsSeries(adx, true);
   if(CopyBuffer(g_symbols[symIdx].handleADX, 0, 0, 2, adx) < 2) return false;
   
   if(buyBreakout)
   {
      signal.direction = "BUY";
      logic = StringFormat("BREAKOUT BUY: close(%.5f)>high(%.5f)+threshold(%.5f), ", close, recentHigh, threshold);
   }
   else
   {
      signal.direction = "SELL";
      logic = StringFormat("BREAKOUT SELL: close(%.5f)<low(%.5f)-threshold(%.5f), ", close, recentLow, threshold);
   }
   
   // Volume confirmation
   if(avgVol > 0 && prevVol > avgVol * 1.5) { confidence += 15; logic += "highVolume, "; }
   else if(avgVol > 0 && prevVol > avgVol * 1.2) { confidence += 8; logic += "aboveAvgVol, "; }
   else { confidence -= 5; logic += "lowVolume, "; }
   
   // ADX confirmation (trend developing)
   if(adx[0] > 25) { confidence += 10; logic += StringFormat("ADX=%.0f(strong), ", adx[0]); }
   else { confidence += 0; logic += StringFormat("ADX=%.0f, ", adx[0]); }
   
   // Clean break (> 1x ATR beyond range)
   double breakDistance = buyBreakout ? (close - recentHigh) : (recentLow - close);
   if(breakDistance > atr) { confidence += 10; logic += "cleanBreak(>1ATR), "; }
   
   // Session bonus
   string sess = GetCurrentSession();
   if(sess == "London" || sess == "Overlap") { confidence += 5; logic += "session=" + sess + ", "; }
   else { logic += "session=" + sess + ", "; }
   
   // Spread penalty
   if(spread > 2.0) { confidence -= 5; logic += StringFormat("spread=%.1f, ", spread); }
   
   confidence = MathMax(0, MathMin(100, confidence));
   
   double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
   double bid = SymbolInfoDouble(sym, SYMBOL_BID);
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   
   if(signal.direction == "BUY")
   {
      signal.entryPrice = ask;
      signal.sl = NormalizeDouble(ask - atr * g_ATR_SL_Mult, digits);
      signal.tp = NormalizeDouble(ask + atr * g_ATR_TP_Mult, digits);
   }
   else
   {
      signal.entryPrice = bid;
      signal.sl = NormalizeDouble(bid + atr * g_ATR_SL_Mult, digits);
      signal.tp = NormalizeDouble(bid - atr * g_ATR_TP_Mult, digits);
   }
   
   signal.symbol = sym;
   signal.strategy = STRAT_BREAKOUT;
   signal.confidence = confidence;
   signal.entryLogic = logic;
   signal.lotSize = CalculateLotSize(sym, atr * g_ATR_SL_Mult);
   signal.atrValue = atr;
   signal.spread = spread;
   signal.session = sess;
   
   return true;
}

//+------------------------------------------------------------------+
//| STRATEGY: Range (Bollinger Bounce + ADX filter)                  |
//+------------------------------------------------------------------+
bool AnalyzeRangeSignal(int symIdx, double atr, double spread, TradeSignal &signal)
{
   string sym = g_symbols[symIdx].symbol;
   
   double adx[];
   ArraySetAsSeries(adx, true);
   if(CopyBuffer(g_symbols[symIdx].handleADX, 0, 0, 2, adx) < 2) return false;
   
   // Only trade range when ADX confirms no trend
   if(adx[0] > 25) return false;
   
   double upperBB[], lowerBB[], middleBB[], rsi[];
   ArraySetAsSeries(upperBB, true);
   ArraySetAsSeries(lowerBB, true);
   ArraySetAsSeries(middleBB, true);
   ArraySetAsSeries(rsi, true);
   
   if(CopyBuffer(g_symbols[symIdx].handleBB, 0, 0, 2, middleBB) < 2) return false;
   if(CopyBuffer(g_symbols[symIdx].handleBB, 1, 0, 2, upperBB) < 2) return false;
   if(CopyBuffer(g_symbols[symIdx].handleBB, 2, 0, 2, lowerBB) < 2) return false;
   if(CopyBuffer(g_symbols[symIdx].handleRSI, 0, 0, 2, rsi) < 2) return false;
   
   double close = iClose(sym, PERIOD_M15, 1);
   if(close == 0) return false;
   
   bool buyBounce = (close <= lowerBB[1] * 1.001);   // Near lower BB
   bool sellBounce = (close >= upperBB[1] * 0.999);   // Near upper BB
   
   if(!buyBounce && !sellBounce) return false;
   
   double confidence = 50.0;
   string logic = "";
   
   if(buyBounce)
   {
      signal.direction = "BUY";
      logic = StringFormat("RANGE BUY: close(%.5f)<=lowerBB(%.5f), ", close, lowerBB[1]);
      
      // RSI oversold confirmation
      if(rsi[0] < 30) { confidence += 15; logic += StringFormat("RSI=%.0f(oversold), ", rsi[0]); }
      else if(rsi[0] < 40) { confidence += 5; logic += StringFormat("RSI=%.0f(lowish), ", rsi[0]); }
      else { logic += StringFormat("RSI=%.0f, ", rsi[0]); }
   }
   else
   {
      signal.direction = "SELL";
      logic = StringFormat("RANGE SELL: close(%.5f)>=upperBB(%.5f), ", close, upperBB[1]);
      
      if(rsi[0] > 70) { confidence += 15; logic += StringFormat("RSI=%.0f(overbought), ", rsi[0]); }
      else if(rsi[0] > 60) { confidence += 5; logic += StringFormat("RSI=%.0f(highish), ", rsi[0]); }
      else { logic += StringFormat("RSI=%.0f, ", rsi[0]); }
   }
   
   // ADX confirms ranging market
   if(adx[0] < 20) { confidence += 15; logic += StringFormat("ADX=%.0f(ranging), ", adx[0]); }
   else { confidence += 5; logic += StringFormat("ADX=%.0f(weakTrend), ", adx[0]); }
   
   // Session bonus
   string sess = GetCurrentSession();
   logic += "session=" + sess + ", ";
   
   // Spread penalty
   if(spread > 2.0) { confidence -= 5; logic += StringFormat("spread=%.1f, ", spread); }
   
   confidence = MathMax(0, MathMin(100, confidence));
   
   double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
   double bid = SymbolInfoDouble(sym, SYMBOL_BID);
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   
   // Range strategy: tighter SL/TP (use middle BB as TP target)
   if(signal.direction == "BUY")
   {
      signal.entryPrice = ask;
      signal.sl = NormalizeDouble(ask - atr * g_ATR_SL_Mult, digits);
      signal.tp = NormalizeDouble(middleBB[1], digits);  // Target: middle of range
   }
   else
   {
      signal.entryPrice = bid;
      signal.sl = NormalizeDouble(bid + atr * g_ATR_SL_Mult, digits);
      signal.tp = NormalizeDouble(middleBB[1], digits);  // Target: middle of range
   }
   
   signal.symbol = sym;
   signal.strategy = STRAT_RANGE;
   signal.confidence = confidence;
   signal.entryLogic = logic;
   signal.lotSize = CalculateLotSize(sym, atr * g_ATR_SL_Mult);
   signal.atrValue = atr;
   signal.spread = spread;
   signal.session = sess;
   
   return true;
}

//+------------------------------------------------------------------+
//| Execute trade signal                                              |
//+------------------------------------------------------------------+
void ExecuteSignal(TradeSignal &signal)
{
   MqlTradeRequest request;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(result);
   
   request.action = TRADE_ACTION_DEAL;
   request.symbol = signal.symbol;
   request.volume = signal.lotSize;
   request.type = (signal.direction == "BUY") ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   request.price = signal.entryPrice;
   request.sl = signal.sl;
   request.tp = signal.tp;
   request.deviation = Slippage;
   request.magic = MagicNumber;
   request.comment = StringFormat("Zev_%s_%.0f%%", StrategyToString(signal.strategy), signal.confidence);
   request.type_filling = GetFillingMode(signal.symbol);
   
   if(!OrderSend(request, result))
   {
      PrintFormat("ORDER FAILED: %s %s %s - Error: %d", signal.symbol, signal.direction, 
                  StrategyToString(signal.strategy), GetLastError());
      return;
   }
   
   PrintFormat("ORDER OK: %s %s %.2f lots | %s | Conf: %.0f%% | Ticket: %d", 
               signal.symbol, signal.direction, signal.lotSize, 
               StrategyToString(signal.strategy), signal.confidence, result.order);
   
   // Log to trade journal
   LogTradeOpen(signal, result.order);
}

//+------------------------------------------------------------------+
//| Manage all open positions (trailing + breakeven)                  |
//+------------------------------------------------------------------+
void ManageAllPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      
      string sym = PositionGetString(POSITION_SYMBOL);
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double currentSL = PositionGetDouble(POSITION_SL);
      double currentTP = PositionGetDouble(POSITION_TP);
      ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
      
      // Get ATR for this symbol
      double atr = GetATRBySymbol(sym);
      if(atr <= 0) continue;
      
      int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
      double bid = SymbolInfoDouble(sym, SYMBOL_BID);
      double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
      
      double newSL = currentSL;
      bool modified = false;
      
      if(posType == POSITION_TYPE_BUY)
      {
         double profit = bid - openPrice;
         
         // Breakeven: move SL to entry when profit >= ATR * breakeven multiplier
         if(profit >= atr * g_ATR_BE_Mult && currentSL < openPrice)
         {
            newSL = NormalizeDouble(openPrice + SymbolInfoDouble(sym, SYMBOL_POINT) * 2, digits);  // +2 points above entry
            modified = true;
         }
         
         // Trailing: if profit > ATR * trailing multiplier, trail at ATR * trailing distance
         if(profit >= atr * g_ATR_Trail_Mult)
         {
            double trailSL = NormalizeDouble(bid - atr * g_ATR_Trail_Mult, digits);
            if(trailSL > newSL)
            {
               newSL = trailSL;
               modified = true;
            }
         }
      }
      else // SELL
      {
         double profit = openPrice - ask;
         
         // Breakeven
         if(profit >= atr * g_ATR_BE_Mult && (currentSL > openPrice || currentSL == 0))
         {
            newSL = NormalizeDouble(openPrice - SymbolInfoDouble(sym, SYMBOL_POINT) * 2, digits);
            modified = true;
         }
         
         // Trailing
         if(profit >= atr * g_ATR_Trail_Mult)
         {
            double trailSL = NormalizeDouble(ask + atr * g_ATR_Trail_Mult, digits);
            if(trailSL < currentSL || currentSL == 0)
            {
               newSL = trailSL;
               modified = true;
            }
         }
      }
      
      if(modified && newSL != currentSL)
      {
         ModifyPosition(ticket, sym, newSL, currentTP);
      }
   }
}

//+------------------------------------------------------------------+
//| FTMO: Check daily loss limit                                      |
//+------------------------------------------------------------------+
bool IsDailyLossLimitHit()
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double dailyLoss = (g_dailyStartEquity - equity) / g_dailyStartEquity * 100.0;
   
   if(dailyLoss >= g_FTMO_MaxDailyLoss)
   {
      static datetime lastWarn = 0;
      if(TimeCurrent() - lastWarn > 300)
      {
         PrintFormat("FTMO DAILY LOSS LIMIT: %.2f%% (max %.1f%%) - TRADING PAUSED", dailyLoss, g_FTMO_MaxDailyLoss);
         lastWarn = TimeCurrent();
      }
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| FTMO: Check total loss limit                                      |
//+------------------------------------------------------------------+
bool IsTotalLossLimitHit()
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double totalLoss = (g_StartingBalance - equity) / g_StartingBalance * 100.0;
   
   if(totalLoss >= g_FTMO_MaxTotalLoss)
   {
      static datetime lastWarn2 = 0;
      if(TimeCurrent() - lastWarn2 > 300)
      {
         PrintFormat("FTMO TOTAL LOSS LIMIT: %.2f%% (max %.1f%%) - TRADING PAUSED", totalLoss, g_FTMO_MaxTotalLoss);
         lastWarn2 = TimeCurrent();
      }
      return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Check daily equity reset                                          |
//+------------------------------------------------------------------+
void CheckDailyReset()
{
   datetime dayStart = GetDayStart();
   if(dayStart != g_dailyResetTime)
   {
      g_dailyStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
      g_dailyResetTime = dayStart;
      PrintFormat("DAILY RESET: Starting equity = %.2f", g_dailyStartEquity);
   }
}

//+------------------------------------------------------------------+
//| UTILITY: Get correlation group for a symbol                       |
//+------------------------------------------------------------------+
int GetCorrelationGroup(string symbol)
{
   if(symbol == "EURUSD" || symbol == "EURGBP" || symbol == "EURJPY" || symbol == "EURAUD") return GROUP_EUR;
   if(symbol == "GBPUSD" || symbol == "GBPJPY" || symbol == "GBPAUD") return GROUP_GBP;
   if(symbol == "AUDUSD" || symbol == "AUDJPY") return GROUP_AUD;
   if(symbol == "USDJPY" || symbol == "USDCHF" || symbol == "USDCAD") return GROUP_USD;
   if(symbol == "NZDUSD" || symbol == "NZDJPY") return GROUP_NZD;
   if(symbol == "XAUUSD") return GROUP_XAU;
   return -1; // Unknown
}

//+------------------------------------------------------------------+
//| UTILITY: Check if position exists on symbol                       |
//+------------------------------------------------------------------+
bool HasPositionOnSymbol(string symbol)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) == MagicNumber && PositionGetString(POSITION_SYMBOL) == symbol)
         return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| UTILITY: Check if correlation group has a position                |
//+------------------------------------------------------------------+
bool HasPositionInGroup(int group)
{
   if(group < 0) return false;
   
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      
      string posSym = PositionGetString(POSITION_SYMBOL);
      if(GetCorrelationGroup(posSym) == group)
         return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| UTILITY: Count my positions                                       |
//+------------------------------------------------------------------+
int CountMyPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) == MagicNumber) count++;
   }
   return count;
}

//+------------------------------------------------------------------+
//| UTILITY: Calculate lot size based on risk                         |
//+------------------------------------------------------------------+
double CalculateLotSize(string symbol, double slDistance)
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmount = balance * g_RiskPercent / 100.0;
   
   double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double lotStep = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   double minLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   
   if(tickSize == 0 || tickValue == 0) return minLot;
   
   double lossPerLot = (slDistance / tickSize) * tickValue;
   if(lossPerLot == 0) return minLot;
   
   double lots = riskAmount / lossPerLot;
   lots = MathFloor(lots / lotStep) * lotStep;
   lots = MathMax(minLot, MathMin(maxLot, lots));
   
   // Hard cap on lot size (conservative mode)
   if(lots > g_MaxLotSize) lots = g_MaxLotSize;
   
   return NormalizeDouble(lots, 2);
}

//+------------------------------------------------------------------+
//| UTILITY: Get ATR value for symbol by index                        |
//+------------------------------------------------------------------+
double GetATR(int symIdx)
{
   double atrBuf[];
   ArraySetAsSeries(atrBuf, true);
   if(g_symbols[symIdx].handleATR == INVALID_HANDLE) return 0;
   if(CopyBuffer(g_symbols[symIdx].handleATR, 0, 0, 1, atrBuf) < 1) return 0;
   return atrBuf[0];
}

//+------------------------------------------------------------------+
//| UTILITY: Get ATR value by symbol name                             |
//+------------------------------------------------------------------+
double GetATRBySymbol(string symbol)
{
   for(int i = 0; i < g_symbolCount; i++)
   {
      if(g_symbols[i].symbol == symbol)
         return GetATR(i);
   }
   // Fallback: create temporary handle
   int handle = iATR(symbol, ATR_Timeframe, ATR_Period);
   if(handle == INVALID_HANDLE) return 0;
   double atrBuf[];
   ArraySetAsSeries(atrBuf, true);
   double result = 0;
   if(CopyBuffer(handle, 0, 0, 1, atrBuf) >= 1) result = atrBuf[0];
   IndicatorRelease(handle);
   return result;
}

//+------------------------------------------------------------------+
//| UTILITY: Get spread in pips                                       |
//+------------------------------------------------------------------+
double GetSpreadPips(string symbol)
{
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   
   double spreadPoints = (ask - bid) / point;
   
   // Convert to pips (1 pip = 10 points for 5-digit, 1 point for 3-digit JPY, etc.)
   if(digits == 5 || digits == 3) return spreadPoints / 10.0;
   if(digits == 2) return spreadPoints;  // XAUUSD
   return spreadPoints;
}

//+------------------------------------------------------------------+
//| UTILITY: Check session                                            |
//+------------------------------------------------------------------+
bool IsWithinSession()
{
   int gmtHour = GetGMTHour();
   return (gmtHour >= g_SessionStartGMT && gmtHour < g_SessionEndGMT);
}

//+------------------------------------------------------------------+
//| UTILITY: Get current session name                                 |
//+------------------------------------------------------------------+
string GetCurrentSession()
{
   int gmtHour = GetGMTHour();
   if(gmtHour >= 12 && gmtHour < 16) return "Overlap";
   if(gmtHour >= 7 && gmtHour < 16) return "London";
   if(gmtHour >= 12 && gmtHour < 21) return "NewYork";
   if(gmtHour >= 0 && gmtHour < 7) return "Asian";
   return "OffHours";
}

//+------------------------------------------------------------------+
//| UTILITY: Get GMT hour (handles broker time offset)                |
//+------------------------------------------------------------------+
int GetGMTHour()
{
   // MT5 TimeCurrent() returns broker time
   // FTMO typically uses EET (GMT+2 winter, GMT+3 summer)
   // Adjust as needed for your broker
   datetime brokerTime = TimeCurrent();
   MqlDateTime dt;
   TimeToStruct(brokerTime, dt);
   
   // FTMO offset: typically GMT+2 (winter) or GMT+3 (summer)
   // Safe default: assume broker = GMT+2
   int brokerGMTOffset = 2;
   int gmtHour = dt.hour - brokerGMTOffset;
   if(gmtHour < 0) gmtHour += 24;
   if(gmtHour >= 24) gmtHour -= 24;
   
   return gmtHour;
}

//+------------------------------------------------------------------+
//| UTILITY: Get start of current day                                 |
//+------------------------------------------------------------------+
datetime GetDayStart()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   dt.hour = 0;
   dt.min = 0;
   dt.sec = 0;
   return StructToTime(dt);
}

//+------------------------------------------------------------------+
//| UTILITY: Strategy enum to string                                  |
//+------------------------------------------------------------------+
string StrategyToString(ENUM_STRATEGY strat)
{
   switch(strat)
   {
      case STRAT_TREND: return "TREND";
      case STRAT_RANGE: return "RANGE";
      case STRAT_BREAKOUT: return "BREAKOUT";
      default: return "UNKNOWN";
   }
}

//+------------------------------------------------------------------+
//| UTILITY: Get filling mode for a symbol                            |
//+------------------------------------------------------------------+
ENUM_ORDER_TYPE_FILLING GetFillingMode(string symbol)
{
   uint filling = (uint)SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE);
   if((filling & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK) return ORDER_FILLING_FOK;
   if((filling & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC) return ORDER_FILLING_IOC;
   return ORDER_FILLING_RETURN;
}

//+------------------------------------------------------------------+
//| UTILITY: Modify position SL/TP                                    |
//+------------------------------------------------------------------+
void ModifyPosition(ulong ticket, string symbol, double sl, double tp)
{
   MqlTradeRequest request;
   MqlTradeResult result;
   ZeroMemory(request);
   ZeroMemory(result);
   
   request.action = TRADE_ACTION_SLTP;
   request.position = ticket;
   request.symbol = symbol;
   request.sl = sl;
   request.tp = tp;
   
   if(!OrderSend(request, result))
   {
      int err = GetLastError();
      if(err != 10025)  // Suppress "no changes" error
         PrintFormat("Modify error on %s ticket %d: %d", symbol, ticket, err);
   }
}

//+------------------------------------------------------------------+
//| LOGGING: Initialize trade log CSV                                 |
//+------------------------------------------------------------------+
void InitTradeLog()
{
   // Check if file exists
   int file = FileOpen(g_logFile, FILE_READ|FILE_TXT|FILE_COMMON);
   if(file != INVALID_HANDLE)
   {
      FileClose(file);
      return; // File exists, don't overwrite
   }
   
   // Create with header
   file = FileOpen(g_logFile, FILE_WRITE|FILE_TXT|FILE_COMMON);
   if(file == INVALID_HANDLE) return;
   
   string header = "timestamp,account,server,ticket,symbol,direction,strategy,confidence,lot_size,";
   header += "entry_price,sl,tp,atr,spread,session,entry_logic,";
   header += "exit_time,exit_price,exit_reason,pnl,pips,duration_min,observations";
   FileWriteString(file, header + "\n");
   FileClose(file);
   
   Print("Trade log initialized: ", g_logFile);
}

//+------------------------------------------------------------------+
//| LOGGING: Log trade open                                           |
//+------------------------------------------------------------------+
void LogTradeOpen(TradeSignal &signal, ulong ticket)
{
   int file = FileOpen(g_logFile, FILE_READ|FILE_WRITE|FILE_TXT|FILE_COMMON);
   if(file == INVALID_HANDLE) return;
   
   FileSeek(file, 0, SEEK_END);
   
   string account = IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN));
   string server = AccountInfoString(ACCOUNT_SERVER);
   string timestamp = TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS);
   
   // Clean entry logic (remove commas for CSV safety)
   string cleanLogic = signal.entryLogic;
   StringReplace(cleanLogic, ",", ";");
   
   string line = StringFormat("%s,%s,%s,%d,%s,%s,%s,%.1f,%.2f,%.5f,%.5f,%.5f,%.5f,%.1f,%s,%s,,,,,,,",
      timestamp, account, server, ticket,
      signal.symbol, signal.direction, StrategyToString(signal.strategy),
      signal.confidence, signal.lotSize,
      signal.entryPrice, signal.sl, signal.tp,
      signal.atrValue, signal.spread, signal.session,
      cleanLogic);
   
   FileWriteString(file, line + "\n");
   FileClose(file);
}

//+------------------------------------------------------------------+
//| LOGGING: Export current status to JSON                             |
//+------------------------------------------------------------------+
void ExportStatus()
{
   int file = FileOpen(g_statusFile, FILE_WRITE|FILE_TXT|FILE_COMMON);
   if(file == INVALID_HANDLE) return;
   
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double margin = AccountInfoDouble(ACCOUNT_MARGIN);
   double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   double floatingPL = AccountInfoDouble(ACCOUNT_PROFIT);
   long account = AccountInfoInteger(ACCOUNT_LOGIN);
   string server = AccountInfoString(ACCOUNT_SERVER);
   
   double profitPct = (balance - g_StartingBalance) / g_StartingBalance * 100.0;
   double dailyLoss = (g_dailyStartEquity > 0) ? (g_dailyStartEquity - equity) / g_dailyStartEquity * 100.0 : 0;
   
   string json = "{\n";
   json += StringFormat("  \"timestamp\": \"%s\",\n", TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS));
   json += StringFormat("  \"account\": %d,\n", account);
   json += StringFormat("  \"server\": \"%s\",\n", server);
   json += StringFormat("  \"balance\": %.2f,\n", balance);
   json += StringFormat("  \"equity\": %.2f,\n", equity);
   json += StringFormat("  \"margin\": %.2f,\n", margin);
   json += StringFormat("  \"free_margin\": %.2f,\n", freeMargin);
   json += StringFormat("  \"floating_pl\": %.2f,\n", floatingPL);
   json += StringFormat("  \"profit_pct\": %.2f,\n", profitPct);
   json += StringFormat("  \"daily_loss_pct\": %.2f,\n", dailyLoss);
   json += StringFormat("  \"starting_balance\": %.2f,\n", StartingBalance);
   json += StringFormat("  \"session_active\": %s,\n", (g_UseSessionFilter && IsWithinSession()) ? "true" : "false");
   json += StringFormat("  \"current_session\": \"%s\",\n", GetCurrentSession());
   
   // Positions
   json += "  \"positions\": [\n";
   int posCount = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      
      if(posCount > 0) json += ",\n";
      
      string sym = PositionGetString(POSITION_SYMBOL);
      string type = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      double openP = PositionGetDouble(POSITION_PRICE_OPEN);
      double curP = PositionGetDouble(POSITION_PRICE_CURRENT);
      double sl = PositionGetDouble(POSITION_SL);
      double tp = PositionGetDouble(POSITION_TP);
      double profit = PositionGetDouble(POSITION_PROFIT);
      double swap = PositionGetDouble(POSITION_SWAP);
      double vol = PositionGetDouble(POSITION_VOLUME);
      string comment = PositionGetString(POSITION_COMMENT);
      
      json += StringFormat("    {\"ticket\": %d, \"symbol\": \"%s\", \"type\": \"%s\", \"volume\": %.2f, ", 
                           ticket, sym, type, vol);
      json += StringFormat("\"open_price\": %.5f, \"current_price\": %.5f, \"sl\": %.5f, \"tp\": %.5f, ", 
                           openP, curP, sl, tp);
      json += StringFormat("\"profit\": %.2f, \"swap\": %.2f, \"comment\": \"%s\"}", profit, swap, comment);
      posCount++;
   }
   json += "\n  ],\n";
   json += StringFormat("  \"positions_count\": %d,\n", posCount);
   
   // FTMO limits
   json += "  \"ftmo\": {\n";
   json += StringFormat("    \"daily_loss_limit\": %.1f,\n", g_FTMO_MaxDailyLoss);
   json += StringFormat("    \"total_loss_limit\": %.1f,\n", g_FTMO_MaxTotalLoss);
   json += StringFormat("    \"profit_target\": %.1f,\n", FTMO_ProfitTarget);
   json += StringFormat("    \"daily_loss_current\": %.2f,\n", dailyLoss);
   json += StringFormat("    \"total_profit_current\": %.2f\n", profitPct);
   json += "  }\n";
   json += "}";
   
   FileWriteString(file, json);
   FileClose(file);
}

//+------------------------------------------------------------------+
//| CONFIG: Load dynamic config from INI file                         |
//+------------------------------------------------------------------+
void LoadConfig()
{
   g_lastConfigLoad = TimeCurrent();
   
   // Set defaults from input parameters first
   g_RiskPercent = RiskPercent;
   g_MaxLotSize = MaxLotSize;
   g_MaxPositions = MaxPositions;
   g_UseTrend = UseTrendStrategy;
   g_UseRange = UseRangeStrategy;
   g_UseBreakout = UseBreakoutStrategy;
   g_MinConfidence = MinConfidence;
   g_HighConfThreshold = 85.0;
   g_SessionStartGMT = SessionStartGMT;
   g_SessionEndGMT = SessionEndGMT;
   g_UseSessionFilter = UseSessionFilter;
   g_ATR_SL_Mult = ATR_SL_Multiplier;
   g_ATR_TP_Mult = ATR_TP_Multiplier;
   g_ATR_Trail_Mult = ATR_Trailing_Mult;
   g_ATR_BE_Mult = ATR_Breakeven_Mult;
   g_FTMO_MaxDailyLoss = FTMO_MaxDailyLossPct;
   g_FTMO_MaxTotalLoss = FTMO_MaxTotalLossPct;
   g_StartingBalance = StartingBalance;
   
   // Enable all pairs by default
   for(int i = 0; i < MAX_SYMBOLS; i++) g_PairEnabled[i] = true;
   
   // Try to read config file
   int file = FileOpen(g_configFile, FILE_READ|FILE_TXT|FILE_COMMON);
   if(file == INVALID_HANDLE)
   {
      if(g_lastConfigLoad == TimeCurrent()) // First load
         Print("CONFIG: No config file found, using input parameters");
      return;
   }
   
   string section = "";
   while(!FileIsEnding(file))
   {
      string line = FileReadString(file);
      StringTrimLeft(line);
      StringTrimRight(line);
      
      if(StringLen(line) == 0 || StringGetCharacter(line, 0) == ';')
         continue;
      
      // Section header
      if(StringGetCharacter(line, 0) == '[')
      {
         section = line;
         StringReplace(section, "[", "");
         StringReplace(section, "]", "");
         continue;
      }
      
      // Key=Value
      int eq = StringFind(line, "=");
      if(eq < 0) continue;
      
      string key = StringSubstr(line, 0, eq);
      string val = StringSubstr(line, eq + 1);
      StringTrimLeft(key); StringTrimRight(key);
      StringTrimLeft(val); StringTrimRight(val);
      
      // Parse values
      if(section == "Risk")
      {
         if(key == "RiskPercent") g_RiskPercent = StringToDouble(val);
         if(key == "MaxLotSize") g_MaxLotSize = StringToDouble(val);
         if(key == "MaxPositions") g_MaxPositions = (int)StringToInteger(val);
      }
      else if(section == "Strategy")
      {
         if(key == "UseTrend") g_UseTrend = (StringToInteger(val) != 0);
         if(key == "UseRange") g_UseRange = (StringToInteger(val) != 0);
         if(key == "UseBreakout") g_UseBreakout = (StringToInteger(val) != 0);
         if(key == "MinConfidence") g_MinConfidence = StringToDouble(val);
         if(key == "HighConfidenceThreshold") g_HighConfThreshold = StringToDouble(val);
      }
      else if(section == "Session")
      {
         if(key == "SessionStartGMT") g_SessionStartGMT = (int)StringToInteger(val);
         if(key == "SessionEndGMT") g_SessionEndGMT = (int)StringToInteger(val);
         if(key == "UseSessionFilter") g_UseSessionFilter = (StringToInteger(val) != 0);
      }
      else if(section == "ATR")
      {
         if(key == "SL_Multiplier") g_ATR_SL_Mult = StringToDouble(val);
         if(key == "TP_Multiplier") g_ATR_TP_Mult = StringToDouble(val);
         if(key == "Trailing_Multiplier") g_ATR_Trail_Mult = StringToDouble(val);
         if(key == "Breakeven_Multiplier") g_ATR_BE_Mult = StringToDouble(val);
      }
      else if(section == "FTMO")
      {
         if(key == "MaxDailyLossPct") g_FTMO_MaxDailyLoss = StringToDouble(val);
         if(key == "MaxTotalLossPct") g_FTMO_MaxTotalLoss = StringToDouble(val);
         if(key == "StartingBalance") g_StartingBalance = StringToDouble(val);
      }
      else if(section == "Pairs")
      {
         bool enabled = (StringToInteger(val) != 0);
         for(int i = 0; i < g_symbolCount; i++)
         {
            if(g_symbols[i].symbol == key)
            {
               g_PairEnabled[i] = enabled;
               break;
            }
         }
      }
   }
   
   FileClose(file);
   PrintFormat("CONFIG LOADED: Risk=%.2f%% MaxLot=%.2f MaxPos=%d Conf>=%.0f%% Session=%02d-%02d",
               g_RiskPercent, g_MaxLotSize, g_MaxPositions, g_MinConfidence, g_SessionStartGMT, g_SessionEndGMT);
}

//+------------------------------------------------------------------+
//| CONFIG: Get risk percent (used by CalculateLotSize)               |
//+------------------------------------------------------------------+
double GetRiskPercent() { return g_RiskPercent; }
double GetMaxLotSize() { return g_MaxLotSize; }
//+------------------------------------------------------------------+
