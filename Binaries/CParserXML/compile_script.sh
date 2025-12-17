#!/bin/bash

# Compile base version for 64-bit with gcc
gcc main.c parse_xml.c xml_content.c -o parse_xml

# Compile base version for 32-bit with gcc
gcc -m32 main.c parse_xml.c xml_content.c -o parse_xml_32

# Compile base version for 64-bit with clang
clang main.c parse_xml.c xml_content.c -o parse_xml_clang

# Compile base version for 32-bit with clang
clang -m32 main.c parse_xml.c xml_content.c -o parse_xml_32_clang

# Compile with no optimization for 64-bit with gcc
gcc -g main.c parse_xml.c xml_content.c -o parse_xml_0 -O0

# Compile with no optimization for 32-bit with gcc
gcc -m32 -g main.c parse_xml.c xml_content.c -o parse_xml_0_32 -O0

# Compile with no optimization for 64-bit with clang
clang -g main.c parse_xml.c xml_content.c -o parse_xml_0_clang -O0

# Compile with no optimization for 32-bit with clang
clang -m32 -g main.c parse_xml.c xml_content.c -o parse_xml_0_32_clang -O0

# Compile with optimization for size for 64-bit with gcc
gcc -g main.c parse_xml.c xml_content.c -o parse_xml_s -Os

# Compile with optimization for size for 32-bit with gcc
gcc -m32 -g main.c parse_xml.c xml_content.c -o parse_xml_s_32 -Os

# Compile with optimization for size for 64-bit with clang
clang -g main.c parse_xml.c xml_content.c -o parse_xml_s_clang -Os

# Compile with optimization for size for 32-bit with clang
clang -m32 -g main.c parse_xml.c xml_content.c -o parse_xml_s_32_clang -Os

# Compile with optimization for speed for 64-bit with gcc
gcc -g main.c parse_xml.c xml_content.c -o parse_xml_3 -O3

# Compile with optimization for speed for 32-bit with gcc
gcc -m32 -g main.c parse_xml.c xml_content.c -o parse_xml_3_32 -O3

# Compile with optimization for speed for 64-bit with clang
clang -g main.c parse_xml.c xml_content.c -o parse_xml_3_clang -O3

# Compile with optimization for speed for 32-bit with clang
clang -m32 -g main.c parse_xml.c xml_content.c -o parse_xml_3_32_clang -O3

# Compile with level 1 optimization for 64-bit with gcc
gcc -g main.c parse_xml.c xml_content.c -o parse_xml_1 -O1

# Compile with level 1 optimization for 32-bit with gcc
gcc -m32 -g main.c parse_xml.c xml_content.c -o parse_xml_1_32 -O1

# Compile with level 1 optimization for 64-bit with clang
clang -g main.c parse_xml.c xml_content.c -o parse_xml_1_clang -O1

# Compile with level 1 optimization for 32-bit with clang
clang -m32 -g main.c parse_xml.c xml_content.c -o parse_xml_1_32_clang -O1

# Compile with level 2 optimization for 64-bit with gcc
gcc -g main.c parse_xml.c xml_content.c -o parse_xml_2 -O2

# Compile with level 2 optimization for 32-bit with gcc
gcc -m32 -g main.c parse_xml.c xml_content.c -o parse_xml_2_32 -O2

# Compile with level 2 optimization for 64-bit with clang
clang -g main.c parse_xml.c xml_content.c -o parse_xml_2_clang -O2

# Compile with level 2 optimization for 32-bit with clang
clang -m32 -g main.c parse_xml.c xml_content.c -o parse_xml_2_32_clang -O2

# Compile with aggressive optimization for 64-bit with gcc
gcc -g main.c parse_xml.c xml_content.c -o parse_xml_fast -Ofast

# Compile with aggressive optimization for 32-bit with gcc
gcc -m32 -g main.c parse_xml.c xml_content.c -o parse_xml_fast_32 -Ofast

# Compile with aggressive optimization for 64-bit with clang
clang -g main.c parse_xml.c xml_content.c -o parse_xml_fast_clang -Ofast

# Compile with aggressive optimization for 32-bit with clang
clang -m32 -g main.c parse_xml.c xml_content.c -o parse_xml_fast_32_clang -Ofast
