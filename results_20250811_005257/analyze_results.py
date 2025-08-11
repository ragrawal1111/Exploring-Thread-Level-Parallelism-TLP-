#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
import os

def analyze_results(csv_file):
    """Analyze the performance results and generate plots"""
    
    print("Loading results from:", csv_file)
    df = pd.read_csv(csv_file)
    
    print("\nAll results:")
    print(df)
    
    print("\nStatus summary:")
    print(df['Status'].value_counts())
    
    # Remove failed experiments
    success_df = df[df['Status'] == 'SUCCESS'].copy()
    
    if success_df.empty:
        print("\nNo successful experiments found! Check debug log for issues.")
        return
    
    print(f"\nFound {len(success_df)} successful experiments")
    
    # Convert to numeric
    success_df['SimSeconds'] = pd.to_numeric(success_df['SimSeconds'], errors='coerce')
    success_df['TotalCycles'] = pd.to_numeric(success_df['TotalCycles'], errors='coerce')
    success_df['AvgIPC'] = pd.to_numeric(success_df['AvgIPC'], errors='coerce')
    
    print("\nSuccessful dataset overview:")
    print(success_df.head())
    
    # Continue with analysis only if we have successful data...
    # [Rest of analysis code remains the same]

if __name__ == "__main__":
    csv_file = "performance_summary.csv"
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    
    if os.path.exists(csv_file):
        analyze_results(csv_file)
    else:
        print(f"Error: File {csv_file} not found!")
        sys.exit(1)
