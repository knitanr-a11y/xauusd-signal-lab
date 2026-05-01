#property strict
#property version   "1.00"
#property description "Export OHLC data for multiple symbols and timeframes to CSV."
#property description "Attach this EA to one chart only. Configure symbols/timeframes from EA inputs."

// ============================================================
// ExportOhlcMultiSymbolEA.mq4
//
// Purpose:
//   Export OHLC data from MT4 to CSV for Python backtesting.
//
// Output folder:
//   MT4 terminal data folder / MQL4 / Files /
//
// Output examples:
//   XAUUSD_M15.csv
//   XAUUSD_H1.csv
//   BTCUSD_M15.csv
//   BTCUSD_H1.csv
//
// Important:
//   - Attach this EA to ONE chart only.
//   - Symbols must exist in Market Watch.
//   - Broker symbol names can differ, e.g. XAUUSD, GOLD, BTCUSD, BTC/USD, BTCUSDm.
//   - Historical spread is not always available in MT4, so this EA writes current spread.
// ============================================================

input string InpSymbolsCsv            = "XAUUSD,BTCUSD";  // Symbols to export, comma-separated
input string InpTimeframesCsv         = "M15,H1";          // Timeframes to export, comma-separated
input int    InpBarsToExport          = 5000;              // Bars per symbol/timeframe
input int    InpExportIntervalSeconds = 60;                // Timer interval in seconds
input bool   InpExportOnInit          = true;              // Export immediately on EA start
input bool   InpPrintLogs             = true;              // Print logs to Experts tab

// ------------------------------------------------------------
// Utility: trim spaces
// ------------------------------------------------------------
string Trim(const string value)
{
   string s = value;
   StringTrimLeft(s);
   StringTrimRight(s);
   return s;
}

// ------------------------------------------------------------
// Utility: sanitize symbol name for file name
// ------------------------------------------------------------
string SanitizeFileName(const string value)
{
   string s = value;
   StringReplace(s, "/", "");
   StringReplace(s, "\\", "");
   StringReplace(s, ":", "");
   StringReplace(s, "*", "");
   StringReplace(s, "?", "");
   StringReplace(s, "\"", "");
   StringReplace(s, "<", "");
   StringReplace(s, ">", "");
   StringReplace(s, "|", "");
   StringReplace(s, " ", "");
   return s;
}

// ------------------------------------------------------------
// Convert timeframe string to MT4 timeframe constant
// ------------------------------------------------------------
int TimeframeFromString(string tf)
{
   tf = Trim(tf);

   if(tf == "1"   || tf == "M1")   return PERIOD_M1;
   if(tf == "5"   || tf == "M5")   return PERIOD_M5;
   if(tf == "15"  || tf == "M15")  return PERIOD_M15;
   if(tf == "30"  || tf == "M30")  return PERIOD_M30;
   if(tf == "60"  || tf == "H1")   return PERIOD_H1;
   if(tf == "240" || tf == "H4")   return PERIOD_H4;
   if(tf == "1440"|| tf == "D1")   return PERIOD_D1;
   if(tf == "10080"|| tf == "W1")  return PERIOD_W1;
   if(tf == "43200"|| tf == "MN1") return PERIOD_MN1;

   return -1;
}

// ------------------------------------------------------------
// Convert timeframe constant to label for file name
// ------------------------------------------------------------
string TimeframeToLabel(const int tf)
{
   if(tf == PERIOD_M1)  return "M1";
   if(tf == PERIOD_M5)  return "M5";
   if(tf == PERIOD_M15) return "M15";
   if(tf == PERIOD_M30) return "M30";
   if(tf == PERIOD_H1)  return "H1";
   if(tf == PERIOD_H4)  return "H4";
   if(tf == PERIOD_D1)  return "D1";
   if(tf == PERIOD_W1)  return "W1";
   if(tf == PERIOD_MN1) return "MN1";
   return "TF" + IntegerToString(tf);
}

