//+------------------------------------------------------------------+
//|                                                export_ohlc_multi |
//|                              XAUUSD/BTCUSD OHLC CSV Exporter EA  |
//+------------------------------------------------------------------+
#property strict

/*
  Purpose
  -------
  Export OHLC data from MT4 to CSV for one or more symbols and timeframes.

  Initial project use:
    - XAUUSD M15/H1
    - BTCUSD M15/H1, if the broker provides BTC/USD in MT4

  Output folder:
    MT4 terminal data folder / MQL4 / Files /

  Output format:
    time,open,high,low,close,volume,spread

  Important notes:
    - Attach this EA to one chart only.
    - Add target symbols to Market Watch before running.
    - Broker symbol names vary. Examples: XAUUSD, XAUUSDm, GOLD, BTCUSD, BTCUSDm, BTCUSD.
    - The EA does not trade. It only exports CSV files.
*/

input string InpSymbolsCSV       = "XAUUSD,BTCUSD"; // comma-separated symbols
input string InpTimeframesCSV    = "M15,H1";        // comma-separated TFs: M1,M5,M15,M30,H1,H4,D1
input int    InpBarsToExport     = 20000;           // number of bars to export per symbol/timeframe
input int    InpTimerSeconds     = 60;              // export interval in seconds
input bool   InpExportOnInit     = true;            // export immediately when attached
input bool   InpUseSubfolder     = false;           // if true, output to MQL4/Files/export/
input string InpSubfolderName    = "export";

//+------------------------------------------------------------------+
//| Utility: trim string                                             |
//+------------------------------------------------------------------+
string TrimString(string value)
{
   StringTrimLeft(value);
   StringTrimRight(value);
   return value;
}

//+------------------------------------------------------------------+
//| Utility: lower string                                            |
//+------------------------------------------------------------------+
string ToLowerString(string value)
{
   string s = value;
   StringToLower(s);
   return s;
}

//+------------------------------------------------------------------+
//| Utility: upper string                                            |
//+------------------------------------------------------------------+
string ToUpperString(string value)
{
   string s = value;
   StringToUpper(s);
   return s;
}

//+------------------------------------------------------------------+
//| Utility: sanitize filename                                       |
//+------------------------------------------------------------------+
string SanitizeFilePart(string value)
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

//+------------------------------------------------------------------+
//| Digits for symbol                                                |
//+------------------------------------------------------------------+
int DigitsForSymbol(string symbol)
{
   int digits = (int)MarketInfo(symbol, MODE_DIGITS);
   if(digits < 0)
      digits = Digits;
   return digits;
}

//+------------------------------------------------------------------+
//| Convert timeframe text to MT4 timeframe constant                 |
//+------------------------------------------------------------------+
int TimeframeFromString(string tf)
{
   string t = ToUpperString(TrimString(tf));

   if(t == "M1")  return PERIOD_M1;
   if(t == "M5")  return PERIOD_M5;
   if(t == "M15") return PERIOD_M15;
   if(t == "M30") return PERIOD_M30;
   if(t == "H1")  return PERIOD_H1;
   if(t == "H4")  return PERIOD_H4;
   if(t == "D1")  return PERIOD_D1;
   if(t == "W1")  return PERIOD_W1;
   if(t == "MN1") return PERIOD_MN1;

   return -1;
}

//+------------------------------------------------------------------+
//| Convert timeframe constant to label                              |
//+------------------------------------------------------------------+
string TimeframeToLabel(int timeframe)
{
   switch(timeframe)
   {
      case PERIOD_M1:  return "m1";
      case PERIOD_M5:  return "m5";
      case PERIOD_M15: return "m15";
      case PERIOD_M30: return "m30";
      case PERIOD_H1:  return "h1";
      case PERIOD_H4:  return "h4";
      case PERIOD_D1:  return "d1";
      case PERIOD_W1:  return "w1";
      case PERIOD_MN1: return "mn1";
   }
   return "unknown";
}

//+------------------------------------------------------------------+
//| Build output filename                                            |
//+------------------------------------------------------------------+
string BuildFileName(string symbol, int timeframe)
{
   string safeSymbol = ToLowerString(SanitizeFilePart(symbol));
   string tfLabel    = TimeframeToLabel(timeframe);
   string filename   = safeSymbol + "_" + tfLabel + ".csv";

   if(InpUseSubfolder)
      filename = InpSubfolderName + "\\" + filename;

   return filename;
}

