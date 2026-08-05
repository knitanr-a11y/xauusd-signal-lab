#property copyright "OpenAI"
#property version   "1.00"
#property strict
#property script_show_inputs

// BTC AI research history exporter for MetaTrader 5.
// Time semantics: broker-server naive time.
// Output: only fully closed bars, semicolon-separated UTF-8 CSV.

input string   InpSymbol             = "";                       // Empty = symbol of the chart
input datetime InpStartTime          = D'2023.01.01 00:00:00';   // Requested broker-server start
input datetime InpEndTime            = 0;                        // 0 = latest fully closed bar
input string   InpOutputFolder       = "BTC_AI_RESEARCH_DATA";   // Under MQL5\Files
input bool     InpUseCommonFolder    = false;                    // false = this terminal's MQL5\Files
input int      InpChunkDays          = 31;                       // CopyRates request size
input int      InpMaxRetryCount      = 40;                       // History download/build retries per chunk
input int      InpRetrySleepMs       = 500;                      // Wait between retries
input bool     InpOverwriteExisting  = true;                     // Replace prior completed files

struct ExportResult
  {
   string            timeframe_name;
   string            file_name;
   datetime          requested_start;
   datetime          requested_end;
   datetime          effective_start;
   datetime          effective_end;
   datetime          actual_first;
   datetime          actual_last;
   long              rows;
   long              gap_count;
   long              max_gap_seconds;
   int               min_spread_points;
   int               max_spread_points;
   bool              success;
   string            status;
  };

string TrimCopy(string value)
  {
   StringTrimLeft(value);
   StringTrimRight(value);
   return value;
  }

string ResolveSymbol()
  {
   string configured=TrimCopy(InpSymbol);
   if(StringLen(configured)>0)
      return configured;
   return _Symbol;
  }

string SafeName(string value)
  {
   string out=value;
   StringReplace(out,"\\","_");
   StringReplace(out,"/","_");
   StringReplace(out,":","_");
   StringReplace(out,"*","_");
   StringReplace(out,"?","_");
   StringReplace(out,"\"","_");
   StringReplace(out,"<","_");
   StringReplace(out,">","_");
   StringReplace(out,"|","_");
   StringReplace(out," ","_");
   return out;
  }

string TimeframeName(const ENUM_TIMEFRAMES timeframe)
  {
   switch(timeframe)
     {
      case PERIOD_M1:  return "M1";
      case PERIOD_M5:  return "M5";
      case PERIOD_M15: return "M15";
      case PERIOD_H1:  return "H1";
      case PERIOD_H4:  return "H4";
      case PERIOD_D1:  return "D1";
      default:         return EnumToString(timeframe);
     }
  }

string DateCompact(const datetime value)
  {
   MqlDateTime parts;
   TimeToStruct(value,parts);
   return StringFormat("%04d%02d%02d",parts.year,parts.mon,parts.day);
  }

string DateTimeText(const datetime value)
  {
   if(value<=0)
      return "";
   return TimeToString(value,TIME_DATE|TIME_MINUTES|TIME_SECONDS);
  }

string BoolText(const bool value)
  {
   return value ? "true" : "false";
  }

int FileScopeFlag()
  {
   return InpUseCommonFolder ? FILE_COMMON : 0;
  }

int FileOpenFlags()
  {
   int flags=FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ;
   if(InpUseCommonFolder)
      flags|=FILE_COMMON;
   return flags;
  }

string OutputRootFullPath()
  {
   if(InpUseCommonFolder)
      return TerminalInfoString(TERMINAL_COMMONDATA_PATH)+"\\Files\\"+InpOutputFolder;
   return TerminalInfoString(TERMINAL_DATA_PATH)+"\\MQL5\\Files\\"+InpOutputFolder;
  }

