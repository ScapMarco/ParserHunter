#!/bin/bash

# Compile base version for 64-bit with gcc
gcc cJSON-master/test.c cJSON-master/cJSON.c -o cjson

# Compile base version for 32-bit with gcc
gcc -m32 cJSON-master/test.c cJSON-master/cJSON.c -o cjson_32

# Compile base version for 64-bit with clang
clang cJSON-master/test.c cJSON-master/cJSON.c -o cjson_clang

# Compile base version for 32-bit with clang
clang -m32 cJSON-master/test.c cJSON-master/cJSON.c -o cjson_32_clang

# Compile with no optimization for 64-bit with gcc
gcc -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_0 -O0

# Compile with no optimization for 32-bit with gcc
gcc -m32 -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_0_32 -O0

# Compile with no optimization for 64-bit with clang
clang -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_0_clang -O0

# Compile with no optimization for 32-bit with clang
clang -m32 -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_0_32_clang -O0

# Compile with optimization for size for 64-bit with gcc
gcc -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_s -Os

# Compile with optimization for size for 32-bit with gcc
gcc -m32 -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_s_32 -Os

# Compile with optimization for size for 64-bit with clang
clang -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_s_clang -Os

# Compile with optimization for size for 32-bit with clang
clang -m32 -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_s_32_clang -Os

# Compile with optimization for speed for 64-bit with gcc
gcc -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_3 -O3

# Compile with optimization for speed for 32-bit with gcc
gcc -m32 -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_3_32 -O3

# Compile with optimization for speed for 64-bit with clang
clang -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_3_clang -O3

# Compile with optimization for speed for 32-bit with clang
clang -m32 -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_3_32_clang -O3

# Compile with level 1 optimization for 64-bit with gcc
gcc -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_1 -O1

# Compile with level 1 optimization for 32-bit with gcc
gcc -m32 -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_1_32 -O1

# Compile with level 1 optimization for 64-bit with clang
clang -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_1_clang -O1

# Compile with level 1 optimization for 32-bit with clang
clang -m32 -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_1_32_clang -O1

# Compile with level 2 optimization for 64-bit with gcc
gcc -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_2 -O2

# Compile with level 2 optimization for 32-bit with gcc
gcc -m32 -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_2_32 -O2

# Compile with level 2 optimization for 64-bit with clang
clang -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_2_clang -O2

# Compile with level 2 optimization for 32-bit with clang
clang -m32 -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_2_32_clang -O2

# Compile with aggressive optimization for 64-bit with gcc
gcc -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_fast -Ofast

# Compile with aggressive optimization for 32-bit with gcc
gcc -m32 -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_fast_32 -Ofast

# Compile with aggressive optimization for 64-bit with clang
clang -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_fast_clang -Ofast

# Compile with aggressive optimization for 32-bit with clang
clang -m32 -g cJSON-master/test.c cJSON-master/cJSON.c -o cjson_fast_32_clang -Ofast