//+------------------------------------------------------------------+
//| Ensure symbol is available                                       |
//+------------------------------------------------------------------+
bool EnsureSymbol(string symbol)
{
   string s = TrimString(symbol);
   if(s == "")
      return false;

   if(SymbolSelect(s, true))
      return true;

   Print("[export_ohlc_multi] SymbolSelect failed: ", s,
         " | Add this symbol to Market Watch or check broker symbol name.");
   return false;
}

//+------------------------------------------------------------------+
//| Export one symbol/timeframe                                      |
//+------------------------------------------------------------------+
bool ExportOne(string symbol, int timeframe)
{
   if(!EnsureSymbol(symbol))
      return false;

   int barsAvailable = iBars(symbol, timeframe);
   if(barsAvailable <= 0)
   {
      Print("[export_ohlc_multi] No bars available: ", symbol, " ", TimeframeToLabel(timeframe));
      return false;
   }

   int barsToCopy = MathMin(InpBarsToExport, barsAvailable);

   MqlRates rates[];
   ArraySetAsSeries(rates, true);

   ResetLastError();
   int copied = CopyRates(symbol, timeframe, 0, barsToCopy, rates);
   if(copied <= 0)
   {
      int err = GetLastError();
      Print("[export_ohlc_multi] CopyRates failed: ", symbol, " ", TimeframeToLabel(timeframe),
            " | error=", err);
      return false;
   }

   string filename = BuildFileName(symbol, timeframe);

   ResetLastError();
   int handle = FileOpen(filename, FILE_CSV | FILE_WRITE | FILE_ANSI, ',');
   if(handle == INVALID_HANDLE)
   {
      int fileErr = GetLastError();
      Print("[export_ohlc_multi] FileOpen failed: ", filename,
            " | error=", fileErr,
            " | Check MQL4/Files permissions or subfolder existence.");
      return false;
   }

   FileWrite(handle, "time", "open", "high", "low", "close", "volume", "spread");

   // CopyRates with ArraySetAsSeries(true): index 0 is newest.
   // Write oldest -> newest for Python/time-series processing.
   for(int i = copied - 1; i >= 0; i--)
   {
      string timeText = TimeToString(rates[i].time, TIME_DATE | TIME_MINUTES);

      FileWrite(handle,
                timeText,
                DoubleToString(rates[i].open,  DigitsForSymbol(symbol)),
                DoubleToString(rates[i].high,  DigitsForSymbol(symbol)),
                DoubleToString(rates[i].low,   DigitsForSymbol(symbol)),
                DoubleToString(rates[i].close, DigitsForSymbol(symbol)),
                (long)rates[i].tick_volume,
                (int)rates[i].spread);
   }

   FileClose(handle);

   Print("[export_ohlc_multi] Exported: ", filename,
         " | symbol=", symbol,
         " | timeframe=", TimeframeToLabel(timeframe),
         " | bars=", copied);

   return true;
}

//+------------------------------------------------------------------+
//| Export all configured symbols/timeframes                         |
//+------------------------------------------------------------------+
void ExportAll()
{
   string symbols[];
   string timeframes[];

   int symbolCount = StringSplit(InpSymbolsCSV, ',', symbols);
   int tfCount     = StringSplit(InpTimeframesCSV, ',', timeframes);

   if(symbolCount <= 0)
   {
      Print("[export_ohlc_multi] No symbols configured.");
      return;
   }

   if(tfCount <= 0)
   {
      Print("[export_ohlc_multi] No timeframes configured.");
      return;
   }

   for(int s = 0; s < symbolCount; s++)
   {
      string symbol = TrimString(symbols[s]);
      if(symbol == "")
         continue;

      for(int t = 0; t < tfCount; t++)
      {
         int timeframe = TimeframeFromString(timeframes[t]);
         if(timeframe < 0)
         {
            Print("[export_ohlc_multi] Unsupported timeframe: ", timeframes[t]);
            continue;
         }

         ExportOne(symbol, timeframe);
      }
   }
}

//+------------------------------------------------------------------+
//| Expert initialization                                            |
//+------------------------------------------------------------------+
int OnInit()
{
   Print("[export_ohlc_multi] EA initialized.");
   Print("[export_ohlc_multi] Symbols=", InpSymbolsCSV, " | Timeframes=", InpTimeframesCSV);

   EventSetTimer(MathMax(1, InpTimerSeconds));

   if(InpExportOnInit)
      ExportAll();

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization                                          |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
   Print("[export_ohlc_multi] EA stopped. reason=", reason);
}

//+------------------------------------------------------------------+
//| Timer                                                            |
//+------------------------------------------------------------------+
void OnTimer()
{
   ExportAll();
}

//+------------------------------------------------------------------+
//| Tick                                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // Export is timer-based to avoid excessive writes on every tick.
}
