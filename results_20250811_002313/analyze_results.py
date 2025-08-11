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
    
    # Remove failed experiments
    df = df[df['SimSeconds'] != 'FAILED']
    df = df[df['SimSeconds'] != 'ERROR']
    df = df[df['SimSeconds'] != 'N/A']
    
    # Convert to numeric
    df['SimSeconds'] = pd.to_numeric(df['SimSeconds'])
    df['TotalCycles'] = pd.to_numeric(df['TotalCycles'])
    df['AvgIPC'] = pd.to_numeric(df['AvgIPC'])
    
    print("\nDataset overview:")
    print(df.head())
    
    # Analysis 1: Performance vs Configuration for different thread counts
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('FloatSimdFU Performance Analysis', fontsize=16)
    
    # Plot 1: Simulation time vs OpLat for different thread counts
    for threads in sorted(df['Threads'].unique()):
        thread_data = df[df['Threads'] == threads]
        axes[0,0].plot(thread_data['OpLat'], thread_data['SimSeconds'], 
                      marker='o', label=f'{threads} threads')
    axes[0,0].set_xlabel('Operation Latency (cycles)')
    axes[0,0].set_ylabel('Simulation Time (seconds)')
    axes[0,0].set_title('Simulation Time vs OpLat')
    axes[0,0].legend()
    axes[0,0].grid(True, alpha=0.3)
    
    # Plot 2: IPC vs OpLat
    for threads in sorted(df['Threads'].unique()):
        thread_data = df[df['Threads'] == threads]
        axes[0,1].plot(thread_data['OpLat'], thread_data['AvgIPC'], 
                      marker='s', label=f'{threads} threads')
    axes[0,1].set_xlabel('Operation Latency (cycles)')
    axes[0,1].set_ylabel('Instructions Per Cycle (IPC)')
    axes[0,1].set_title('IPC vs OpLat')
    axes[0,1].legend()
    axes[0,1].grid(True, alpha=0.3)
    
    # Plot 3: Speedup calculation (comparing to single thread)
    single_thread_data = df[df['Threads'] == 1]
    speedup_data = []
    
    for _, config in single_thread_data.iterrows():
        base_time = config['SimSeconds']
        op_lat = config['OpLat']
        
        for threads in [2, 4, 8]:
            thread_row = df[(df['Threads'] == threads) & (df['OpLat'] == op_lat)]
            if not thread_row.empty:
                speedup = base_time / thread_row.iloc[0]['SimSeconds']
                speedup_data.append({
                    'OpLat': op_lat,
                    'IssueLat': config['IssueLat'],
                    'Threads': threads,
                    'Speedup': speedup
                })
    
    speedup_df = pd.DataFrame(speedup_data)
    
    if not speedup_df.empty:
        for threads in sorted(speedup_df['Threads'].unique()):
            thread_data = speedup_df[speedup_df['Threads'] == threads]
            axes[1,0].plot(thread_data['OpLat'], thread_data['Speedup'], 
                          marker='^', label=f'{threads} threads')
    axes[1,0].set_xlabel('Operation Latency (cycles)')
    axes[1,0].set_ylabel('Parallel Speedup')
    axes[1,0].set_title('Parallel Speedup vs OpLat')
    axes[1,0].legend()
    axes[1,0].grid(True, alpha=0.3)
    axes[1,0].axhline(y=1, color='r', linestyle='--', alpha=0.5, label='No speedup')
    
    # Plot 4: Efficiency (Speedup/Threads)
    if not speedup_df.empty:
        speedup_df['Efficiency'] = speedup_df['Speedup'] / speedup_df['Threads']
        for threads in sorted(speedup_df['Threads'].unique()):
            thread_data = speedup_df[speedup_df['Threads'] == threads]
            axes[1,1].plot(thread_data['OpLat'], thread_data['Efficiency'], 
                          marker='d', label=f'{threads} threads')
    axes[1,1].set_xlabel('Operation Latency (cycles)')
    axes[1,1].set_ylabel('Parallel Efficiency')
    axes[1,1].set_title('Parallel Efficiency vs OpLat')
    axes[1,1].legend()
    axes[1,1].grid(True, alpha=0.3)
    axes[1,1].axhline(y=1, color='r', linestyle='--', alpha=0.5, label='Perfect efficiency')
    
    plt.tight_layout()
    plt.savefig('floatsimd_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Generate summary table
    print("\n" + "="*80)
    print("PERFORMANCE SUMMARY")
    print("="*80)
    
    # Best configuration analysis
    print("\nBest configurations by metric:")
    
    # Best single-thread performance
    single_best = df[df['Threads'] == 1].loc[df[df['Threads'] == 1]['SimSeconds'].idxmin()]
    print(f"Best single-thread time: OpLat={single_best['OpLat']}, IssueLat={single_best['IssueLat']}, "
          f"Time={single_best['SimSeconds']:.6f}s")
    
    # Best IPC
    best_ipc = df.loc[df['AvgIPC'].idxmax()]
    print(f"Best IPC: OpLat={best_ipc['OpLat']}, IssueLat={best_ipc['IssueLat']}, "
          f"Threads={best_ipc['Threads']}, IPC={best_ipc['AvgIPC']:.4f}")
    
    # Best speedup
    if not speedup_df.empty:
        best_speedup = speedup_df.loc[speedup_df['Speedup'].idxmax()]
        print(f"Best speedup: OpLat={best_speedup['OpLat']}, IssueLat={best_speedup['IssueLat']}, "
              f"Threads={best_speedup['Threads']}, Speedup={best_speedup['Speedup']:.2f}x")
    
    # Configuration comparison table
    print(f"\n{'Config':<20} {'OpLat':<6} {'IssueLat':<8} {'1T Time':<10} {'2T Time':<10} {'4T Time':<10} {'8T Time':<10}")
    print("-" * 80)
    
    for config in df['Configuration'].unique():
        config_data = df[df['Configuration'] == config].sort_values('Threads')
        if len(config_data) > 0:
            op_lat = config_data.iloc[0]['OpLat']
            issue_lat = config_data.iloc[0]['IssueLat']
            
            times = {}
            for _, row in config_data.iterrows():
                times[row['Threads']] = row['SimSeconds']
            
            print(f"{config:<20} {op_lat:<6} {issue_lat:<8} "
                  f"{times.get(1, 'N/A'):<10} {times.get(2, 'N/A'):<10} "
                  f"{times.get(4, 'N/A'):<10} {times.get(8, 'N/A'):<10}")

if __name__ == "__main__":
    csv_file = "performance_summary.csv"
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    
    if os.path.exists(csv_file):
        analyze_results(csv_file)
    else:
        print(f"Error: File {csv_file} not found!")
        sys.exit(1)
