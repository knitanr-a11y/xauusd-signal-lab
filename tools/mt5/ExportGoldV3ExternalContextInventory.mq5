#property strict
#property script_show_inputs
#property version   "1.00"
#property description "Read-only GOLD V3 Stage277 external-context availability inventory."
#property description "Exports exact broker symbols, sessions, and closed-bar coverage summaries."

input string   InpGoldBaselineSymbol = "";                         // Empty = current chart symbol
input string   InpExplicitSymbols     = "";                         // Optional semicolon-separated exact symbols
input datetime InpFromServer          = D'2023.01.01 00:00:00';
input datetime InpToServerExclusive   = D'2027.01.01 00:00:00';
input string   InpFilePrefix          = "gold_v3_stage277_external_context_inventory";
input bool     InpUseCommonFolder     = false;
input int      InpRatesChunkDays      = 31;
input int      InpCopyRetryCount      = 5;
input int      InpRetrySleepMs        = 500;
input bool     InpProbeM1             = true;
input bool     InpProbeM5             = true;
input bool     InpProbeM15            = true;
input bool     InpProbeH1             = true;
input bool     InpProbeH4             = true;
input bool     InpProbeD1             = true;

struct ProbeSummary
  {
   string   symbol;
   string   source_group;
   string   match_basis;
   string   timeframe;
   int      timeframe_seconds;
   long     rows_total;
   datetime first_bar_time;
   datetime last_bar_time;
   long     rows_2023;
   long     rows_2024;
   long     rows_2025;
   long     rows_2026;
   datetime first_2023;
   datetime last_2023;
   datetime first_2024;
   datetime last_2024;
   datetime first_2025;
   datetime last_2025;
   datetime first_2026;
   datetime last_2026;
   long     duplicate_count;
   long     non_monotonic_count;
   long     raw_gap_count;
   long     max_gap_seconds;
   int      copy_errors;
   int      empty_chunks;
   int      chunks;
   string   status;
  };

string TrimCopy(string value)
  {
   StringTrimLeft(value);
   StringTrimRight(value);
   return value;
  }

string SanitizeFilePart(string value)
  {
   StringReplace(value,"\\","_");
   StringReplace(value,"/","_");
   StringReplace(value,":","_");
   StringReplace(value,"*","_");
   StringReplace(value,"?","_");
   StringReplace(value,"\"","_");
   StringReplace(value,"<","_");
   StringReplace(value,">","_");
   StringReplace(value,"|","_");
   StringReplace(value,"#","_");
   value=TrimCopy(value);
   if(value=="") value="gold_v3_stage277_external_context_inventory";
   return value;
  }

int FileFlags()
  {
   int flags=FILE_WRITE|FILE_CSV|FILE_ANSI;
   if(InpUseCommonFolder) flags|=FILE_COMMON;
   return flags;
  }

string OutputRoot()
  {
   if(InpUseCommonFolder)
      return TerminalInfoString(TERMINAL_COMMONDATA_PATH)+"\\Files\\";
   return TerminalInfoString(TERMINAL_DATA_PATH)+"\\MQL5\\Files\\";
  }

string UpperCopy(string value)
  {
   StringToUpper(value);
   return value;
  }

string CompactSymbolName(string value)
  {
   value=UpperCopy(value);
   StringReplace(value,"#","");
   StringReplace(value,".","");
   StringReplace(value,"_","");
   StringReplace(value,"-","");
   StringReplace(value," ","");
   return value;
  }

bool ContainsAny(const string haystack,const string a,const string b="",const string c="",const string d="",const string e="")
  {
   if(a!="" && StringFind(haystack,a)>=0) return true;
   if(b!="" && StringFind(haystack,b)>=0) return true;
   if(c!="" && StringFind(haystack,c)>=0) return true;
   if(d!="" && StringFind(haystack,d)>=0) return true;
   if(e!="" && StringFind(haystack,e)>=0) return true;
   return false;
  }

