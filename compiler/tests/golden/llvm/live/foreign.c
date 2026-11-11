#include <stdarg.h>
#include <stdint.h>
extern int64_t neo_entry(void);
extern int64_t c_entry(int64_t);
int64_t add_foreign(int64_t base, ...) {
    va_list args;
    va_start(args, base);
    int value = va_arg(args, int);
    double real = va_arg(args, double);
    void *pointer = va_arg(args, void *);
    va_end(args);
    return pointer == 0 ? base + value + (int64_t)real : -1;
}
int main(void) { return neo_entry() != 42 || c_entry(10) != 11; }
