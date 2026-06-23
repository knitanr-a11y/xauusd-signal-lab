#property strict
#property script_show_inputs
#property version "1.10"

input string InpGoldSymbol = "GOLD#";
input datetime InpStartTime = D'2023.12.01 00:00';
input string InpOutputFolder = "FX_OUTPUTS\\gold_v3\\289_training_history";
input int InpRetrySeconds = 120;

bool EnsureFolders()
{
   FolderCreate("FX_OUTPUTS");
   FolderCreate("FX_OUTPUTS\\gold_v3");
   if(FolderCreate(InpOutputFolder))
      return true;
   int err=GetLastError();
   if(err==5010)
      return true;
   Print("FolderCreate failed: ",err);
   return false;
}

int LoadRates(ENUM_TIMEFRAMES timeframe,MqlRates &rates[],datetime from_time,datetime to_time)
{
   ArraySetAsSeries(rates,false);
   int copied=-1;
   int attempts=MathMax(1,InpRetrySeconds);
   for(int i=0;i<attempts;i++)
   {
      ResetLastError();
      copied=CopyRates(InpGoldSymbol,timeframe,from_time,to_time,rates);
      if(copied>0)
         return copied;
      Print("Waiting for history. timeframe=",EnumToString(timeframe),
            " attempt=",i+1," copied=",copied," error=",GetLastError());
      Sleep(1000);
   }
   return copied;
}

bool ExportTimeframe(ENUM_TIMEFRAMES timeframe,string output_file)
{
   datetime current_open=iTime(InpGoldSymbol,timeframe,0);
   if(current_open<=0)
   {
      Print("Current bar unavailable. timeframe=",EnumToString(timeframe),
            " error=",GetLastError());
      return false;
   }
   datetime end_time=current_open-1;
   if(InpStartTime>=end_time)
   {
      Print("Invalid export range. timeframe=",EnumToString(timeframe));
      return false;
   }

   MqlRates rates[];
   int copied=LoadRates(timeframe,rates,InpStartTime,end_time);
   if(copied<=0)
   {
      Print("CopyRates failed. timeframe=",EnumToString(timeframe),
            " error=",GetLastError());
      return false;
   }

   string path=InpOutputFolder+"\\"+output_file;
   int handle=FileOpen(path,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(handle==INVALID_HANDLE)
   {
      Print("FileOpen failed: ",path," error=",GetLastError());
      return false;
   }

   FileWrite(handle,"time","open","high","low","close","tick_volume","spread","real_volume");
   int digits=(int)SymbolInfoInteger(InpGoldSymbol,SYMBOL_DIGITS);
   int written=0;
   for(int i=0;i<copied;i++)
   {
      if(rates[i].time>=current_open)
         continue;
      FileWrite(handle,
                TimeToString(rates[i].time,TIME_DATE|TIME_SECONDS),
                DoubleToString(rates[i].open,digits),
                DoubleToString(rates[i].high,digits),
                DoubleToString(rates[i].low,digits),
                DoubleToString(rates[i].close,digits),
                (long)rates[i].tick_volume,
                (int)rates[i].spread,
                (long)rates[i].real_volume);
      written++;
   }
   FileFlush(handle);
   FileClose(handle);

   Print("STAGE289_TRAINING_EXPORT_COMPLETE timeframe=",EnumToString(timeframe),
         " path=",path,
         " rows=",written,
         " first=",TimeToString(rates[0].time,TIME_DATE|TIME_SECONDS),
         " last=",TimeToString(rates[copied-1].time,TIME_DATE|TIME_SECONDS));
   return written>0;
}

void OnStart()
{
   if(!SymbolSelect(InpGoldSymbol,true))
   {
      Print("SymbolSelect failed: ",GetLastError());
      return;
   }
   if(!EnsureFolders())
      return;

   bool ok_m1=ExportTimeframe(PERIOD_M1,"goldsharp_m1.csv");
   bool ok_m5=ExportTimeframe(PERIOD_M5,"goldsharp_m5.csv");
   bool ok_m15=ExportTimeframe(PERIOD_M15,"goldsharp_m15.csv");

   if(ok_m1 && ok_m5 && ok_m15)
      Print("STAGE289_TRAINING_HISTORY_EXPORT_ALL_COMPLETE");
   else
      Print("STAGE289_TRAINING_HISTORY_EXPORT_INCOMPLETE");
}
