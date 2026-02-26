//+------------------------------------------------------------------+
//|                                     FTMO_Status_Exporter.mq5       |
//|  Export account status to JSON for Zev monitoring                  |
//+------------------------------------------------------------------+
#property copyright "Zev AI Trading"
#property version   "1.00"
#property strict

input string   StatusFilePath = "C:\\Users\\Claw\\.openclaw\\workspace\\mt5_trader\\live_ftmo_status.json";
input int      ExportIntervalSeconds = 30;  // How often to export

string         g_lastStatus = "";
datetime       g_lastExport = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   Print("FTMO Status Exporter initialized");
   Print("Export path: ", StatusFilePath);
   ExportStatus();  // Export immediately on start
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("FTMO Status Exporter stopped");
}

//+------------------------------------------------------------------+
void OnTick()
{
   datetime now = TimeLocal();
   if(now - g_lastExport >= ExportIntervalSeconds)
   {
      ExportStatus();
      g_lastExport = now;
   }
}

//+------------------------------------------------------------------+
void ExportStatus()
{
   if(!AccountInfoInteger(ACCOUNT_TRADE_ALLOWED))
   {
      Print("Trading not allowed on this account");
      return;
   }
   
   int file = FileOpen(StatusFilePath, FILE_WRITE|FILE_TXT|FILE_COMMON);
   if(file == INVALID_HANDLE)
   {
      // Try without FILE_COMMON
      file = FileOpen(StatusFilePath, FILE_WRITE|FILE_TXT);
   }
   if(file == INVALID_HANDLE)
   {
      Print("Cannot open status file: ", StatusFilePath, " Error: ", GetLastError());
      return;
   }
   
   // Build JSON
   string json = "{\n";
   
   // Timestamp
   json += "  \"timestamp\": \"" + TimeToString(TimeLocal(), TIME_DATE|TIME_SECONDS) + "\",\n";
   
   // Account info
   long login = AccountInfoInteger(ACCOUNT_LOGIN);
   string server = AccountInfoString(ACCOUNT_SERVER);
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double margin = AccountInfoDouble(ACCOUNT_MARGIN);
   double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   string currency = AccountInfoString(ACCOUNT_CURRENCY);
   
   json += "  \"account\": " + IntegerToString(login) + ",\n";
   json += "  \"server\": \"" + server + "\",\n";
   json += "  \"balance\": " + DoubleToString(balance, 2) + ",\n";
   json += "  \"equity\": " + DoubleToString(equity, 2) + ",\n";
   json += "  \"margin\": " + DoubleToString(margin, 2) + ",\n";
   json += "  \"free_margin\": " + DoubleToString(freeMargin, 2) + ",\n";
   json += "  \"currency\": \"" + currency + "\",\n";
   
   // Positions
   int posCount = PositionsTotal();
   json += "  \"position_count\": " + IntegerToString(posCount) + ",\n";
   json += "  \"positions\": [\n";
   
   for(int i = 0; i < posCount; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket <= 0) continue;
      
      string symbol = PositionGetString(POSITION_SYMBOL);
      string type = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      double volume = PositionGetDouble(POSITION_VOLUME);
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double currentPrice = PositionGetDouble(POSITION_PRICE_CURRENT);
      double sl = PositionGetDouble(POSITION_SL);
      double tp = PositionGetDouble(POSITION_TP);
      double profit = PositionGetDouble(POSITION_PROFIT);
      
      if(i > 0) json += ",\n";
      json += "    {\n";
      json += "      \"ticket\": " + IntegerToString((int)ticket) + ",\n";
      json += "      \"symbol\": \"" + symbol + "\",\n";
      json += "      \"type\": \"" + type + "\",\n";
      json += "      \"volume\": " + DoubleToString(volume, 2) + ",\n";
      json += "      \"open_price\": " + DoubleToString(openPrice, 5) + ",\n";
      json += "      \"current_price\": " + DoubleToString(currentPrice, 5) + ",\n";
      json += "      \"sl\": " + DoubleToString(sl, 5) + ",\n";
      json += "      \"tp\": " + DoubleToString(tp, 5) + ",\n";
      json += "      \"profit\": " + DoubleToString(profit, 2) + "\n";
      json += "    }";
   }
   
   json += "\n  ],\n";
   
   // Orders (pending)
   int ordCount = OrdersTotal();
   json += "  \"order_count\": " + IntegerToString(ordCount) + ",\n";
   json += "  \"orders\": [\n";
   
   for(int i = 0; i < ordCount; i++)
   {
      ulong ticket = OrderGetTicket(i);
      if(ticket <= 0) continue;
      
      string symbol = OrderGetString(ORDER_SYMBOL);
      string type = OrderTypeToString((ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE));
      double volume = OrderGetDouble(ORDER_VOLUME_CURRENT);
      double price = OrderGetDouble(ORDER_PRICE_OPEN);
      
      if(i > 0) json += ",\n";
      json += "    {\"ticket\": " + IntegerToString((int)ticket) + ", \"symbol\": \"" + symbol + "\", \"type\": \"" + type + "\", \"volume\": " + DoubleToString(volume, 2) + ", \"price\": " + DoubleToString(price, 5) + "}";
   }
   
   json += "\n  ]\n";
   json += "}\n";
   
   FileWriteString(file, json);
   FileClose(file);
   
   Print("Status exported: Balance=", balance, " Equity=", equity, " Positions=", posCount);
}

//+------------------------------------------------------------------+
string OrderTypeToString(ENUM_ORDER_TYPE type)
{
   switch(type)
   {
      case ORDER_TYPE_BUY: return "BUY";
      case ORDER_TYPE_SELL: return "SELL";
      case ORDER_TYPE_BUY_LIMIT: return "BUY_LIMIT";
      case ORDER_TYPE_SELL_LIMIT: return "SELL_LIMIT";
      case ORDER_TYPE_BUY_STOP: return "BUY_STOP";
      case ORDER_TYPE_SELL_STOP: return "SELL_STOP";
      default: return "UNKNOWN";
   }
}
//+------------------------------------------------------------------+
