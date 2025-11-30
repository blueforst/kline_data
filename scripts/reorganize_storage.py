#!/usr/bin/env python3
"""
Reorganize storage structure to merge resampled data into raw directory by period.

New Structure:
/Volumes/sandisk/kline_data/raw/binance/BTCUSDT/
├── 1s/         # Original 1-second data
│   ├── 2017/
│   ├── 2018/
│   └── ...
├── 1h/         # 1-hour resampled data
│   ├── 2020/
│   └── ...
├── 4h/         # 4-hour resampled data
│   └── ...
└── 1d/         # 1-day resampled data
    └── ...
"""

import os
import shutil
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def reorganize_storage(
    raw_base: str = "/Volumes/sandisk/kline_data/raw/binance/BTCUSDT",
    resampled_base: str = "/Volumes/sandisk/kline_data/resampled/binance/BTCUSDT",
    dry_run: bool = False
):
    """
    Reorganize storage structure by period.
    
    Args:
        raw_base: Base directory for raw data
        resampled_base: Base directory for resampled data
        dry_run: If True, only print what would be done without making changes
    """
    raw_path = Path(raw_base)
    resampled_path = Path(resampled_base)
    
    if not raw_path.exists():
        logger.error(f"Raw path does not exist: {raw_path}")
        return
    
    if not resampled_path.exists():
        logger.error(f"Resampled path does not exist: {resampled_path}")
        return
    
    # Step 1: Move existing year directories to 1s subdirectory
    logger.info("=" * 80)
    logger.info("Step 1: Organizing original 1s data")
    logger.info("=" * 80)
    
    # Create 1s directory
    target_1s = raw_path / "1s"
    if not dry_run:
        target_1s.mkdir(exist_ok=True)
        logger.info(f"Created directory: {target_1s}")
    else:
        logger.info(f"[DRY RUN] Would create directory: {target_1s}")
    
    # Move year directories to 1s
    year_dirs = [d for d in raw_path.iterdir() 
                 if d.is_dir() and d.name.isdigit() and len(d.name) == 4]
    
    for year_dir in sorted(year_dirs):
        target = target_1s / year_dir.name
        if dry_run:
            logger.info(f"[DRY RUN] Would move: {year_dir} -> {target}")
        else:
            if target.exists():
                logger.warning(f"Target already exists, skipping: {target}")
            else:
                shutil.move(str(year_dir), str(target))
                logger.info(f"Moved: {year_dir.name} -> 1s/{year_dir.name}")
    
    # Step 2: Move resampled data for each period
    logger.info("\n" + "=" * 80)
    logger.info("Step 2: Moving resampled data by period")
    logger.info("=" * 80)
    
    # Get all period directories from resampled
    period_dirs = [d for d in resampled_path.iterdir() if d.is_dir()]
    
    for period_dir in sorted(period_dirs):
        period_name = period_dir.name
        logger.info(f"\nProcessing period: {period_name}")
        
        # Create period directory in raw
        target_period = raw_path / period_name
        if not dry_run:
            target_period.mkdir(exist_ok=True)
            logger.info(f"  Created directory: {target_period}")
        else:
            logger.info(f"  [DRY RUN] Would create directory: {target_period}")
        
        # Move all year directories for this period
        year_dirs_in_period = [d for d in period_dir.iterdir() if d.is_dir()]
        
        for year_dir in sorted(year_dirs_in_period):
            source = year_dir
            target = target_period / year_dir.name
            
            if dry_run:
                logger.info(f"  [DRY RUN] Would move: {source} -> {target}")
            else:
                if target.exists():
                    logger.warning(f"  Target already exists, merging: {target}")
                    # Merge directories
                    for month_dir in year_dir.iterdir():
                        if month_dir.is_dir():
                            target_month = target / month_dir.name
                            if target_month.exists():
                                logger.warning(f"    Month exists, skipping: {target_month}")
                            else:
                                shutil.move(str(month_dir), str(target_month))
                                logger.info(f"    Merged month: {month_dir.name}")
                else:
                    shutil.move(str(source), str(target))
                    logger.info(f"  Moved: {period_name}/{year_dir.name}")
    
    # Step 3: Summary
    logger.info("\n" + "=" * 80)
    logger.info("Step 3: Summary")
    logger.info("=" * 80)
    
    if not dry_run:
        # List final structure
        logger.info("\nFinal structure:")
        for period_dir in sorted(raw_path.iterdir()):
            if period_dir.is_dir():
                year_count = len([d for d in period_dir.iterdir() if d.is_dir()])
                logger.info(f"  {period_dir.name}/: {year_count} year directories")
        
        # Check if resampled directory is empty
        remaining = list(resampled_path.rglob("*.parquet"))
        if remaining:
            logger.warning(f"\nWarning: {len(remaining)} parquet files still in resampled directory")
        else:
            logger.info("\n✓ All resampled data successfully moved")
            logger.info(f"You can now remove the empty resampled directory: {resampled_path}")
    else:
        logger.info("\n[DRY RUN] No changes were made. Run without --dry-run to apply changes.")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Reorganize kline data storage structure")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--raw-base",
        default="/Volumes/sandisk/kline_data/raw/binance/BTCUSDT",
        help="Base directory for raw data"
    )
    parser.add_argument(
        "--resampled-base",
        default="/Volumes/sandisk/kline_data/resampled/binance/BTCUSDT",
        help="Base directory for resampled data"
    )
    
    args = parser.parse_args()
    
    reorganize_storage(
        raw_base=args.raw_base,
        resampled_base=args.resampled_base,
        dry_run=args.dry_run
    )
