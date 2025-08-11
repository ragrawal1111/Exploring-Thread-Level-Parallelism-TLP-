# Makefile for multi-threaded DAXPY benchmark

CXX = g++
CXXFLAGS = -std=c++20 -Wall -Wextra -O3 -march=native
LDFLAGS = -pthread

# Directories
SRC_DIR = src
BUILD_DIR = build

# Source and target files
SOURCES = $(SRC_DIR)/multi_threaded_daxpy.cpp
TARGET = $(SRC_DIR)/multi_threaded_daxpy

# Gem5 magic instruction support (optional)
ifdef USE_GEM5
    CXXFLAGS += -DGEM5 -I$(GEM5_ROOT)/include
    GEM5_LIB = $(GEM5_ROOT)/util/m5/build/x86/out/m5.o
    LDFLAGS += $(GEM5_LIB)
endif

.PHONY: all clean debug test help

# Default target
all: $(TARGET)

# Build the main target
$(TARGET): $(SOURCES) | create_dirs
	$(CXX) $(CXXFLAGS) -o $@ $< $(LDFLAGS)
	@echo "Built multi-threaded DAXPY benchmark: $@"

# Create necessary directories
create_dirs:
	@mkdir -p $(SRC_DIR)
	@mkdir -p $(BUILD_DIR)

# Debug build
debug: CXXFLAGS += -g -DDEBUG -O0
debug: $(TARGET)
	@echo "Built debug version"

# Test the benchmark
test: $(TARGET)
	@echo "Running test with small vector (size=100, threads=2, alpha=2.5)..."
	./$(TARGET) 100 2 2.5
	@echo "Running test with medium vector (size=1000, threads=4, alpha=1.5)..."
	./$(TARGET) 1000 4 1.5

# Test with gem5 (assumes you have gem5 available)
test-gem5: $(TARGET)
	@echo "Running gem5 simulation test..."
	../gem5/build/X86/gem5.opt \
		--outdir=test_output \
		configs/minor_cpu_floatsimd_config.py \
		--num-cpus=2 \
		--float-simd-op-lat=3 \
		--float-simd-issue-lat=4 \
		--caches \
		--cmd=$(TARGET) \
		--options="1000 2 2.5"

# Clean build artifacts
clean:
	rm -f $(TARGET)
	rm -rf $(BUILD_DIR)
	rm -rf test_output
	rm -rf m5out*
	rm -rf results_*
	@echo "Cleaned build artifacts"

# Install gem5 m5 utility (if gem5 root is available)
install-m5:
	@if [ -z "$(GEM5_ROOT)" ]; then \
		echo "Error: GEM5_ROOT not set. Please set it to your gem5 installation directory."; \
		exit 1; \
	fi
	@echo "Building gem5 m5 utility..."
	cd $(GEM5_ROOT)/util/m5 && scons build/x86/out/m5.o
	@echo "Gem5 m5 utility built. Use 'make USE_GEM5=1' to build with gem5 support."

# Run performance experiments
run-experiments: $(TARGET)
	@echo "Starting automated performance experiments..."
	@if [ ! -f "configs/minor_cpu_floatsimd_config.py" ]; then \
		echo "Error: Configuration script not found. Please ensure configs/minor_cpu_floatsimd_config.py exists."; \
		exit 1; \
	fi
	./run_experiments.sh

# Validate build environment
check-env:
	@echo "Checking build environment..."
	@which $(CXX) > /dev/null || (echo "Error: $(CXX) not found" && exit 1)
	@$(CXX) --version | head -1
	@echo "C++ compiler: OK"
	@echo "C++20 support: $(shell $(CXX) -std=c++20 -dM -E - < /dev/null | grep -c __cplusplus)"
	@echo "Thread support: $(shell echo '#include <thread>' | $(CXX) -E - > /dev/null 2>&1 && echo 'OK' || echo 'MISSING')"
	@if [ ! -z "$(GEM5_ROOT)" ]; then \
		echo "Gem5 root: $(GEM5_ROOT)"; \
		if [ -f "$(GEM5_ROOT)/build/X86/gem5.opt" ]; then \
			echo "Gem5 binary: OK"; \
		else \
			echo "Gem5 binary: NOT FOUND"; \
		fi \
	else \
		echo "Gem5 root: NOT SET (optional)"; \
	fi

# Help target
help:
	@echo "Multi-threaded DAXPY Benchmark Build System"
	@echo ""
	@echo "Available targets:"
	@echo "  all              - Build the benchmark (default)"
	@echo "  debug            - Build with debug symbols and no optimization"
	@echo "  test             - Run basic functionality tests"
	@echo "  test-gem5        - Run a gem5 simulation test"
	@echo "  run-experiments  - Run full automated performance experiments"
	@echo "  clean            - Remove build artifacts"
	@echo "  check-env        - Check build environment"
	@echo "  install-m5       - Build gem5 m5 utility (requires GEM5_ROOT)"
	@echo "  help             - Show this help message"
	@echo ""
	@echo "Environment variables:"
	@echo "  GEM5_ROOT        - Path to gem5 installation (optional)"
	@echo "  USE_GEM5=1       - Enable gem5 magic instruction support"
	@echo ""
	@echo "Examples:"
	@echo "  make                    # Build benchmark"
	@echo "  make debug             # Build debug version"
	@echo "  make USE_GEM5=1        # Build with gem5 support"
	@echo "  make test              # Test functionality"
	@echo "  GEM5_ROOT=/path/to/gem5 make install-m5"

# Show configuration
show-config:
	@echo "Build Configuration:"
	@echo "  CXX: $(CXX)"
	@echo "  CXXFLAGS: $(CXXFLAGS)"
	@echo "  LDFLAGS: $(LDFLAGS)"
	@echo "  TARGET: $(TARGET)"
	@echo "  USE_GEM5: $(USE_GEM5)"
	@echo "  GEM5_ROOT: $(GEM5_ROOT)"