string ClassifySourceGroup(const string symbol,const string path,const string description,string &match_basis)
  {
   string compact=CompactSymbolName(symbol);
   string text=UpperCopy(symbol+"|"+path+"|"+description);
   match_basis="";

   string baseline=InpGoldBaselineSymbol;
   if(baseline=="") baseline=_Symbol;
   if(symbol==baseline)
     {
      match_basis="exact_baseline_symbol";
      return "GOLD_BASELINE";
     }

   if(StringFind(compact,"XAGUSD")>=0 || ContainsAny(text,"SILVER","XAG/USD"))
     {
      match_basis="name_or_description_token:XAGUSD|SILVER";
      return "XAGUSD";
     }
   if(StringFind(compact,"USDJPY")>=0)
     {
      match_basis="symbol_token:USDJPY";
      return "USDJPY";
     }
   if(StringFind(compact,"EURUSD")>=0)
     {
      match_basis="symbol_token:EURUSD";
      return "EURUSD";
     }
   if(ContainsAny(compact,"US500","SPX500","SP500","SANDP500") || ContainsAny(text,"S&P 500","S&P500"))
     {
      match_basis="name_or_description_token:US500|SPX500|SP500|S&P500";
      return "US500_RISK_PROXY";
     }
   if(ContainsAny(compact,"NAS100","USTEC","US100","NDX100","NASDAQ100") || ContainsAny(text,"NASDAQ 100","NASDAQ100"))
     {
      match_basis="name_or_description_token:NAS100|USTEC|US100|NDX|NASDAQ100";
      return "NAS100_RISK_PROXY";
     }
   if(ContainsAny(compact,"DXY","USDX","USDINDEX","DOLLARINDEX") || ContainsAny(text,"US DOLLAR INDEX","USD INDEX","DOLLAR INDEX"))
     {
      match_basis="name_or_description_token:DXY|USDX|USDINDEX|DOLLARINDEX";
      return "USD_INDEX_PROXY";
     }
   if(ContainsAny(compact,"US10Y","UST10Y","US2Y","UST2Y","US30Y") || ContainsAny(text,"US 10Y","US10Y","TREASURY 10","10-YEAR TREASURY","US 2Y"))
     {
      match_basis="name_or_description_token:US10Y|UST10Y|US2Y|US30Y";
      return "YIELD_PROXY";
     }

   match_basis="no_priority_token_match";
   return "UNCLASSIFIED";
  }

bool IsExplicitSymbol(const string symbol)
  {
   string raw=InpExplicitSymbols;
   raw=TrimCopy(raw);
   if(raw=="") return false;

   string items[];
   int count=StringSplit(raw,';',items);
   for(int i=0;i<count;i++)
     {
      string item=TrimCopy(items[i]);
      if(item!="" && item==symbol) return true;
     }
   return false;
  }

string TfLabel(const ENUM_TIMEFRAMES tf)
  {
   switch(tf)
     {
      case PERIOD_M1:  return "M1";
      case PERIOD_M5:  return "M5";
      case PERIOD_M15: return "M15";
      case PERIOD_H1:  return "H1";
      case PERIOD_H4:  return "H4";
      case PERIOD_D1:  return "D1";
      default:         return "UNKNOWN";
     }
  }

void ResetProbeSummary(ProbeSummary &result,const string symbol,const string source_group,const string match_basis,const ENUM_TIMEFRAMES tf)
  {
   result.symbol=symbol;
   result.source_group=source_group;
   result.match_basis=match_basis;
   result.timeframe=TfLabel(tf);
   result.timeframe_seconds=PeriodSeconds(tf);
   result.rows_total=0;
   result.first_bar_time=0;
   result.last_bar_time=0;
   result.rows_2023=0;
   result.rows_2024=0;
   result.rows_2025=0;
   result.rows_2026=0;
   result.first_2023=0;
   result.last_2023=0;
   result.first_2024=0;
   result.last_2024=0;
   result.first_2025=0;
   result.last_2025=0;
   result.first_2026=0;
   result.last_2026=0;
   result.duplicate_count=0;
   result.non_monotonic_count=0;
   result.raw_gap_count=0;
   result.max_gap_seconds=0;
   result.copy_errors=0;
   result.empty_chunks=0;
   result.chunks=0;
   result.status="NOT_RUN";
  }

