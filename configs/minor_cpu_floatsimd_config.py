import argparse
import sys
import os

import m5
from m5.objects import *
from m5.util import addToPath, fatal, warn

class CustomMinorFUPool(MinorFUPool):
    """Custom FU Pool with configurable FloatSimdFU"""
    def __init__(self, float_simd_op_lat=1, float_simd_issue_lat=6):
        super(CustomMinorFUPool, self).__init__()
        
        # Ensure opLat + issueLat = 7
        if float_simd_op_lat + float_simd_issue_lat != 7:
            fatal(f"FloatSimdFU opLat ({float_simd_op_lat}) + issueLat ({float_simd_issue_lat}) must equal 7")
        
        # Define the custom functional units
        self.funcUnits = [
            # Integer ALU - keep default
            MinorFU(opClasses=['IntAlu'], opLat=3, issueLat=1),
            
            # Integer multiply/divide
            MinorFU(opClasses=['IntMult', 'IntDiv'], opLat=3, issueLat=9),
            
            # Load/Store unit  
            MinorFU(opClasses=['MemRead', 'MemWrite'], opLat=1, issueLat=1),
            
            # Floating point ALU
            MinorFU(opClasses=['FloatAdd', 'FloatCmp', 'FloatCvt'], opLat=2, issueLat=1),
            
            # Floating point multiply/divide
            MinorFU(opClasses=['FloatMult', 'FloatDiv', 'FloatSqrt'], opLat=4, issueLat=1),
            
            # CUSTOMIZABLE FloatSimd functional unit
            MinorFU(opClasses=['FloatSIMD'], 
                   opLat=float_simd_op_lat, 
                   issueLat=float_simd_issue_lat),
            
            # Miscellaneous
            MinorFU(opClasses=['IprAccess', 'InstPrefetch'], opLat=1, issueLat=1),
        ]

def get_processes(binary_path, binary_args):
    """Create the process to be executed"""
    
    if not os.path.isfile(binary_path):
        fatal(f"Binary {binary_path} not found!")
    
    process = Process()
    process.executable = binary_path
    process.cmd = [binary_path] + binary_args
    process.cwd = os.getcwd()
    
    return process

def create_system(options):
    """Create the gem5 system with MinorCPU"""
    
    # Create the system
    system = System()
    
    # Set the clock domain
    system.clk_domain = SrcClockDomain()
    system.clk_domain.clock = options.sys_clock
    system.clk_domain.voltage_domain = VoltageDomain()
    
    # Create memory ranges
    system.mem_ranges = [AddrRange('512MB')]
    
    # Create MinorCPUs with custom FU pool
    system.cpu = []
    for i in range(options.num_cpus):
        cpu = MinorCPU()
        # Assign custom FU pool with specified FloatSimd configuration
        cpu.executeFuncUnits = CustomMinorFUPool(
            float_simd_op_lat=options.float_simd_op_lat,
            float_simd_issue_lat=options.float_simd_issue_lat
        )
        system.cpu.append(cpu)
    
    # Create memory bus
    system.membus = SystemXBar()
    
    # Cache setup
    if options.caches:
        # Create L2 cache if requested
        if options.l2cache:
            system.l2 = L2Cache(size='256kB', assoc=8)
            system.l2.mem_side = system.membus.cpu_side_ports
            system.tol2bus = L2XBar()
            system.l2.cpu_side = system.tol2bus.mem_side_ports
            
        for i, cpu in enumerate(system.cpu):
            # Create L1 caches for each CPU
            cpu.icache = Cache(size="32kB", assoc=2, tag_latency=2, data_latency=2, response_latency=2, mshrs=4, tgts_per_mshr=20)
            cpu.dcache = Cache(size="32kB", assoc=2, tag_latency=2, data_latency=2, response_latency=2, mshrs=4, tgts_per_mshr=20)
            
            # Connect caches
            cpu.icache_port = cpu.icache.cpu_side
            cpu.dcache_port = cpu.dcache.cpu_side
            
            if options.l2cache:
                cpu.icache.mem_side = system.tol2bus.cpu_side_ports
                cpu.dcache.mem_side = system.tol2bus.cpu_side_ports
            else:
                cpu.icache.mem_side = system.membus.cpu_side_ports
                cpu.dcache.mem_side = system.membus.cpu_side_ports
    else:
        # No caches - direct connection
        for cpu in system.cpu:
            cpu.icache_port = system.membus.cpu_side_ports
            cpu.dcache_port = system.membus.cpu_side_ports
    
    # Create memory controller
    system.mem_ctrl = MemCtrl()
    system.mem_ctrl.dram = DDR3_1600_8x8()
    system.mem_ctrl.dram.range = system.mem_ranges[0]
    system.mem_ctrl.port = system.membus.mem_side_ports
    
    # Create interrupt controllers for each CPU
    for cpu in system.cpu:
        cpu.createInterruptController()
        if hasattr(m5.objects, 'X86LocalApic'):
            cpu.interrupts[0].pio = system.membus.mem_side_ports
            cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
            cpu.interrupts[0].int_responder = system.membus.mem_side_ports
    
    # Connect system port
    system.system_port = system.membus.cpu_side_ports
    
    return system

