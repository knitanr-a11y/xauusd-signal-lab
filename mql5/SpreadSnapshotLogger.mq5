//+------------------------------------------------------------------+
//| SpreadSnapshotLogger.mq5                                         |
//| MT5 spread snapshot logger for XM KIWAMI / Vantage comparison     |
//|                                                                  |
//| 目的:                                                            |
//| - Pythonを使わず、MT5だけで現在スプレッドをCSV出力する。          |
//| - まずは壊れにくいように、即時スナップショットを書いて終了する。 |
//|                                                                  |
//| CSV保存場所:                                                     |
//| MT5 -> ファイル -> データフォルダを開く -> MQL5 -> Files          |
//+------------------------------------------------------------------+
#property strict
#property script_show_inputs

input string InpSymbolsCsv = "GOLD#,BTCUSD#,USDJPY#,EURJPY#,GBPJPY#";
input int    InpSamples    = 10;      // 何回記録するか。まずは10回で十分。
input int    InpIntervalMs = 1000;    // 記録間隔ミリ秒。1000 = 1秒。
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
   StringReplace(value, ".", "-");
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
      "sample_no",
      "account_login",
      "account_server",
      "account_company",
      "symbol",
      "selected",
      "tick_ok",
      "bid",
      "ask",
      "spread_price",
      "spread_points_by_price",
      "symbol_spread_points",
      "digits",
      "point",
      "trade_mode",
      "last_error"
   );
}

void WriteSymbolSnapshot(const int handle, const int sample_no, const string symbol)
{
   ResetLastError();
   const bool selected = SymbolSelect(symbol, true);
   int last_error = GetLastError();

   MqlTick tick;
   ZeroMemory(tick);

   ResetLastError();
   const bool tick_ok = SymbolInfoTick(symbol, tick);
   if(!tick_ok)
      last_error = GetLastError();

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
      sample_no,
      (long)AccountInfoInteger(ACCOUNT_LOGIN),
      AccountInfoString(ACCOUNT_SERVER),
      AccountInfoString(ACCOUNT_COMPANY),
      symbol,
      selected ? "true" : "false",
      tick_ok ? "true" : "false",
      DoubleToString(tick.bid, digits),
      DoubleToString(tick.ask, digits),
      DoubleToString(spread_price, digits),
      DoubleToString(spread_points_by_price, 2),
      symbol_spread_points,
      digits,
      DoubleToString(point, digits),
      trade_mode,
      last_error
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
   const string started_part = SanitizeFilePart(started);

   const string file_name = InpFilePrefix + "_" + company + "_" + server + "_" + IntegerToString((int)login) + "_" + started_part + ".csv";

   ResetLastError();
   const int handle = FileOpen(file_name, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(handle == INVALID_HANDLE)
   {
      Print("FileOpen failed: ", file_name, " error=", GetLastError());
      return;
   }

   Print("Spread snapshot logger started: ", file_name);
   Print("CSV output folder: MT5 -> File -> Open Data Folder -> MQL5 -> Files");

   WriteHeader(handle);
   FileFlush(handle);

   int samples = InpSamples;
   if(samples < 1)
      samples = 1;

   for(int sample_no = 1; sample_no <= samples; sample_no++)
   {
      for(int i = 0; i < count; i++)
      {
         const string symbol = TrimString(symbols[i]);
         if(symbol == "")
            continue;

         WriteSymbolSnapshot(handle, sample_no, symbol);
      }

      FileFlush(handle);

      if(sample_no < samples)
         Sleep(InpIntervalMs);
   }

   FileClose(handle);
   Print("Spread snapshot logger finished: ", file_name);
}