void AddYearRow(ProbeSummary &result,const datetime bar_time)
  {
   MqlDateTime parts;
   TimeToStruct(bar_time,parts);
   if(parts.year==2023)
     {
      result.rows_2023++;
      if(result.first_2023==0) result.first_2023=bar_time;
      result.last_2023=bar_time;
     }
   else if(parts.year==2024)
     {
      result.rows_2024++;
      if(result.first_2024==0) result.first_2024=bar_time;
      result.last_2024=bar_time;
     }
   else if(parts.year==2025)
     {
      result.rows_2025++;
      if(result.first_2025==0) result.first_2025=bar_time;
      result.last_2025=bar_time;
     }
   else if(parts.year==2026)
     {
      result.rows_2026++;
      if(result.first_2026==0) result.first_2026=bar_time;
      result.last_2026=bar_time;
     }
  }

int CopyRatesRetry(const string symbol,const ENUM_TIMEFRAMES tf,const datetime from_time,const datetime to_time_inclusive,MqlRates &rates[])
  {
   int retries=InpCopyRetryCount;
   if(retries<1) retries=1;
   int sleep_ms=InpRetrySleepMs;
   if(sleep_ms<100) sleep_ms=100;

   bool saw_zero=false;
   for(int attempt=0;attempt<retries;attempt++)
     {
      ResetLastError();
      ArrayFree(rates);
      ArraySetAsSeries(rates,false);
      int copied=CopyRates(symbol,tf,from_time,to_time_inclusive,rates);
      if(copied>0) return copied;
      if(copied==0) saw_zero=true;
      int err=GetLastError();
      long synchronized=0;
      SeriesInfoInteger(symbol,tf,SERIES_SYNCHRONIZED,synchronized);
      PrintFormat("Stage277 CopyRates retry: symbol=%s tf=%s attempt=%d copied=%d synchronized=%d error=%d",
                  symbol,TfLabel(tf),attempt+1,copied,synchronized,err);
      Sleep(sleep_ms);
     }
   if(saw_zero) return 0;
   return -1;
  }

ProbeSummary ProbeTimeframe(const string symbol,const string source_group,const string match_basis,const ENUM_TIMEFRAMES tf,const datetime effective_to_exclusive,const datetime captured_server_now)
  {
   ProbeSummary result;
   ResetProbeSummary(result,symbol,source_group,match_basis,tf);

   if(!SymbolSelect(symbol,true))
     {
      result.status="SYMBOL_SELECT_FAILED";
      result.copy_errors=1;
      return result;
     }

   int chunk_days=InpRatesChunkDays;
   if(chunk_days<1) chunk_days=1;
   datetime cursor=InpFromServer;
   datetime previous_time=0;

   while(cursor<effective_to_exclusive)
     {
      datetime next=cursor+(datetime)(chunk_days*86400);
      if(next>effective_to_exclusive) next=effective_to_exclusive;
      if(next<=cursor) break;

      MqlRates rates[];
      ArraySetAsSeries(rates,false);
      int copied=CopyRatesRetry(symbol,tf,cursor,next-1,rates);
      result.chunks++;
      if(copied<0)
        {
         result.copy_errors++;
         cursor=next;
         continue;
        }
      if(copied==0) result.empty_chunks++;

      for(int i=0;i<copied;i++)
        {
         datetime bar_time=rates[i].time;
         if(bar_time<InpFromServer || bar_time>=effective_to_exclusive) continue;

         // Closed bars only. CSV time semantics are broker-server bar OPEN time.
         if(bar_time+(datetime)result.timeframe_seconds>captured_server_now) continue;

         if(previous_time!=0)
           {
            if(bar_time==previous_time) result.duplicate_count++;
            if(bar_time<previous_time) result.non_monotonic_count++;
            long delta=(long)(bar_time-previous_time);
            if(delta>result.timeframe_seconds)
              {
               result.raw_gap_count++;
               if(delta>result.max_gap_seconds) result.max_gap_seconds=delta;
              }
           }

         if(result.rows_total==0) result.first_bar_time=bar_time;
         result.last_bar_time=bar_time;
         result.rows_total++;
         AddYearRow(result,bar_time);
         previous_time=bar_time;
        }

      cursor=next;
     }

   if(result.rows_total>0 && result.copy_errors==0) result.status="AVAILABLE";
   else if(result.rows_total>0 && result.copy_errors>0) result.status="PARTIAL_COPY_ERRORS";
   else if(result.rows_total==0 && result.copy_errors==0) result.status="NO_RATES_RETURNED";
   else result.status="COPY_FAILED";

   return result;
  }

