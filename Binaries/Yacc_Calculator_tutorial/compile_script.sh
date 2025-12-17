#!/bin/bash

# Compile base version for 64-bit with gcc
gcc -o calc y.tab.c lex.yy.c -lfl -L/usr/lib64 -lfl


# Compile base version for 64-bit with clang
clang -o calc_clang y.tab.c lex.yy.c -lfl -L/usr/lib64 -lfl


# Compile with no optimization for 64-bit with gcc
gcc -g -o calc_0 y.tab.c lex.yy.c -lfl -L/usr/lib64 -lfl -O0


# Compile with no optimization for 64-bit with clang
clang -g -o calc_0_clang y.tab.c lex.yy.c -lfl -L/usr/lib64 -lfl -O0


# Compile with optimization for size for 64-bit with gcc
gcc -g -o calc_s y.tab.c lex.yy.c -lfl -L/usr/lib64 -lfl -Os


# Compile with optimization for size for 64-bit with clang
clang -g -o calc_s_clang y.tab.c lex.yy.c -lfl -L/usr/lib64 -lfl -Os


# Compile with optimization for speed for 64-bit with gcc
gcc -g -o calc_3 y.tab.c lex.yy.c -lfl -L/usr/lib64 -lfl -O3

# Compile with level 1 optimization for 64-bit with clang
clang -g -o calc_1_clang y.tab.c lex.yy.c -lfl -L/usr/lib64 -lfl -O1


# Compile with level 2 optimization for 64-bit with gcc
gcc -g -o calc_2 y.tab.c lex.yy.c -lfl -L/usr/lib64 -lfl -O2


# Compile with aggressive optimization for 64-bit with gcc
gcc -g -o calc_fast y.tab.c lex.yy.c -lfl -L/usr/lib64 -lfl -Ofast
