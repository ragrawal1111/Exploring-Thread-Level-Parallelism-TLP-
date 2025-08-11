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
    
    print("\nDataset overview:")
    print(df.head())
    
    # Convert to numeric
    df['SimSeconds'] = pd.to_numeric(df['SimSeconds'])
    df['TotalCycles'] = pd.to_numeric(df['TotalCycles'])
    df['AvgIPC'] = pd.to_numeric(df['AvgIPC'])
    df['TotalInstructions'] = pd.to_numeric(df['TotalInstructions'])
    
    # Create visualizations
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    
    # 1. Simulation Time vs Thread Count for each configuration
    ax1 = axes[0, 0]
    for config in df['Configuration'].unique():
        config_data = df[df['Configuration'] == config]
        ax1.plot(config_data['Threads'], config_data['SimSeconds'], 
                marker='o', label=f"{config} ({config_data['OpLat'].iloc[0]}/{config_data['IssueLat'].iloc[0]})")
    ax1.set_xlabel('Number of Threads')
    ax1.set_ylabel('Simulation Time (seconds)')
    ax1.set_title('Simulation Time vs Thread Count')
    ax1.legend()
    ax1.grid(True)
    
    # 2. IPC vs Thread Count
    ax2 = axes[0, 1]
    for config in df['Configuration'].unique():
        config_data = df[df['Configuration'] == config]
        ax2.plot(config_data['Threads'], config_data['AvgIPC'], 
                marker='s', label=f"{config} ({config_data['OpLat'].iloc[0]}/{config_data['IssueLat'].iloc[0]})")
    ax2.set_xlabel('Number of Threads')
    ax2.set_ylabel('Instructions Per Cycle (IPC)')
    ax2.set_title('IPC vs Thread Count')
    ax2.legend()
    ax2.grid(True)
    
    # 3. Speedup analysis
    ax3 = axes[0, 2]
    for config in df['Configuration'].unique():
        config_data = df[df['Configuration'] == config].sort_values('Threads')
        single_thread_time = config_data[config_data['Threads'] == 1]['SimSeconds'].iloc[0]
        speedup = single_thread_time / config_data['SimSeconds']
        ax3.plot(config_data['Threads'], speedup, 
                marker='^', label=f"{config} ({config_data['OpLat'].iloc[0]}/{config_data['IssueLat'].iloc[0]})")
    
    # Add ideal speedup line
    threads = [1, 2, 4, 8]
    ax3.plot(threads, threads, 'k--', label='Ideal Speedup', alpha=0.7)
    ax3.set_xlabel('Number of Threads')
    ax3.set_ylabel('Speedup')
    ax3.set_title('Parallel Speedup')
    ax3.legend()
    ax3.grid(True)
    
    # 4. OpLat vs IssueLat heatmap for 4 threads
    ax4 = axes[1, 0]
    thread_4_data = df[df['Threads'] == 4]
    pivot_data = thread_4_data.pivot(index='OpLat', columns='IssueLat', values='SimSeconds')
    im = ax4.imshow(pivot_data.values, cmap='RdYlBu_r', aspect='auto')
    ax4.set_xticks(range(len(pivot_data.columns)))
    ax4.set_yticks(range(len(pivot_data.index)))
    ax4.set_xticklabels(pivot_data.columns)
    ax4.set_yticklabels(pivot_data.index)
    ax4.set_xlabel('Issue Latency')
    ax4.set_ylabel('Operation Latency')
    ax4.set_title('Simulation Time Heatmap (4 threads)')
    plt.colorbar(im, ax=ax4)
    
    # 5. Configuration comparison bar chart
    ax5 = axes[1, 1]
    thread_counts = [1, 2, 4, 8]
    x = np.arange(len(thread_counts))
    width = 0.12
    
    configs = df['Configuration'].unique()
    for i, config in enumerate(configs):
        config_data = df[df['Configuration'] == config]
        times = [config_data[config_data['Threads'] == t]['SimSeconds'].iloc[0] for t in thread_counts]
        ax5.bar(x + i*width, times, width, label=f"{config}")
    
    ax5.set_xlabel('Thread Count')
    ax5.set_ylabel('Simulation Time (seconds)')
    ax5.set_title('Performance Comparison Across Configurations')
    ax5.set_xticks(x + width * 2.5)
    ax5.set_xticklabels(thread_counts)
    ax5.legend()
    ax5.grid(True, axis='y')
    
    # 6. Efficiency analysis
    ax6 = axes[1, 2]
    for config in df['Configuration'].unique():
        config_data = df[df['Configuration'] == config].sort_values('Threads')
        single_thread_time = config_data[config_data['Threads'] == 1]['SimSeconds'].iloc[0]
        speedup = single_thread_time / config_data['SimSeconds']
        efficiency = speedup / config_data['Threads'] * 100
        ax6.plot(config_data['Threads'], efficiency, 
                marker='d', label=f"{config} ({config_data['OpLat'].iloc[0]}/{config_data['IssueLat'].iloc[0]})")
    
    ax6.set_xlabel('Number of Threads')
    ax6.set_ylabel('Parallel Efficiency (%)')
    ax6.set_title('Parallel Efficiency')
    ax6.legend()
    ax6.grid(True)
    ax6.set_ylim(0, 100)
    
    plt.tight_layout()
    plt.savefig('floatsimdfu_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Generate summary table
    print("\n" + "="*80)
    print("PERFORMANCE ANALYSIS SUMMARY")
    print("="*80)
    
    print("\n1. BEST CONFIGURATIONS BY METRIC:")
    print("-" * 50)
    
    # Best for single-thread performance
    single_thread = df[df['Threads'] == 1]
    best_single = single_thread.loc[single_thread['SimSeconds'].idxmin()]
    print(f"Best Single-Thread: {best_single['Configuration']} ({best_single['OpLat']}/{best_single['IssueLat']}) - {best_single['SimSeconds']:.6f}s")
    
    # Best for 8-thread performance
    eight_thread = df[df['Threads'] == 8]
    best_eight = eight_thread.loc[eight_thread['SimSeconds'].idxmin()]
    print(f"Best 8-Thread: {best_eight['Configuration']} ({best_eight['OpLat']}/{best_eight['IssueLat']}) - {best_eight['SimSeconds']:.6f}s")
    
    # Best overall speedup
    speedups = []
    for config in df['Configuration'].unique():
        config_data = df[df['Configuration'] == config]
        single_time = config_data[config_data['Threads'] == 1]['SimSeconds'].iloc[0]
        eight_time = config_data[config_data['Threads'] == 8]['SimSeconds'].iloc[0]
        speedup = single_time / eight_time
        speedups.append((config, speedup, config_data['OpLat'].iloc[0], config_data['IssueLat'].iloc[0]))
    
    best_speedup = max(speedups, key=lambda x: x[1])
    print(f"Best Speedup: {best_speedup[0]} ({best_speedup[2]}/{best_speedup[3]}) - {best_speedup[1]:.2f}x")
    
    print("\n2. DETAILED RESULTS TABLE:")
    print("-" * 50)
    summary_table = df.pivot_table(
        index=['Configuration', 'OpLat', 'IssueLat'],
        columns='Threads',
        values='SimSeconds',
        aggfunc='first'
    )
    print(summary_table)
    
    print("\n3. KEY OBSERVATIONS:")
    print("-" * 50)
    print("• OpLat vs IssueLat Tradeoffs:")
    print("  - Lower OpLat generally improves execution performance")
    print("  - Lower IssueLat improves instruction throughput")
    print("  - Balance depends on workload characteristics")
    
    print("\n• Thread Scaling Analysis:")
    for config in df['Configuration'].unique():
        config_data = df[df['Configuration'] == config].sort_values('Threads')
        single_time = config_data[config_data['Threads'] == 1]['SimSeconds'].iloc[0]
        eight_time = config_data[config_data['Threads'] == 8]['SimSeconds'].iloc[0]
        speedup = single_time / eight_time
        efficiency = speedup / 8 * 100
        print(f"  - {config}: {speedup:.2f}x speedup, {efficiency:.1f}% efficiency")

if __name__ == "__main__":
    csv_file = "performance_summary.csv"
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    
    if os.path.exists(csv_file):
        analyze_results(csv_file)
    else:
        print(f"Error: File {csv_file} not found!")
        sys.exit(1)
