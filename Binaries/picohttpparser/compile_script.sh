#!/bin/bash

# Compile base version for 64-bit with gcc
gcc picohttpparser.c picotest/picotest.c test.c -o picohttpparser

# Compile base version for 32-bit with gcc
gcc -m32 picohttpparser.c picotest/picotest.c test.c -o picohttpparser_32

# Compile base version for 64-bit with clang
clang picohttpparser.c picotest/picotest.c test.c -o picohttpparser_clang

# Compile base version for 32-bit with clang
clang -m32 picohttpparser.c picotest/picotest.c test.c -o picohttpparser_32_clang

# Compile with no optimization for 64-bit with gcc
gcc -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_0 -O0

# Compile with no optimization for 32-bit with gcc
gcc -m32 -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_0_32 -O0

# Compile with no optimization for 64-bit with clang
clang -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_0_clang -O0

# Compile with no optimization for 32-bit with clang
clang -m32 -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_0_32_clang -O0

# Compile with optimization for size for 64-bit with gcc
gcc -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_s -Os

# Compile with optimization for size for 32-bit with gcc
gcc -m32 -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_s_32 -Os

# Compile with optimization for size for 64-bit with clang
clang -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_s_clang -Os

# Compile with optimization for size for 32-bit with clang
clang -m32 -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_s_32_clang -Os

# Compile with optimization for speed for 64-bit with gcc
gcc -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_3 -O3

# Compile with optimization for speed for 32-bit with gcc
gcc -m32 -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_3_32 -O3

# Compile with optimization for speed for 64-bit with clang
clang -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_3_clang -O3

# Compile with optimization for speed for 32-bit with clang
clang -m32 -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_3_32_clang -O3

# Compile with level 1 optimization for 64-bit with gcc
gcc -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_1 -O1

# Compile with level 1 optimization for 32-bit with gcc
gcc -m32 -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_1_32 -O1

# Compile with level 1 optimization for 64-bit with clang
clang -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_1_clang -O1

# Compile with level 1 optimization for 32-bit with clang
clang -m32 -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_1_32_clang -O1

# Compile with level 2 optimization for 64-bit with gcc
gcc -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_2 -O2

# Compile with level 2 optimization for 32-bit with gcc
gcc -m32 -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_2_32 -O2

# Compile with level 2 optimization for 64-bit with clang
clang -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_2_clang -O2

# Compile with level 2 optimization for 32-bit with clang
clang -m32 -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_2_32_clang -O2

# Compile with aggressive optimization for 64-bit with gcc
gcc -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_fast -Ofast

# Compile with aggressive optimization for 32-bit with gcc
gcc -m32 -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_fast_32 -Ofast

# Compile with aggressive optimization for 64-bit with clang
clang -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_fast_clang -Ofast

# Compile with aggressive optimization for 32-bit with clang
clang -m32 -g picohttpparser.c picotest/picotest.c test.c -o picohttpparser_fast_32_clang -Ofast
