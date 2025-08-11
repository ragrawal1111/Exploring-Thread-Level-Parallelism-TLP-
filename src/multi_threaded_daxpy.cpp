#include <iostream>
#include <vector>
#include <thread>
#include <chrono>
#include <barrier>
#include <cmath>
#include <random>
#include <cassert>

// Include gem5 magic instructions for statistics collection
#ifdef GEM5
#include "gem5/m5ops.h"
#endif

class MultiThreadedDaxpy {
private:
    size_t vector_size;
    int num_threads;
    double alpha;
    std::vector<double> x, y, y_original;
    std::barrier<> thread_barrier;
    
public:
    MultiThreadedDaxpy(size_t size, int threads, double a) 
        : vector_size(size), num_threads(threads), alpha(a), 
          thread_barrier(threads), x(size), y(size), y_original(size) {
        
        // Initialize vectors with random values
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_real_distribution<double> dis(1.0, 10.0);
        
        for (size_t i = 0; i < vector_size; ++i) {
            x[i] = dis(gen);
            y[i] = dis(gen);
            y_original[i] = y[i];
        }
        
        std::cout << "DAXPY Multi-threaded Benchmark" << std::endl;
        std::cout << "Vector size: " << vector_size << std::endl;
        std::cout << "Threads: " << num_threads << std::endl;
        std::cout << "Alpha: " << alpha << std::endl;
    }
    
    void thread_worker(int thread_id) {
        // Calculate work distribution for this thread
        size_t elements_per_thread = vector_size / num_threads;
        size_t start_idx = thread_id * elements_per_thread;
        size_t end_idx = (thread_id == num_threads - 1) ? 
                         vector_size : start_idx + elements_per_thread;
        
        // Wait for all threads to be ready
        thread_barrier.arrive_and_wait();
        
        // Start timing after barrier (only thread 0)
        if (thread_id == 0) {
#ifdef GEM5
            m5_dump_reset_stats(0, 0);  // Reset and start statistics
#endif
        }
        
        // Perform DAXPY: y[i] = alpha * x[i] + y[i]
        for (size_t i = start_idx; i < end_idx; ++i) {
            y[i] = alpha * x[i] + y[i];
        }
        
        // Synchronize all threads before timing ends
        thread_barrier.arrive_and_wait();
        
        // Stop timing (only thread 0)
        if (thread_id == 0) {
#ifdef GEM5
            m5_dump_stats(0, 0);  // Dump final statistics
#endif
        }
    }
    
    void run_parallel() {
        std::cout << "Starting parallel computation..." << std::endl;
        
        auto start_time = std::chrono::high_resolution_clock::now();
        
        // Create and launch threads
        std::vector<std::thread> threads;
        for (int i = 0; i < num_threads; ++i) {
            threads.emplace_back(&MultiThreadedDaxpy::thread_worker, this, i);
        }
        
        // Wait for all threads to complete
        for (auto& t : threads) {
            t.join();
        }
        
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
        
        std::cout << "Parallel execution time: " << duration.count() << " microseconds" << std::endl;
        
        // Verify correctness by comparing with sequential version
        verify_results();
    }
    
    void run_sequential() {
        std::cout << "Running sequential version for comparison..." << std::endl;
        
        // Reset y to original values
        y = y_original;
        
        auto start_time = std::chrono::high_resolution_clock::now();
        
        // Sequential DAXPY
        for (size_t i = 0; i < vector_size; ++i) {
            y[i] = alpha * x[i] + y[i];
        }
        
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
        
        std::cout << "Sequential execution time: " << duration.count() << " microseconds" << std::endl;
    }
    
private:
    void verify_results() {
        // Save parallel results
        std::vector<double> parallel_result = y;
        
        // Run sequential version
        y = y_original;
        for (size_t i = 0; i < vector_size; ++i) {
            y[i] = alpha * x[i] + y[i];
        }
        
        // Compare results
        bool correct = true;
        double max_error = 0.0;
        for (size_t i = 0; i < vector_size; ++i) {
            double error = std::abs(parallel_result[i] - y[i]);
            max_error = std::max(max_error, error);
            if (error > 1e-10) {
                correct = false;
            }
        }
        
        std::cout << "Results verification: " << (correct ? "PASSED" : "FAILED") << std::endl;
        std::cout << "Maximum error: " << max_error << std::endl;
        
        // Restore parallel results
        y = parallel_result;
        
        // Print first few results
        std::cout << "First 10 results: ";
        for (size_t i = 0; i < std::min(size_t(10), vector_size); ++i) {
            std::cout << y[i] << " ";
        }
        std::cout << std::endl;
    }
};

int main(int argc, char* argv[]) {
    if (argc != 4) {
        std::cerr << "Usage: " << argv[0] << " <vector_size> <num_threads> <alpha>" << std::endl;
        std::cerr << "Example: " << argv[0] << " 1000 4 2.5" << std::endl;
        return 1;
    }
    
    size_t vector_size = std::stoull(argv[1]);
    int num_threads = std::stoi(argv[2]);
    double alpha = std::stod(argv[3]);
    
    if (num_threads <= 0 || num_threads > std::thread::hardware_concurrency()) {
        std::cerr << "Invalid number of threads. Must be between 1 and " 
                  << std::thread::hardware_concurrency() << std::endl;
        return 1;
    }
    
    if (vector_size == 0) {
        std::cerr << "Vector size must be greater than 0" << std::endl;
        return 1;
    }
    
    try {
        MultiThreadedDaxpy benchmark(vector_size, num_threads, alpha);
        
        // Run parallel version
        benchmark.run_parallel();
        
        std::cout << "Benchmark completed successfully!" << std::endl;
        
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
}