// ------------------------------------------------------------
// Write one symbol/timeframe CSV
// ------------------------------------------------------------
bool ExportOne(const string symbolRaw, const int timeframe)
{
   string symbol = Trim(symbolRaw);
   if(symbol == "")
      return false;

   bool selected = SymbolSelect(symbol, true);
   if(!selected)
   {
      Print("[ExportOhlcMultiSymbolEA] ERROR: SymbolSelect failed: ", symbol,
            ". Check broker symbol name and Market Watch.");
      return false;
   }

   int totalBars = iBars(symbol, timeframe);
   if(totalBars <= 0)
   {
      Print("[ExportOhlcMultiSymbolEA] ERROR: No bars for ", symbol, " ", TimeframeToLabel(timeframe),
            ". Open chart or download history first.");
      return false;
   }

   int bars = InpBarsToExport;
   if(bars <= 0 || bars > totalBars)
      bars = totalBars;

   int digits = (int)MarketInfo(symbol, MODE_DIGITS);
   int currentSpread = (int)MarketInfo(symbol, MODE_SPREAD);

   string fileName = SanitizeFileName(symbol) + "_" + TimeframeToLabel(timeframe) + ".csv";
   int handle = FileOpen(fileName, FILE_CSV | FILE_WRITE | FILE_ANSI, ',');

   if(handle == INVALID_HANDLE)
   {
      Print("[ExportOhlcMultiSymbolEA] ERROR: FileOpen failed: ", fileName,
            ", error=", GetLastError());
      return false;
   }

   FileWrite(handle, "time", "open", "high", "low", "close", "volume", "spread");

   // MT4 shift 0 is the latest bar. Write chronological order: old -> new.
   for(int shift = bars - 1; shift >= 0; shift--)
   {
      datetime t = iTime(symbol, timeframe, shift);
      if(t <= 0)
         continue;

      double o = iOpen(symbol, timeframe, shift);
      double h = iHigh(symbol, timeframe, shift);
      double l = iLow(symbol, timeframe, shift);
      double c = iClose(symbol, timeframe, shift);
      long   v = iVolume(symbol, timeframe, shift);

      FileWrite(
         handle,
         TimeToString(t, TIME_DATE | TIME_MINUTES),
         DoubleToString(o, digits),
         DoubleToString(h, digits),
         DoubleToString(l, digits),
         DoubleToString(c, digits),
         IntegerToString((int)v),
         IntegerToString(currentSpread)
      );
   }

   FileClose(handle);

   if(InpPrintLogs)
   {
      Print("[ExportOhlcMultiSymbolEA] Exported: ", fileName,
            " bars=", bars,
            " spread=", currentSpread,
            " digits=", digits);
   }

   return true;
}

// ------------------------------------------------------------
// Export all configured symbols and timeframes
// ------------------------------------------------------------
void ExportAll()
{
   string symbols[];
   string timeframes[];

   int symbolCount = StringSplit(InpSymbolsCsv, ',', symbols);
   int tfCount = StringSplit(InpTimeframesCsv, ',', timeframes);

   if(symbolCount <= 0)
   {
      Print("[ExportOhlcMultiSymbolEA] ERROR: No symbols configured.");
      return;
   }

   if(tfCount <= 0)
   {
      Print("[ExportOhlcMultiSymbolEA] ERROR: No timeframes configured.");
      return;
   }

   for(int s = 0; s < symbolCount; s++)
   {
      string symbol = Trim(symbols[s]);
      if(symbol == "")
         continue;

      for(int t = 0; t < tfCount; t++)
      {
         int tf = TimeframeFromString(timeframes[t]);
         if(tf < 0)
         {
            Print("[ExportOhlcMultiSymbolEA] ERROR: Unsupported timeframe: ", timeframes[t]);
            continue;
         }

         ExportOne(symbol, tf);
      }
   }
}

// ------------------------------------------------------------
// EA lifecycle
// ------------------------------------------------------------
int OnInit()
{
   if(InpExportIntervalSeconds < 1)
   {
      Print("[ExportOhlcMultiSymbolEA] ERROR: InpExportIntervalSeconds must be >= 1.");
      return INIT_PARAMETERS_INCORRECT;
   }

   EventSetTimer(InpExportIntervalSeconds);

   if(InpPrintLogs)
   {
      Print("[ExportOhlcMultiSymbolEA] Started. Symbols=", InpSymbolsCsv,
            " Timeframes=", InpTimeframesCsv,
            " Bars=", InpBarsToExport,
            " IntervalSeconds=", InpExportIntervalSeconds);
   }

   if(InpExportOnInit)
      ExportAll();

   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();

   if(InpPrintLogs)
      Print("[ExportOhlcMultiSymbolEA] Stopped. reason=", reason);
}

void OnTimer()
{
   ExportAll();
}

void OnTick()
{
   // Intentionally empty.
   // Export is timer-based so this EA can be attached to only one chart
   // while exporting multiple symbols.
}
