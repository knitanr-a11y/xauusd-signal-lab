#!/usr/bin/env python3
"""Upgrade ExportOhlcToCsv.mq5 v1.34 to v1.35.

Adds confirmed M15 exports for US100Cash# and US500Cash# without changing the
existing GOLD/BTC candle contracts. A .bak copy is created before replacement.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def patch(source: Path) -> None:
    raw = source.read_bytes()
    text = raw.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text else "\n"
    text = text.replace("\r\n", "\n")

    text = replace_once(text, '#property version   "1.34"', '#property version   "1.35"', "version")
    text = replace_once(
        text,
        '#property description "Export confirmed OHLC candles and optional GOLD V3 closed-bar feature snapshot."',
        '#property description "Export confirmed OHLC candles for GOLD, BTC, US100Cash and US500Cash, plus optional GOLD V3 feature snapshot."',
        "description",
    )
    text = replace_once(
        text,
        '''input string InpGoldSymbol = "GOLD#";
input string InpBtcSymbol  = "BTCUSD#";
input bool   InpExportGold = true;
input bool   InpExportBtc  = true;
''',
        '''input string InpGoldSymbol  = "GOLD#";
input string InpBtcSymbol   = "BTCUSD#";
input string InpUs100Symbol = "US100Cash#";
input string InpUs500Symbol = "US500Cash#";
input bool   InpExportGold  = true;
input bool   InpExportBtc   = true;
input bool   InpExportUs100 = true;
input bool   InpExportUs500 = true;
''',
        "symbol inputs",
    )
    text = replace_once(
        text,
        '''input bool   InpBtcD1Enabled  = true;
input bool   InpBtcH4Enabled  = true;
''',
        '''input bool   InpBtcD1Enabled  = true;
input bool   InpBtcH4Enabled  = true;
input bool   InpUs100M15Enabled = true;
input bool   InpUs500M15Enabled = true;
''',
        "index enable inputs",
    )
    text = replace_once(
        text,
        'input string InpBtcD1File   = "btcusdsharp_d1.csv";\n',
        '''input string InpBtcD1File   = "btcusdsharp_d1.csv";
input string InpUs100M15File = "us100cashsharp_m15.csv";
input string InpUs500M15File = "us500cashsharp_m15.csv";
''',
        "index filenames",
    )
    btc_jobs = '''   if(InpExportBtc)
   {
      AddJob(jobs, InpBtcSymbol, PERIOD_M1,  InpBtcM1File,  InpExportM1  && InpBtcM1Enabled);
      AddJob(jobs, InpBtcSymbol, PERIOD_M5,  InpBtcM5File,  InpExportM5  && InpBtcM5Enabled);
      AddJob(jobs, InpBtcSymbol, PERIOD_M15, InpBtcM15File, InpExportM15);
      AddJob(jobs, InpBtcSymbol, PERIOD_H1,  InpBtcH1File,  InpExportH1);
      AddJob(jobs, InpBtcSymbol, PERIOD_H4,  InpBtcH4File,  InpExportH4  && InpBtcH4Enabled);
      AddJob(jobs, InpBtcSymbol, PERIOD_D1,  InpBtcD1File,  InpExportD1  && InpBtcD1Enabled);
   }
'''
    text = replace_once(
        text,
        btc_jobs,
        btc_jobs + '''   // Stage286 strict SHORT needs only confirmed M15 candles for these indices.
   if(InpExportUs100)
      AddJob(jobs, InpUs100Symbol, PERIOD_M15, InpUs100M15File, InpExportM15 && InpUs100M15Enabled);
   if(InpExportUs500)
      AddJob(jobs, InpUs500Symbol, PERIOD_M15, InpUs500M15File, InpExportM15 && InpUs500M15Enabled);
''',
        "BuildJobs index jobs",
    )
    text = replace_once(text, 'DebugLog("Initializing EA v1.34");', 'DebugLog("Initializing EA v1.35");', "init version")
    text = replace_once(
        text,
        'DebugLog("GoldSymbol=" + InpGoldSymbol + ", BtcSymbol=" + InpBtcSymbol);',
        '''DebugLog("GoldSymbol=" + InpGoldSymbol
            + ", BtcSymbol=" + InpBtcSymbol
            + ", Us100Symbol=" + InpUs100Symbol
            + ", Us500Symbol=" + InpUs500Symbol);''',
        "symbol log",
    )
    btc_log = '''   DebugLog("BtcM1Enabled=" + (InpBtcM1Enabled ? "true" : "false")
            + ", BtcM5Enabled=" + (InpBtcM5Enabled ? "true" : "false")
            + ", BtcH4Enabled=" + (InpBtcH4Enabled ? "true" : "false")
            + ", BtcD1Enabled=" + (InpBtcD1Enabled ? "true" : "false"));
'''
    text = replace_once(
        text,
        btc_log,
        btc_log + '''   DebugLog("Us100M15Enabled=" + (InpUs100M15Enabled ? "true" : "false")
            + ", Us500M15Enabled=" + (InpUs500M15Enabled ? "true" : "false")
            + ", ExportUs100=" + (InpExportUs100 ? "true" : "false")
            + ", ExportUs500=" + (InpExportUs500 ? "true" : "false"));
''',
        "index log",
    )
    text = replace_once(
        text,
        '''   bool ok = ExportAll();
   g_initialized_full_export = ok;
''',
        '''   bool ok = ExportAll();
   // Successful jobs can switch to append mode immediately. A failed optional
   // symbol keeps no remembered last-bar key and will retry a full export later.
   g_initialized_full_export = true;
   if(!ok)
      DebugLog("Initial export had one or more failures; failed jobs will retry without forcing successful files to rebuild.");
''',
        "initial append transition",
    )

    backup = source.with_suffix(source.suffix + ".v1.34.bak")
    shutil.copy2(source, backup)
    source.write_text(text.replace("\n", newline), encoding="utf-8", newline="")
    print(f"patched: {source}")
    print(f"backup : {backup}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ea", type=Path, help="Path to ExportOhlcToCsv.mq5 v1.34")
    args = parser.parse_args()
    patch(args.ea.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
