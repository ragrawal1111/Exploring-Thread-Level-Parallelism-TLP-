import argparse
import sys
import os

import m5
from m5.objects import *
from m5.util import addToPath, fatal, warn

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
    """Create the gem5 system"""
    
    # Create the system
    system = System()
    
    # Set the clock domain
    system.clk_domain = SrcClockDomain()
    system.clk_domain.clock = options.sys_clock
    system.clk_domain.voltage_domain = VoltageDomain()
    
    # Create memory ranges
    system.mem_ranges = [AddrRange('512MB')]
    
    # Create CPUs - simple timing CPU for basic simulation
    system.cpu = [TimingSimpleCPU() for i in range(options.num_cpus)]
    
    # Create memory bus
    system.membus = SystemXBar()
    
    # Simple cache setup
    if options.caches:
        for i, cpu in enumerate(system.cpu):
            # Create L1 caches
            cpu.icache = Cache(size="16kB", assoc=2, tag_latency=2, data_latency=2, response_latency=2, mshrs=4, tgts_per_mshr=20)
            cpu.dcache = Cache(size="64kB", assoc=2, tag_latency=2, data_latency=2, response_latency=2, mshrs=4, tgts_per_mshr=20)
            
            # Connect caches
            cpu.icache.mem_side = system.membus.cpu_side_ports
            cpu.dcache.mem_side = system.membus.cpu_side_ports
            cpu.icache_port = cpu.icache.cpu_side
            cpu.dcache_port = cpu.dcache.cpu_side
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
    
    # Create interrupt controllers
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
    
    # Parse arguments manually since we might not have common modules
    parser = argparse.ArgumentParser()
    parser.add_argument("--cores", type=int, default=1, help="Number of CPU cores")
    parser.add_argument("--op-lat", type=int, default=1, help="Operation latency")
    parser.add_argument("--issue-lat", type=int, default=1, help="Issue latency")
    parser.add_argument("--sys-clock", default="1GHz", help="System clock frequency")
    parser.add_argument("--caches", action="store_true", default=True, help="Use caches")
    
    # Parse known args and get the rest for the binary
    options, unknown = parser.parse_known_args()
    
    # The first unknown arg should be the binary, the rest are binary args
    if not unknown:
        fatal("No binary specified!")
    
    binary_path = unknown[0]
    binary_args = unknown[1:]
    
    # Set up options
    options.num_cpus = options.cores
    
    # Create the system
    system = create_system(options)
    
    # Get the process
    process = get_processes(binary_path, binary_args)
    
    # Assign process to first CPU, others idle
    system.cpu[0].workload = process
    system.cpu[0].createThreads()
    
    for i in range(1, len(system.cpu)):
        idle_process = Process()
        idle_process.executable = '/bin/echo'
        idle_process.cmd = ['echo', 'idle']
        system.cpu[i].workload = idle_process
        system.cpu[i].createThreads()
    
    # Set up the root SimObject
    root = Root(full_system=False, system=system)
    
    # Instantiate the simulation
    m5.instantiate()
    
    print("Beginning simulation!")
    print(f"Running {process.executable} with args: {process.cmd[1:]}")
    print(f"CPUs: {len(system.cpu)}")
    print(f"System clock: {options.sys_clock}")
    
    # Run the simulation
    exit_event = m5.simulate()
    
    print(f"Exiting @ tick {m5.curTick()} because {exit_event.getCause()}")

if __name__ == "__main__":
    main()