string TimeText(const datetime value)
  {
   if(value==0) return "";
   return TimeToString(value,TIME_DATE|TIME_SECONDS);
  }

void WriteProbeHeader(const int handle)
  {
   FileWrite(handle,
             "captured_at_server","broker_company","account_server","terminal_build",
             "symbol","source_group","match_basis","timeframe","timeframe_seconds",
             "requested_from_server_inclusive","requested_to_server_exclusive","effective_to_server_exclusive",
             "rows_total","first_bar_open_time","last_bar_open_time",
             "rows_2023","first_2023","last_2023",
             "rows_2024","first_2024","last_2024",
             "rows_2025","first_2025","last_2025",
             "rows_2026","first_2026","last_2026",
             "duplicate_count","non_monotonic_count","raw_gap_intervals_gt_one_period",
             "max_raw_gap_seconds","copy_errors","empty_chunks","chunks","status",
             "csv_time_semantics","closed_bar_rule","source_close_availability_rule",
             "gap_fill_applied","nearest_future_applied","fallback_source_applied","audit_only");
  }

void WriteProbeRow(const int handle,const ProbeSummary &result,const datetime captured_server_now,const datetime effective_to_exclusive)
  {
   FileWrite(handle,
             TimeText(captured_server_now),
             AccountInfoString(ACCOUNT_COMPANY),
             AccountInfoString(ACCOUNT_SERVER),
             (long)TerminalInfoInteger(TERMINAL_BUILD),
             result.symbol,result.source_group,result.match_basis,result.timeframe,result.timeframe_seconds,
             TimeText(InpFromServer),TimeText(InpToServerExclusive),TimeText(effective_to_exclusive),
             result.rows_total,TimeText(result.first_bar_time),TimeText(result.last_bar_time),
             result.rows_2023,TimeText(result.first_2023),TimeText(result.last_2023),
             result.rows_2024,TimeText(result.first_2024),TimeText(result.last_2024),
             result.rows_2025,TimeText(result.first_2025),TimeText(result.last_2025),
             result.rows_2026,TimeText(result.first_2026),TimeText(result.last_2026),
             result.duplicate_count,result.non_monotonic_count,result.raw_gap_count,
             result.max_gap_seconds,result.copy_errors,result.empty_chunks,result.chunks,result.status,
             "broker_server_bar_open_time",
             "bar_open_time+timeframe_seconds<=captured_at_server",
             StringFormat("source_close_time=bar_open_time+%d_seconds; use only source_close_time<=decision_time",result.timeframe_seconds),
             false,false,false,true);
  }

void WriteSymbolHeader(const int handle)
  {
   FileWrite(handle,
             "captured_at_server","broker_company","account_server","terminal_build",
             "symbol","source_group_candidate","match_basis","explicit_symbol_requested",
             "selected_before","selected_for_probe","restore_attempted","restore_succeeded","selected_final",
             "path","description",
             "currency_base","currency_profit","currency_margin",
             "digits","point","trade_tick_size","trade_tick_value","trade_contract_size",
             "trade_calc_mode","trade_mode","current_spread_points","spread_float",
             "spread_price_formula","selection_contract","audit_only");
  }

