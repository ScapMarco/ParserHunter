#!/usr/bin/env bash
# gcc, 64-bit
gcc -g -O0   ./network_analyzer.c -o network_analyzer_O0
gcc -g -O1   ./network_analyzer.c -o network_analyzer_O1
gcc -g -O2   ./network_analyzer.c -o network_analyzer_O2
gcc -g -O3   ./network_analyzer.c -o network_analyzer_O3
gcc -g -Os   ./network_analyzer.c -o network_analyzer_Os
gcc -g -Ofast ./network_analyzer.c -o network_analyzer_Ofast

# gcc, 32-bit
gcc -g -O0 -m32   ./network_analyzer.c -o network_analyzer_O0_32
gcc -g -O1 -m32   ./network_analyzer.c -o network_analyzer_O1_32
gcc -g -O2 -m32   ./network_analyzer.c -o network_analyzer_O2_32
gcc -g -O3 -m32   ./network_analyzer.c -o network_analyzer_O3_32
gcc -g -Os -m32   ./network_analyzer.c -o network_analyzer_Os_32
gcc -g -Ofast -m32 ./network_analyzer.c -o network_analyzer_Ofast_32

# clang, 64-bit
clang -g -O0   ./network_analyzer.c -o network_analyzer_O0_clang
clang -g -O1   ./network_analyzer.c -o network_analyzer_O1_clang
clang -g -O2   ./network_analyzer.c -o network_analyzer_O2_clang
clang -g -O3   ./network_analyzer.c -o network_analyzer_O3_clang
clang -g -Os   ./network_analyzer.c -o network_analyzer_Os_clang
clang -g -Ofast ./network_analyzer.c -o network_analyzer_Ofast_clang

# clang, 32-bit
clang -g -O0 -m32   ./network_analyzer.c -o network_analyzer_O0_32_clang
clang -g -O1 -m32   ./network_analyzer.c -o network_analyzer_O1_32_clang
clang -g -O2 -m32   ./network_analyzer.c -o network_analyzer_O2_32_clang
clang -g -O3 -m32   ./network_analyzer.c -o network_analyzer_O3_32_clang
clang -g -Os -m32   ./network_analyzer.c -o network_analyzer_Os_32_clang
clang -g -Ofast -m32 ./network_analyzer.c -o network_analyzer_Ofast_32_clang

# --- Base (no -O) builds ---

# gcc, 64-bit
gcc      ./network_analyzer.c -o network_analyzer

# gcc, 32-bit
gcc -m32 ./network_analyzer.c -o network_analyzer_32

# clang, 64-bit
clang    ./network_analyzer.c -o network_analyzer_clang

# clang, 32-bit
clang -m32 ./network_analyzer.c -o network_analyzer_32_clang
