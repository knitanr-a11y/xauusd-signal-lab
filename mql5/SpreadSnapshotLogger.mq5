//+------------------------------------------------------------------+
//| SpreadSnapshotLogger.mq5                                         |
//| MT5 spread snapshot logger for XM KIWAMI / Vantage comparison     |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs

input string InpSymbolsCsv = "GOLD#,BTCUSD#,USDJPY#,EURJPY#,GBPJPY#";
input int    InpSeconds    = 300;     // 計測秒数
input int    InpIntervalMs = 1000;    // 記録間隔ミリ秒
input string InpFilePrefix = "spread_snapshot";

string TrimString(string value)
{
   StringTrimLeft(value);
   StringTrimRight(value);
   return value;
}

string SanitizeFilePart(string value)
{
   StringReplace(value, " ", "_");
   StringReplace(value, ":", "-");
   StringReplace(value, "/", "-");
   StringReplace(value, "\\", "-");
   StringReplace(value, "#", "sharp");
   return value;
}

void WriteHeader(const int handle)
{
   FileWrite(
      handle,
      "timestamp_server",
      "account_login",
      "account_server",
      "account_company",
      "symbol",
      "bid",
      "ask",
      "spread_price",
      "spread_points_by_price",
      "symbol_spread_points",
      "digits",
      "point",
      "trade_mode"
   );
}

void WriteSymbolSnapshot(const int handle, const string symbol)
{
   if(!SymbolSelect(symbol, true))
   {
      Print("SymbolSelect failed: ", symbol, " error=", GetLastError());
      return;
   }

   MqlTick tick;
   if(!SymbolInfoTick(symbol, tick))
   {
      Print("SymbolInfoTick failed: ", symbol, " error=", GetLastError());
      return;
   }

   const double point = SymbolInfoDouble(symbol, SYMBOL_POINT);
   const int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   const int trade_mode = (int)SymbolInfoInteger(symbol, SYMBOL_TRADE_MODE);
   const int symbol_spread_points = (int)SymbolInfoInteger(symbol, SYMBOL_SPREAD);

   double spread_price = 0.0;
   double spread_points_by_price = 0.0;

   if(tick.ask > 0.0 && tick.bid > 0.0)
   {
      spread_price = tick.ask - tick.bid;
      if(point > 0.0)
         spread_points_by_price = spread_price / point;
   }

   FileWrite(
      handle,
      TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS),
      (long)AccountInfoInteger(ACCOUNT_LOGIN),
      AccountInfoString(ACCOUNT_SERVER),
      AccountInfoString(ACCOUNT_COMPANY),
      symbol,
      DoubleToString(tick.bid, digits),
      DoubleToString(tick.ask, digits),
      DoubleToString(spread_price, digits),
      DoubleToString(spread_points_by_price, 2),
      symbol_spread_points,
      digits,
      DoubleToString(point, digits),
      trade_mode
   );
}

void OnStart()
{
   string symbols[];
   const int count = StringSplit(InpSymbolsCsv, ',', symbols);

   if(count <= 0)
   {
      Print("No symbols. Please set InpSymbolsCsv.");
      return;
   }

   const string server = SanitizeFilePart(AccountInfoString(ACCOUNT_SERVER));
   const string company = SanitizeFilePart(AccountInfoString(ACCOUNT_COMPANY));
   const long login = (long)AccountInfoInteger(ACCOUNT_LOGIN);
   const string started = TimeToString(TimeCurrent(), TIME_DATE | TIME_MINUTES | TIME_SECONDS);
   string started_part = SanitizeFilePart(started);

   const string file_name = InpFilePrefix + "_" + company + "_" + server + "_" + IntegerToString((int)login) + "_" + started_part + ".csv";

   const int handle = FileOpen(file_name, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(handle == INVALID_HANDLE)
   {
      Print("FileOpen failed: ", file_name, " error=", GetLastError());
      return;
   }

   Print("Spread snapshot logging started: ", file_name);
   Print("CSV output folder: MT5 File -> Open Data Folder -> MQL5 -> Files");

   WriteHeader(handle);

   const datetime end_time = TimeCurrent() + InpSeconds;

   while(!IsStopped() && TimeCurrent() <= end_time)
   {
      for(int i = 0; i < count; i++)
      {
         const string symbol = TrimString(symbols[i]);
         if(symbol == "")
            continue;

         WriteSymbolSnapshot(handle, symbol);
      }

      FileFlush(handle);
      Sleep(InpIntervalMs);
   }

   FileClose(handle);
   Print("Spread snapshot logging finished: ", file_name);
}