void WriteSymbolRow(const int handle,const string symbol,const string source_group,const string match_basis,
                    const bool explicit_requested,const bool selected_before,const bool selected_for_probe,
                    const bool restore_attempted,const bool restore_succeeded,const bool selected_final,
                    const datetime captured_server_now)
  {
   long digits=SymbolInfoInteger(symbol,SYMBOL_DIGITS);
   long calc_mode=SymbolInfoInteger(symbol,SYMBOL_TRADE_CALC_MODE);
   long trade_mode=SymbolInfoInteger(symbol,SYMBOL_TRADE_MODE);
   long spread_points=SymbolInfoInteger(symbol,SYMBOL_SPREAD);
   long spread_float=SymbolInfoInteger(symbol,SYMBOL_SPREAD_FLOAT);
   int digits_int=(int)digits;

   FileWrite(handle,
             TimeText(captured_server_now),
             AccountInfoString(ACCOUNT_COMPANY),
             AccountInfoString(ACCOUNT_SERVER),
             (long)TerminalInfoInteger(TERMINAL_BUILD),
             symbol,source_group,match_basis,explicit_requested,
             selected_before,selected_for_probe,restore_attempted,restore_succeeded,selected_final,
             SymbolInfoString(symbol,SYMBOL_PATH),
             SymbolInfoString(symbol,SYMBOL_DESCRIPTION),
             SymbolInfoString(symbol,SYMBOL_CURRENCY_BASE),
             SymbolInfoString(symbol,SYMBOL_CURRENCY_PROFIT),
             SymbolInfoString(symbol,SYMBOL_CURRENCY_MARGIN),
             digits,
             DoubleToString(SymbolInfoDouble(symbol,SYMBOL_POINT),digits_int),
             DoubleToString(SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_SIZE),digits_int),
             DoubleToString(SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_VALUE),8),
             DoubleToString(SymbolInfoDouble(symbol,SYMBOL_TRADE_CONTRACT_SIZE),4),
             EnumToString((ENUM_SYMBOL_CALC_MODE)calc_mode),
             EnumToString((ENUM_SYMBOL_TRADE_MODE)trade_mode),
             spread_points,spread_float,
             "spread_price=spread_points*point",
             "candidate labels are inventory hints only; temporary Market Watch selection is restored when possible; no automatic source substitution or activation",
             true);
  }

void WriteSessions(const int handle,const string symbol,const string source_group,const datetime captured_server_now)
  {
   for(int day=SUNDAY;day<=SATURDAY;day++)
     {
      bool any=false;
      for(uint index=0;index<32;index++)
        {
         datetime from_time=0;
         datetime to_time=0;
         ResetLastError();
         if(!SymbolInfoSessionTrade(symbol,(ENUM_DAY_OF_WEEK)day,index,from_time,to_time)) break;
         any=true;
         FileWrite(handle,
                   TimeText(captured_server_now),
                   AccountInfoString(ACCOUNT_COMPANY),
                   AccountInfoString(ACCOUNT_SERVER),
                   symbol,source_group,
                   EnumToString((ENUM_DAY_OF_WEEK)day),(int)index,
                   TimeToString(from_time,TIME_MINUTES),
                   TimeToString(to_time,TIME_MINUTES),
                   "MT5_SymbolInfoSessionTrade",false,true);
        }
      if(!any)
        {
         FileWrite(handle,
                   TimeText(captured_server_now),
                   AccountInfoString(ACCOUNT_COMPANY),
                   AccountInfoString(ACCOUNT_SERVER),
                   symbol,source_group,
                   EnumToString((ENUM_DAY_OF_WEEK)day),"","","",
                   "NO_SESSION_ROWS_RETURNED",false,true);
        }
     }
  }

void ProbeAndWrite(const int probe_handle,const string symbol,const string source_group,const string match_basis,const ENUM_TIMEFRAMES tf,const datetime effective_to_exclusive,const datetime captured_server_now)
  {
   ProbeSummary result=ProbeTimeframe(symbol,source_group,match_basis,tf,effective_to_exclusive,captured_server_now);
   WriteProbeRow(probe_handle,result,captured_server_now,effective_to_exclusive);
   FileFlush(probe_handle);
   PrintFormat("Stage277 probe: symbol=%s group=%s tf=%s status=%s rows=%I64d",
               symbol,source_group,result.timeframe,result.status,result.rows_total);
  }

