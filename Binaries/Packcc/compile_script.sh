#!/usr/bin/env bash

# gcc, 64-bit
gcc -g -O0    ./packcc.c -o packcc_O0
gcc -g -O1    ./packcc.c -o packcc_O1
gcc -g -O2    ./packcc.c -o packcc_O2
gcc -g -O3    ./packcc.c -o packcc_O3
gcc -g -Os    ./packcc.c -o packcc_Os
gcc -g -Ofast ./packcc.c -o packcc_Ofast

# gcc, 32-bit
gcc -g -O0 -m32    ./packcc.c -o packcc_O0_32
gcc -g -O1 -m32    ./packcc.c -o packcc_O1_32
gcc -g -O2 -m32    ./packcc.c -o packcc_O2_32
gcc -g -O3 -m32    ./packcc.c -o packcc_O3_32
gcc -g -Os -m32    ./packcc.c -o packcc_Os_32
gcc -g -Ofast -m32 ./packcc.c -o packcc_Ofast_32

# clang, 64-bit
clang -g -O0    ./packcc.c -o packcc_O0_clang
clang -g -O1    ./packcc.c -o packcc_O1_clang
clang -g -O2    ./packcc.c -o packcc_O2_clang
clang -g -O3    ./packcc.c -o packcc_O3_clang
clang -g -Os    ./packcc.c -o packcc_Os_clang
clang -g -Ofast ./packcc.c -o packcc_Ofast_clang

# clang, 32-bit
clang -g -O0 -m32    ./packcc.c -o packcc_O0_32_clang
clang -g -O1 -m32    ./packcc.c -o packcc_O1_32_clang
clang -g -O2 -m32    ./packcc.c -o packcc_O2_32_clang
clang -g -O3 -m32    ./packcc.c -o packcc_O3_32_clang
clang -g -Os -m32    ./packcc.c -o packcc_Os_32_clang
clang -g -Ofast -m32 ./packcc.c -o packcc_Ofast_32_clang

# --- Base (no -O) builds ---

# gcc, 64-bit
gcc      ./packcc.c -o packcc

# gcc, 32-bit
gcc -m32 ./packcc.c -o packcc_32

# clang, 64-bit
clang    ./packcc.c -o packcc_clang

# clang, 32-bit
clang -m32 ./packcc.c -o packcc_32_clang