bool EnsureFolder()
  {
   ResetLastError();
   if(FolderCreate(InpOutputFolder,FileScopeFlag()))
      return true;

   const int error_code=GetLastError();
   string probe=InpOutputFolder+"\\.__write_probe.tmp";
   int handle=FileOpen(probe,FileOpenFlags(),';',CP_UTF8);
   if(handle==INVALID_HANDLE)
     {
      PrintFormat("Output folder is not writable: %s error=%d",OutputRootFullPath(),GetLastError());
      return false;
     }
   FileClose(handle);
   FileDelete(probe,FileScopeFlag());
   PrintFormat("Output folder already existed or FolderCreate returned error=%d; write probe succeeded.",error_code);
   return true;
  }

bool EnsureSeriesReady(const string symbol,const ENUM_TIMEFRAMES timeframe)
  {
   MqlRates probe[];
   ArraySetAsSeries(probe,false);

   for(int attempt=0;attempt<InpMaxRetryCount;attempt++)
     {
      ResetLastError();
      int copied=CopyRates(symbol,timeframe,0,10,probe);
      bool synchronized=(bool)SeriesInfoInteger(symbol,timeframe,SERIES_SYNCHRONIZED);
      if(copied>0 && synchronized)
         return true;
      Sleep(InpRetrySleepMs);
     }

   PrintFormat("Series synchronization failed: symbol=%s timeframe=%s error=%d",
               symbol,TimeframeName(timeframe),GetLastError());
   return false;
  }

datetime LatestClosedBarOpen(const string symbol,const ENUM_TIMEFRAMES timeframe)
  {
   MqlRates latest[];
   ArraySetAsSeries(latest,false);

   int copied=-1;
   for(int attempt=0;attempt<InpMaxRetryCount;attempt++)
     {
      ResetLastError();
      copied=CopyRates(symbol,timeframe,0,3,latest);
      if(copied>=2)
         break;
      Sleep(InpRetrySleepMs);
     }

   if(copied<2)
      return 0;

   datetime server_now=TimeTradeServer();
   if(server_now<=0)
      server_now=TimeCurrent();

   int seconds=PeriodSeconds(timeframe);
   if(seconds<=0)
      return 0;

   datetime newest_open=latest[copied-1].time;
   if(newest_open+(datetime)seconds<=server_now)
      return newest_open;

   return latest[copied-2].time;
  }

int CopyRatesWithRetry(const string symbol,
                       const ENUM_TIMEFRAMES timeframe,
                       const datetime from_time,
                       const datetime to_time,
                       MqlRates &rates[])
  {
   ArrayFree(rates);
   ArraySetAsSeries(rates,false);

   for(int attempt=0;attempt<InpMaxRetryCount;attempt++)
     {
      ResetLastError();
      int copied=CopyRates(symbol,timeframe,from_time,to_time,rates);
      if(copied>=0)
         return copied;
      Sleep(InpRetrySleepMs);
     }

   return -1;
  }

bool MoveCompletedFile(const string partial_name,const string final_name)
  {
   int scope=FileScopeFlag();

   if(FileIsExist(final_name,scope) && !InpOverwriteExisting)
     {
      PrintFormat("Completed file already exists and overwrite is disabled: %s",final_name);
      return false;
     }

   int destination_flags=FILE_REWRITE;
   if(InpUseCommonFolder)
      destination_flags|=FILE_COMMON;

   ResetLastError();
   if(!FileMove(partial_name,scope,final_name,destination_flags))
     {
      PrintFormat("FileMove failed: %s -> %s error=%d",partial_name,final_name,GetLastError());
      return false;
     }
   return true;
  }

