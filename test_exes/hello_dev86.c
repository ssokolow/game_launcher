/** Minimal test program.
 *
 * (Apparently Dev86 doesn't like typed function parameters)
 *
 * Intended to be compiled using various compilers for the purpose of testing
 * code to detect and distinguish between DOS, Windows, and .NET EXEs.
 */

#include<stdio.h>

int main(argc, argv) {
    printf("Hello World");
    return 0;
}
