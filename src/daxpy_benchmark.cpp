#include <iostream>
#include <vector>
#include <thread>
#include <chrono>
#include <cstdlib>

class DaxpyBenchmark {
private:
    std::vector<double> x, y;
    size_t vector_size;
    size_t num_threads;
    double alpha;

public:
    DaxpyBenchmark(size_t size, size_t threads, double a) 
        : vector_size(size), num_threads(threads), alpha(a) {
        
        // Initialize vectors
        x.resize(vector_size);
        y.resize(vector_size);
        
        for (size_t i = 0; i < vector_size; ++i) {
            x[i] = static_cast<double>(i + 1);
            y[i] = static_cast<double>(vector_size - i);
        }
    }
    
    void daxpy_thread(size_t start, size_t end) {
        // Perform DAXPY: y = alpha * x + y
        for (size_t i = start; i < end; ++i) {
            y[i] = alpha * x[i] + y[i];
        }
    }
    
    void run_multithreaded() {
        std::vector<std::thread> threads;
        size_t chunk_size = vector_size / num_threads;
        
        auto start_time = std::chrono::high_resolution_clock::now();
        
        // Launch threads
        for (size_t t = 0; t < num_threads; ++t) {
            size_t start = t * chunk_size;
            size_t end = (t == num_threads - 1) ? vector_size : (t + 1) * chunk_size;
            
            threads.emplace_back(&DaxpyBenchmark::daxpy_thread, this, start, end);
        }
        
        // Wait for all threads
        for (auto& thread : threads) {
            thread.join();
        }
        
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
        
        std::cout << "Multi-threaded execution time: " << duration.count() << " microseconds" << std::endl;
    }
    
    void run_single_threaded() {
        auto start_time = std::chrono::high_resolution_clock::now();
        
        daxpy_thread(0, vector_size);
        
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end_time - start_time);
        
        std::cout << "Single-threaded execution time: " << duration.count() << " microseconds" << std::endl;
    }
    
    void print_results() const {
        std::cout << "First 10 results: ";
        for (size_t i = 0; i < std::min(static_cast<size_t>(10), vector_size); ++i) {
            std::cout << y[i] << " ";
        }
        std::cout << std::endl;
    }
};

int main(int argc, char* argv[]) {
    // Default values
    size_t vector_size = 1000;
    size_t num_threads = 1;
    double alpha = 2.5;
    
    // Parse command line arguments
    if (argc >= 2) vector_size = std::stoul(argv[1]);
    if (argc >= 3) num_threads = std::stoul(argv[2]);  
    if (argc >= 4) alpha = std::stod(argv[3]);
    
    std::cout << "DAXPY Benchmark" << std::endl;
    std::cout << "Vector size: " << vector_size << std::endl;
    std::cout << "Threads: " << num_threads << std::endl;
    std::cout << "Alpha: " << alpha << std::endl;
    std::cout << "Starting computation..." << std::endl;
    
    DaxpyBenchmark benchmark(vector_size, num_threads, alpha);
    
    if (num_threads > 1) {
        benchmark.run_multithreaded();
    } else {
        benchmark.run_single_threaded();
    }
    
    benchmark.print_results();
    std::cout << "Benchmark completed!" << std::endl;
    
    return 0;
}