bool ExportTimeframe(const string symbol,
                     const ENUM_TIMEFRAMES timeframe,
                     ExportResult &result)
  {
   result.timeframe_name=TimeframeName(timeframe);
   result.requested_start=InpStartTime;
   result.requested_end=InpEndTime;
   result.rows=0;
   result.gap_count=0;
   result.max_gap_seconds=0;
   result.min_spread_points=2147483647;
   result.max_spread_points=-2147483647;
   result.success=false;
   result.status="INITIALIZING";

   if(!EnsureSeriesReady(symbol,timeframe))
     {
      result.status="SERIES_NOT_READY";
      return false;
     }

   datetime latest_closed=LatestClosedBarOpen(symbol,timeframe);
   if(latest_closed<=0)
     {
      result.status="NO_CLOSED_BAR";
      return false;
     }

   datetime requested_end=(InpEndTime<=0 ? latest_closed : InpEndTime);
   datetime effective_end=(requested_end<latest_closed ? requested_end : latest_closed);

   datetime server_first=(datetime)SeriesInfoInteger(symbol,timeframe,SERIES_SERVER_FIRSTDATE);
   datetime effective_start=InpStartTime;
   if(server_first>0 && server_first>effective_start)
      effective_start=server_first;

   result.effective_start=effective_start;
   result.effective_end=effective_end;

   if(effective_start>effective_end)
     {
      result.status="REQUESTED_RANGE_NOT_AVAILABLE";
      return false;
     }

   string safe_symbol=SafeName(symbol);
   string base_name=safe_symbol+"_"+result.timeframe_name+"_"+
                    DateCompact(InpStartTime)+"_"+DateCompact(effective_end)+".csv";
   string final_name=InpOutputFolder+"\\"+base_name;
   string partial_name=final_name+".part";
   result.file_name=base_name;

   int scope=FileScopeFlag();
   if(FileIsExist(partial_name,scope))
      FileDelete(partial_name,scope);

   int handle=FileOpen(partial_name,FileOpenFlags(),';',CP_UTF8);
   if(handle==INVALID_HANDLE)
     {
      result.status="FILE_OPEN_FAILED_"+IntegerToString(GetLastError());
      return false;
     }

   FileWrite(handle,"time","open","high","low","close","tick_volume","spread","real_volume");

   int digits=(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS);
   int period_seconds=PeriodSeconds(timeframe);
   long chunk_seconds=(long)InpChunkDays*86400;
   if(chunk_seconds<period_seconds)
      chunk_seconds=period_seconds;

   datetime cursor=effective_start;
   datetime previous_time=0;
   bool failed=false;

   while(cursor<=effective_end)
     {
      long proposed=(long)cursor+chunk_seconds-1;
      datetime chunk_end=(datetime)(proposed<(long)effective_end ? proposed : (long)effective_end);

      MqlRates rates[];
      int copied=CopyRatesWithRetry(symbol,timeframe,cursor,chunk_end,rates);
      if(copied<0)
        {
         result.status="COPY_RATES_FAILED_"+IntegerToString(GetLastError())+"_AT_"+DateTimeText(cursor);
         failed=true;
         break;
        }

      for(int i=0;i<copied;i++)
        {
         datetime bar_time=rates[i].time;
         if(bar_time<effective_start || bar_time>effective_end)
            continue;

         if(previous_time>0)
           {
            long delta=(long)bar_time-(long)previous_time;
            if(delta<=0)
              {
               result.status="NON_ASCENDING_OR_DUPLICATE_TIME_AT_"+DateTimeText(bar_time);
               failed=true;
               break;
              }
            if(delta>period_seconds)
              {
               result.gap_count++;
               if(delta>result.max_gap_seconds)
                  result.max_gap_seconds=delta;
              }
           }

         FileWrite(handle,
                   DateTimeText(bar_time),
                   DoubleToString(rates[i].open,digits),
                   DoubleToString(rates[i].high,digits),
                   DoubleToString(rates[i].low,digits),
                   DoubleToString(rates[i].close,digits),
                   (long)rates[i].tick_volume,
                   (int)rates[i].spread,
                   (long)rates[i].real_volume);

         if(result.rows==0)
            result.actual_first=bar_time;
         result.actual_last=bar_time;
         result.rows++;
         previous_time=bar_time;

         if((int)rates[i].spread<result.min_spread_points)
            result.min_spread_points=(int)rates[i].spread;
         if((int)rates[i].spread>result.max_spread_points)
            result.max_spread_points=(int)rates[i].spread;
        }

      if(failed)
         break;

      FileFlush(handle);
      if(chunk_end>=effective_end)
         break;
      cursor=chunk_end+1;
     }

   FileClose(handle);

   if(failed || result.rows<=0)
     {
      FileDelete(partial_name,scope);
      if(result.rows<=0 && !failed)
         result.status="NO_BARS_IN_REQUESTED_RANGE";
      return false;
     }

   if(!MoveCompletedFile(partial_name,final_name))
     {
      result.status="FINALIZE_RENAME_FAILED";
      return false;
     }

   result.success=true;
   result.status="OK";
   return true;
  }