void OnStart()
  {
   if(InpToServerExclusive<=InpFromServer)
     {
      Print("Stage277 invalid range: InpToServerExclusive must be later than InpFromServer.");
      return;
     }

   datetime captured_server_now=TimeTradeServer();
   if(captured_server_now<=0) captured_server_now=TimeCurrent();
   if(captured_server_now<=0)
     {
      Print("Stage277 server time unavailable. Confirm the MT5 connection.");
      return;
     }

   datetime effective_to_exclusive=InpToServerExclusive;
   if(effective_to_exclusive>captured_server_now+1) effective_to_exclusive=captured_server_now+1;
   if(effective_to_exclusive<=InpFromServer)
     {
      Print("Stage277 effective end is not later than the requested start.");
      return;
     }

   string baseline_symbol=InpGoldBaselineSymbol;
   if(baseline_symbol=="") baseline_symbol=_Symbol;

   string prefix=SanitizeFilePart(InpFilePrefix);
   string symbols_filename=prefix+"_symbols.csv";
   string probes_filename=prefix+"_timeframe_coverage.csv";
   string sessions_filename=prefix+"_sessions.csv";
   string run_filename=prefix+"_run_metadata.csv";

   int symbols_handle=FileOpen(symbols_filename,FileFlags(),',');
   int probe_handle=FileOpen(probes_filename,FileFlags(),',');
   int sessions_handle=FileOpen(sessions_filename,FileFlags(),',');
   int run_handle=FileOpen(run_filename,FileFlags(),',');
   if(symbols_handle==INVALID_HANDLE || probe_handle==INVALID_HANDLE || sessions_handle==INVALID_HANDLE || run_handle==INVALID_HANDLE)
     {
      PrintFormat("Stage277 FileOpen failed. error=%d",GetLastError());
      if(symbols_handle!=INVALID_HANDLE) FileClose(symbols_handle);
      if(probe_handle!=INVALID_HANDLE) FileClose(probe_handle);
      if(sessions_handle!=INVALID_HANDLE) FileClose(sessions_handle);
      if(run_handle!=INVALID_HANDLE) FileClose(run_handle);
      return;
     }

   WriteSymbolHeader(symbols_handle);
   WriteProbeHeader(probe_handle);
   FileWrite(sessions_handle,
             "captured_at_server","broker_company","account_server","symbol","source_group_candidate",
             "weekday","session_index","from_hhmm","to_hhmm","source_name",
             "holiday_exceptions_included","audit_only");
   FileWrite(run_handle,
             "captured_at_server","broker_company","account_server","terminal_build",
             "baseline_symbol","requested_from_server_inclusive","requested_to_server_exclusive",
             "effective_to_server_exclusive","symbols_total_server","symbols_inventory_rows",
             "symbols_probed","timeframes_requested","csv_time_semantics","closed_only",
             "gap_fill_applied","nearest_future_applied","fallback_source_applied",
             "performance_grid_run","candidate_created","router_changed","live_ready",
             "final_signal","mt5_order","discord_notify","partial_close","audit_only");

   int symbols_total=SymbolsTotal(false);
   int inventory_rows=0;
   int symbols_probed=0;
   int timeframes_requested=0;
   if(InpProbeM1) timeframes_requested++;
   if(InpProbeM5) timeframes_requested++;
   if(InpProbeM15) timeframes_requested++;
   if(InpProbeH1) timeframes_requested++;
   if(InpProbeH4) timeframes_requested++;
   if(InpProbeD1) timeframes_requested++;

   for(int i=0;i<symbols_total;i++)
     {
      string symbol=SymbolName(i,false);
      if(symbol=="") continue;

      bool selected_before=(bool)SymbolInfoInteger(symbol,SYMBOL_SELECT);
      bool explicit_requested=IsExplicitSymbol(symbol);
      string match_basis="";
      string source_group=ClassifySourceGroup(symbol,
                                               SymbolInfoString(symbol,SYMBOL_PATH),
                                               SymbolInfoString(symbol,SYMBOL_DESCRIPTION),
                                               match_basis);
      if(explicit_requested && source_group=="UNCLASSIFIED")
        {
         source_group="EXPLICIT_UNCLASSIFIED";
         match_basis="exact_explicit_symbol";
        }

      bool should_probe=(source_group!="UNCLASSIFIED");
      bool selected_for_probe=selected_before;
      bool restore_attempted=false;
      bool restore_succeeded=true;
      if(should_probe)
        {
         selected_for_probe=SymbolSelect(symbol,true);
         if(!selected_for_probe)
           {
            PrintFormat("Stage277 SymbolSelect failed: symbol=%s error=%d",symbol,GetLastError());
           }
         else
           {
            symbols_probed++;
            WriteSessions(sessions_handle,symbol,source_group,captured_server_now);

            if(InpProbeM1)  ProbeAndWrite(probe_handle,symbol,source_group,match_basis,PERIOD_M1,effective_to_exclusive,captured_server_now);
            if(InpProbeM5)  ProbeAndWrite(probe_handle,symbol,source_group,match_basis,PERIOD_M5,effective_to_exclusive,captured_server_now);
            if(InpProbeM15) ProbeAndWrite(probe_handle,symbol,source_group,match_basis,PERIOD_M15,effective_to_exclusive,captured_server_now);
            if(InpProbeH1)  ProbeAndWrite(probe_handle,symbol,source_group,match_basis,PERIOD_H1,effective_to_exclusive,captured_server_now);
            if(InpProbeH4)  ProbeAndWrite(probe_handle,symbol,source_group,match_basis,PERIOD_H4,effective_to_exclusive,captured_server_now);
            if(InpProbeD1)  ProbeAndWrite(probe_handle,symbol,source_group,match_basis,PERIOD_D1,effective_to_exclusive,captured_server_now);
           }

         if(!selected_before && selected_for_probe)
           {
            restore_attempted=true;
            restore_succeeded=SymbolSelect(symbol,false);
            if(!restore_succeeded)
               PrintFormat("Stage277 Market Watch restore failed: symbol=%s error=%d",symbol,GetLastError());
           }
        }

      bool selected_final=(bool)SymbolInfoInteger(symbol,SYMBOL_SELECT);
      WriteSymbolRow(symbols_handle,symbol,source_group,match_basis,explicit_requested,
                     selected_before,selected_for_probe,restore_attempted,restore_succeeded,selected_final,
                     captured_server_now);
      inventory_rows++;
     }

   FileWrite(run_handle,
             TimeText(captured_server_now),
             AccountInfoString(ACCOUNT_COMPANY),
             AccountInfoString(ACCOUNT_SERVER),
             (long)TerminalInfoInteger(TERMINAL_BUILD),
             baseline_symbol,TimeText(InpFromServer),TimeText(InpToServerExclusive),TimeText(effective_to_exclusive),
             symbols_total,inventory_rows,symbols_probed,timeframes_requested,
             "broker_server_bar_open_time",true,false,false,false,
             false,false,false,false,false,false,false,false,true);

   FileFlush(symbols_handle);
   FileFlush(probe_handle);
   FileFlush(sessions_handle);
   FileFlush(run_handle);
   FileClose(symbols_handle);
   FileClose(probe_handle);
   FileClose(sessions_handle);
   FileClose(run_handle);

   Print("------------------------------------------------------------");
   PrintFormat("GOLD V3 Stage277 inventory finished: server_symbols=%d inventory_rows=%d probed_symbols=%d",
               symbols_total,inventory_rows,symbols_probed);
   PrintFormat("Server range: [%s, %s), effective end=%s",
               TimeText(InpFromServer),TimeText(InpToServerExclusive),TimeText(effective_to_exclusive));
   PrintFormat("Symbols file: %s",symbols_filename);
   PrintFormat("Coverage file: %s",probes_filename);
   PrintFormat("Sessions file: %s",sessions_filename);
   PrintFormat("Run metadata file: %s",run_filename);
   PrintFormat("Output folder: %s",OutputRoot());
   Print("Read-only audit. No model grid, candidate creation, router change, order, alert, or partial close.");
  }
