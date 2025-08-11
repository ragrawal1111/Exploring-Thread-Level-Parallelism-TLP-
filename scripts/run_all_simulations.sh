#!/bin/bash

# Configuration
PROJECT_DIR=~/gem5_assignment
GEM5_BINARY=~/gem5/build/X86/gem5.opt
CONFIG_SCRIPT=$PROJECT_DIR/configs/daxpy_gem5_config.py
BENCHMARK_BINARY=$PROJECT_DIR/src/daxpy_benchmark
OUTPUT_DIR=$PROJECT_DIR/outputs

# Create output directory
mkdir -p $OUTPUT_DIR

# Configuration arrays
CONFIGS=("1,6" "2,5" "3,4" "4,3" "5,2" "6,1")
THREAD_COUNTS=(1 2 4 8)
VECTOR_SIZE=50000

echo "=== FloatSimdFU Design Space Exploration ==="
echo "Vector size: $VECTOR_SIZE"
echo "Configurations: ${CONFIGS[@]}"
echo "Thread counts: ${THREAD_COUNTS[@]}"
echo "GEM5 Binary: $GEM5_BINARY"
echo "=============================================="

# Check if gem5 binary exists
if [ ! -f "$GEM5_BINARY" ]; then
    echo "ERROR: gem5 binary not found at $GEM5_BINARY"
    echo "Please check the path and build gem5 first"
    exit 1
fi

# Results summary file
SUMMARY_FILE=$OUTPUT_DIR/simulation_summary.csv
echo "opLat,issueLat,threads,sim_ticks,sim_seconds,instructions,cycles" > $SUMMARY_FILE

# Run simulations
for config in "${CONFIGS[@]}"; do
    IFS=',' read -r op_lat issue_lat <<< "$config"
    
    for threads in "${THREAD_COUNTS[@]}"; do
        echo
        echo "Running: opLat=$op_lat, issueLat=$issue_lat, threads=$threads"
        echo "----------------------------------------"
        
        # Output files
        output_dir="$OUTPUT_DIR/sim_${op_lat}_${issue_lat}_t${threads}"
        mkdir -p $output_dir
        
        stdout_file="$output_dir/stdout.txt"
        stderr_file="$output_dir/stderr.txt"
        stats_file="$output_dir/stats.txt"
        
        # Run simulation with correct arguments
        $GEM5_BINARY \
            --outdir=$output_dir \
            --stats-file=$stats_file \
            $CONFIG_SCRIPT \
            --cores=$threads \
            --op-lat=$op_lat \
            --issue-lat=$issue_lat \
            $BENCHMARK_BINARY \
            --vector-size=$VECTOR_SIZE \
            --threads=$threads \
            > $stdout_file 2> $stderr_file
        
        if [ $? -eq 0 ]; then
            echo "✓ Simulation completed successfully"
            
            # Extract key statistics with better error handling
            sim_ticks=$(grep "sim_ticks" $output_dir/stats.txt 2>/dev/null | awk '{print $2}' | head -1)
            sim_seconds=$(grep "sim_seconds" $output_dir/stats.txt 2>/dev/null | awk '{print $2}' | head -1)
            instructions=$(grep "system.cpu.committedInsts\|system.cpu\[0\].committedInsts" $output_dir/stats.txt 2>/dev/null | awk '{print $2}' | head -1)
            cycles=$(grep "system.cpu.numCycles\|system.cpu\[0\].numCycles" $output_dir/stats.txt 2>/dev/null | awk '{print $2}' | head -1)
            
            # Use default values if extraction failed
            sim_ticks=${sim_ticks:-ERROR}
            sim_seconds=${sim_seconds:-ERROR}
            instructions=${instructions:-ERROR}
            cycles=${cycles:-ERROR}
            
            echo "$op_lat,$issue_lat,$threads,$sim_ticks,$sim_seconds,$instructions,$cycles" >> $SUMMARY_FILE
            
        else
            echo "✗ Simulation failed - check $stderr_file"
            echo "$op_lat,$issue_lat,$threads,ERROR,ERROR,ERROR,ERROR" >> $SUMMARY_FILE
        fi
    done
done

echo
echo "=== All Simulations Complete ==="
echo "Results summary: $SUMMARY_FILE"
echo "Individual results in: $OUTPUT_DIR"
echo "================================="