bool WriteManifest(const string symbol,ExportResult &results[])
  {
   string manifest_name=InpOutputFolder+"\\export_manifest.csv";
   string partial_name=manifest_name+".part";
   int scope=FileScopeFlag();

   if(FileIsExist(partial_name,scope))
      FileDelete(partial_name,scope);

   int handle=FileOpen(partial_name,FileOpenFlags(),';',CP_UTF8);
   if(handle==INVALID_HANDLE)
     {
      PrintFormat("Manifest open failed: error=%d",GetLastError());
      return false;
     }

   FileWrite(handle,
             "symbol","timeframe","requested_start","requested_end_input",
             "effective_start","effective_end_last_closed_open","actual_first","actual_last",
             "rows","gap_count","max_gap_seconds","min_spread_points","max_spread_points",
             "file","success","status");

   for(int i=0;i<ArraySize(results);i++)
     {
      ExportResult r=results[i];
      string min_spread=(r.rows>0 ? IntegerToString(r.min_spread_points) : "");
      string max_spread=(r.rows>0 ? IntegerToString(r.max_spread_points) : "");
      FileWrite(handle,
                symbol,
                r.timeframe_name,
                DateTimeText(r.requested_start),
                DateTimeText(r.requested_end),
                DateTimeText(r.effective_start),
                DateTimeText(r.effective_end),
                DateTimeText(r.actual_first),
                DateTimeText(r.actual_last),
                r.rows,
                r.gap_count,
                r.max_gap_seconds,
                min_spread,
                max_spread,
                r.file_name,
                BoolText(r.success),
                r.status);
     }

   FileClose(handle);
   return MoveCompletedFile(partial_name,manifest_name);
  }

bool WriteSymbolMetadata(const string symbol)
  {
   string final_name=InpOutputFolder+"\\symbol_metadata.csv";
   string partial_name=final_name+".part";
   int scope=FileScopeFlag();

   if(FileIsExist(partial_name,scope))
      FileDelete(partial_name,scope);

   int handle=FileOpen(partial_name,FileOpenFlags(),';',CP_UTF8);
   if(handle==INVALID_HANDLE)
     {
      PrintFormat("Symbol metadata open failed: error=%d",GetLastError());
      return false;
     }

   FileWrite(handle,"field","value");
   FileWrite(handle,"exporter_version","1.00");
   FileWrite(handle,"terminal_company",TerminalInfoString(TERMINAL_COMPANY));
   FileWrite(handle,"account_server",AccountInfoString(ACCOUNT_SERVER));
   FileWrite(handle,"symbol",symbol);
   FileWrite(handle,"description",SymbolInfoString(symbol,SYMBOL_DESCRIPTION));
   FileWrite(handle,"digits",(int)SymbolInfoInteger(symbol,SYMBOL_DIGITS));
   FileWrite(handle,"point",DoubleToString(SymbolInfoDouble(symbol,SYMBOL_POINT),16));
   FileWrite(handle,"trade_tick_size",DoubleToString(SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_SIZE),16));
   FileWrite(handle,"trade_tick_value",DoubleToString(SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_VALUE),16));
   FileWrite(handle,"trade_contract_size",DoubleToString(SymbolInfoDouble(symbol,SYMBOL_TRADE_CONTRACT_SIZE),8));
   FileWrite(handle,"currency_base",SymbolInfoString(symbol,SYMBOL_CURRENCY_BASE));
   FileWrite(handle,"currency_profit",SymbolInfoString(symbol,SYMBOL_CURRENCY_PROFIT));
   FileWrite(handle,"currency_margin",SymbolInfoString(symbol,SYMBOL_CURRENCY_MARGIN));
   FileWrite(handle,"requested_start",DateTimeText(InpStartTime));
   FileWrite(handle,"requested_end_input",DateTimeText(InpEndTime));
   FileWrite(handle,"closed_bars_only","true");
   FileWrite(handle,"time_semantics","MT5 broker-server naive time");
   FileWrite(handle,"csv_delimiter","semicolon");
   FileWrite(handle,"csv_encoding","UTF-8");

   FileClose(handle);
   return MoveCompletedFile(partial_name,final_name);
  }

