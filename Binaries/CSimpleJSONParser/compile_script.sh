#!/bin/bash

# Compile base version for 64-bit with gcc
gcc example.c json.c -o example

# Compile base version for 32-bit with gcc
gcc -m32 example.c json.c -o example_32

# Compile base version for 64-bit with clang
clang example.c json.c -o example_clang

# Compile base version for 32-bit with clang
clang -m32 example.c json.c -o example_32_clang

# Compile with no optimization for 64-bit with gcc
gcc -g example.c json.c -o example_0 -O0

# Compile with no optimization for 32-bit with gcc
gcc -m32 -g example.c json.c -o example_0_32 -O0

# Compile with no optimization for 64-bit with clang
clang -g example.c json.c -o example_0_clang -O0

# Compile with no optimization for 32-bit with clang
clang -m32 -g example.c json.c -o example_0_32_clang -O0

# Compile with optimization for size for 64-bit with gcc
gcc -g example.c json.c -o example_s -Os

# Compile with optimization for size for 32-bit with gcc
gcc -m32 -g example.c json.c -o example_s_32 -Os

# Compile with optimization for size for 64-bit with clang
clang -g example.c json.c -o example_s_clang -Os

# Compile with optimization for size for 32-bit with clang
clang -m32 -g example.c json.c -o example_s_32_clang -Os

# Compile with optimization for speed for 64-bit with gcc
gcc -g example.c json.c -o example_3 -O3

# Compile with optimization for speed for 32-bit with gcc
gcc -m32 -g example.c json.c -o example_3_32 -O3

# Compile with optimization for speed for 64-bit with clang
clang -g example.c json.c -o example_3_clang -O3

# Compile with optimization for speed for 32-bit with clang
clang -m32 -g example.c json.c -o example_3_32_clang -O3

# Compile with level 1 optimization for 64-bit with gcc
gcc -g example.c json.c -o example_1 -O1

# Compile with level 1 optimization for 32-bit with gcc
gcc -m32 -g example.c json.c -o example_1_32 -O1

# Compile with level 1 optimization for 64-bit with clang
clang -g example.c json.c -o example_1_clang -O1

# Compile with level 1 optimization for 32-bit with clang
clang -m32 -g example.c json.c -o example_1_32_clang -O1

# Compile with level 2 optimization for 64-bit with gcc
gcc -g example.c json.c -o example_2 -O2

# Compile with level 2 optimization for 32-bit with gcc
gcc -m32 -g example.c json.c -o example_2_32 -O2

# Compile with level 2 optimization for 64-bit with clang
clang -g example.c json.c -o example_2_clang -O2

# Compile with level 2 optimization for 32-bit with clang
clang -m32 -g example.c json.c -o example_2_32_clang -O2

# Compile with aggressive optimization for 64-bit with gcc
gcc -g example.c json.c -o example_fast -Ofast

# Compile with aggressive optimization for 32-bit with gcc
gcc -m32 -g example.c json.c -o example_fast_32 -Ofast

# Compile with aggressive optimization for 64-bit with clang
clang -g example.c json.c -o example_fast_clang -Ofast

# Compile with aggressive optimization for 32-bit with clang
clang -m32 -g example.c json.c -o example_fast_32_clang -Ofast
