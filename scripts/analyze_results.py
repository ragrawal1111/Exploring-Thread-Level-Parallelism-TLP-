#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import sys

def load_and_analyze_results(csv_file):
    """Load simulation results and perform analysis"""
    
    if not os.path.exists(csv_file):
        print(f"Results file {csv_file} not found!")
        return None
    
    df = pd.read_csv(csv_file)
    
    # Filter out error rows
    df = df[df['sim_ticks'] != 'ERROR'].copy()
    df['sim_ticks'] = pd.to_numeric(df['sim_ticks'])
    df['sim_seconds'] = pd.to_numeric(df['sim_seconds'])
    df['instructions'] = pd.to_numeric(df['instructions'])
    df['cycles'] = pd.to_numeric(df['cycles'])
    
    # Calculate derived metrics
    df['ipc'] = df['instructions'] / df['cycles'].replace(0, np.nan)
    df['speedup'] = 1.0  # Will be calculated per configuration
    
    # Calculate speedup relative to single thread
    speedups = []
    for _, row in df.iterrows():
        baseline = df[(df['opLat'] == row['opLat']) & 
                      (df['issueLat'] == row['issueLat']) & 
                      (df['threads'] == 1)]
        if not baseline.empty:
            baseline_time = baseline['sim_seconds'].iloc[0]
            speedup = baseline_time / row['sim_seconds'] if row['sim_seconds'] > 0 else 0
        else:
            speedup = 1.0
        speedups.append(speedup)
    
    df['speedup'] = speedups
    return df

def create_performance_plots(df, output_dir):
    """Create performance analysis plots"""
    
    if df is None or df.empty:
        print("No data to plot!")
        return
    
    plt.style.use('seaborn-v0_8')
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('FloatSimdFU Design Space Exploration Results', fontsize=16, fontweight='bold')
    
    # 1. Speedup vs Thread Count
    configs = df.groupby(['opLat', 'issueLat'])
    colors = plt.cm.viridis(np.linspace(0, 1, len(configs)))
    
    for i, ((op_lat, issue_lat), group) in enumerate(configs):
        ax1.plot(group['threads'], group['speedup'], 
                marker='o', label=f'({op_lat},{issue_lat})', 
                color=colors[i], linewidth=2, markersize=6)
    
    ax1.plot([1, 8], [1, 8], 'k--', alpha=0.5, label='Ideal')
    ax1.set_xlabel('Thread Count')
    ax1.set_ylabel('Speedup')
    ax1.set_title('Speedup vs Thread Count')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 2. IPC vs Thread Count
    for i, ((op_lat, issue_lat), group) in enumerate(configs):
        ax2.plot(group['threads'], group['ipc'], 
                marker='s', label=f'({op_lat},{issue_lat})', 
                color=colors[i], linewidth=2, markersize=6)
    
    ax2.set_xlabel('Thread Count')
    ax2.set_ylabel('Instructions Per Cycle (IPC)')
    ax2.set_title('IPC vs Thread Count')
    ax2.grid(True, alpha=0.3)
    
    # 3. Configuration Comparison (8 threads)
    eight_thread_data = df[df['threads'] == 8].copy()
    if not eight_thread_data.empty:
        config_labels = [f"({row['opLat']},{row['issueLat']})" 
                        for _, row in eight_thread_data.iterrows()]
        ax3.bar(range(len(eight_thread_data)), eight_thread_data['speedup'], 
                color=colors[:len(eight_thread_data)], alpha=0.7)
        ax3.set_xlabel('Configuration (opLat, issueLat)')
        ax3.set_ylabel('Speedup (8 threads)')
        ax3.set_title('Configuration Performance Comparison')
        ax3.set_xticks(range(len(config_labels)))
        ax3.set_xticklabels(config_labels, rotation=45)
        ax3.grid(True, axis='y', alpha=0.3)
    
    # 4. Efficiency Heatmap
    pivot_data = df.pivot_table(values='speedup', index=['opLat', 'issueLat'], 
                               columns='threads', fill_value=0)
    efficiency_data = pivot_data.div(pivot_data.columns, axis=1)
    
    im = ax4.imshow(efficiency_data.values, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
    ax4.set_xlabel('Thread Count')
    ax4.set_ylabel('Configuration')
    ax4.set_title('Parallel Efficiency Heatmap')
    
    # Set labels
    ax4.set_xticks(range(len(efficiency_data.columns)))
    ax4.set_xticklabels(efficiency_data.columns)
    ax4.set_yticks(range(len(efficiency_data.index)))
    ax4.set_yticklabels([f"({op},{iss})" for op, iss in efficiency_data.index])
    
    plt.colorbar(im, ax=ax4, label='Efficiency')
    
    plt.tight_layout()
    plot_file = os.path.join(output_dir, 'performance_analysis.png')
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"Performance plots saved to: {plot_file}")
    plt.show()

def print_summary_table(df):
    """Print summary performance table"""
    
    if df is None or df.empty:
        print("No data to summarize!")
        return
    
    print("\n" + "="*80)
    print("PERFORMANCE SUMMARY TABLE")
    print("="*80)
    
    # Speedup table
    speedup_table = df.pivot_table(values='speedup', index=['opLat', 'issueLat'], 
                                  columns='threads', fill_value=0)
    print("\nSpeedup Table:")
    print(speedup_table.round(3))
    
    # IPC table
    ipc_table = df.pivot_table(values='ipc', index=['opLat', 'issueLat'], 
                              columns='threads', fill_value=0)
    print("\nIPC Table:")
    print(ipc_table.round(3))
    
    # Best configurations
    print(f"\n{'Thread Count':<12} {'Best Config':<15} {'Max Speedup':<12} {'Best IPC':<10}")
    print("-" * 55)
    
    for threads in sorted(df['threads'].unique()):
        thread_data = df[df['threads'] == threads]
        best_speedup = thread_data.loc[thread_data['speedup'].idxmax()]
        best_ipc = thread_data.loc[thread_data['ipc'].idxmax()]
        
        print(f"{threads:<12} ({int(best_speedup['opLat'])},{int(best_speedup['issueLat'])})"
              f"{'(' + str(int(best_ipc['opLat'])) + ',' + str(int(best_ipc['issueLat'])) + ')':<15} "
              f"{best_speedup['speedup']:<12.3f} {best_ipc['ipc']:<10.3f}")

def main():
    output_dir = os.path.expanduser("~/gem5_assignment/outputs")
    csv_file = os.path.join(output_dir, "simulation_summary.csv")
    
    print("Loading simulation results...")
    df = load_and_analyze_results(csv_file)
    
    if df is not None:
        print(f"Loaded {len(df)} simulation results")
        print_summary_table(df)
        create_performance_plots(df, output_dir)
    else:
        print("No valid results found!")

if __name__ == "__main__":
    main()