void OnStart()
  {
   if(InpStartTime<=0)
     {
      Alert("InpStartTime must be greater than zero.");
      return;
     }
   if(InpEndTime>0 && InpEndTime<InpStartTime)
     {
      Alert("InpEndTime must be zero or later than InpStartTime.");
      return;
     }
   if(InpChunkDays<1 || InpMaxRetryCount<1 || InpRetrySleepMs<1)
     {
      Alert("Chunk and retry settings must be positive.");
      return;
     }

   string symbol=ResolveSymbol();
   if(StringLen(symbol)==0)
     {
      Alert("No symbol was resolved.");
      return;
     }

   ResetLastError();
   if(!SymbolSelect(symbol,true))
     {
      Alert(StringFormat("SymbolSelect failed for %s. error=%d",symbol,GetLastError()));
      return;
     }

   if(!EnsureFolder())
     {
      Alert("Output folder preparation failed. See Experts log.");
      return;
     }

   bool metadata_ok=WriteSymbolMetadata(symbol);
   if(!metadata_ok)
      Print("Warning: symbol_metadata.csv could not be finalized.");

   ENUM_TIMEFRAMES timeframes[6]={PERIOD_M1,PERIOD_M5,PERIOD_M15,PERIOD_H1,PERIOD_H4,PERIOD_D1};
   ExportResult results[6];
   int success_count=0;

   PrintFormat("BTC history export started. symbol=%s requested_start=%s requested_end=%s output=%s",
               symbol,DateTimeText(InpStartTime),DateTimeText(InpEndTime),OutputRootFullPath());

   for(int i=0;i<ArraySize(timeframes);i++)
     {
      string tf_name=TimeframeName(timeframes[i]);
      PrintFormat("Exporting %s %s ...",symbol,tf_name);
      if(ExportTimeframe(symbol,timeframes[i],results[i]))
        {
         success_count++;
         PrintFormat("Completed %s rows=%I64d first=%s last=%s gaps=%I64d max_gap_seconds=%I64d file=%s",
                     tf_name,
                     results[i].rows,
                     DateTimeText(results[i].actual_first),
                     DateTimeText(results[i].actual_last),
                     results[i].gap_count,
                     results[i].max_gap_seconds,
                     results[i].file_name);
        }
      else
        {
         PrintFormat("Failed %s status=%s",tf_name,results[i].status);
        }
     }

   bool manifest_ok=WriteManifest(symbol,results);
   string summary=StringFormat("BTC history export finished: %d/6 timeframes succeeded. Manifest=%s Metadata=%s. Output=%s",
                               success_count,(manifest_ok ? "OK" : "FAILED"),
                               (metadata_ok ? "OK" : "FAILED"),OutputRootFullPath());
   Print(summary);
   Alert(summary);
  }