def main():
    """Main simulation function"""
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-cpus", type=int, default=1, help="Number of CPU cores")
    parser.add_argument("--float-simd-op-lat", type=int, default=1, choices=range(1,7),
                       help="FloatSimdFU operation latency (1-6 cycles)")
    parser.add_argument("--float-simd-issue-lat", type=int, default=6, choices=range(1,7),
                       help="FloatSimdFU issue latency (1-6 cycles)")
    parser.add_argument("--sys-clock", default="1GHz", help="System clock frequency")
    parser.add_argument("--caches", action="store_true", default=True, help="Use caches")
    parser.add_argument("--l2cache", action="store_true", help="Use L2 cache")
    parser.add_argument("--cmd", required=True, help="Binary to execute")
    parser.add_argument("--options", default="", help="Arguments for the binary")
    
    options = parser.parse_args()
    
    # Validate FloatSimd configuration
    if options.float_simd_op_lat + options.float_simd_issue_lat != 7:
        fatal(f"FloatSimdFU opLat ({options.float_simd_op_lat}) + issueLat ({options.float_simd_issue_lat}) must equal 7")
    
    # Parse binary options
    binary_args = options.options.split() if options.options else []
    
    # Create the system
    system = create_system(options)
    
    # Get the process
    process = get_processes(options.cmd, binary_args)
    
    # Assign process to first CPU, others get a simple idle process
    system.cpu[0].workload = process
    system.cpu[0].createThreads()
    
    # Create idle processes for additional CPUs
    for i in range(1, len(system.cpu)):
        idle_process = Process()
        idle_process.executable = '/bin/sleep'
        idle_process.cmd = ['sleep', '1']
        system.cpu[i].workload = idle_process
        system.cpu[i].createThreads()
    
    # Set up the root SimObject
    root = Root(full_system=False, system=system)
    
    # Instantiate the simulation
    m5.instantiate()
    
    print("=" * 50)
    print("GEM5 MinorCPU FloatSimdFU Configuration")
    print("=" * 50)
    print(f"CPUs: {len(system.cpu)}")
    print(f"System clock: {options.sys_clock}")
    print(f"FloatSimdFU opLat: {options.float_simd_op_lat}")
    print(f"FloatSimdFU issueLat: {options.float_simd_issue_lat}")
    print(f"Caches enabled: {options.caches}")
    print(f"L2 cache enabled: {options.l2cache}")
    print(f"Binary: {process.executable}")
    print(f"Arguments: {process.cmd[1:]}")
    print("=" * 50)
    
    # Run the simulation
    exit_event = m5.simulate()
    
    print(f"Simulation completed @ tick {m5.curTick()}")
    print(f"Exit reason: {exit_event.getCause()}")

if __name__ == "__main__":
    main()
