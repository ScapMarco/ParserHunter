#!/usr/bin/env bash

# gcc, 64-bit
gcc -g -O0    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_O0
gcc -g -O1    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_O1
gcc -g -O2    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_O2
gcc -g -O3    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_O3
gcc -g -Os    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_Os
gcc -g -Ofast ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_Ofast

# gcc, 32-bit
gcc -g -O0 -m32    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_O0_32
gcc -g -O1 -m32    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_O1_32
gcc -g -O2 -m32    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_O2_32
gcc -g -O3 -m32    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_O3_32
gcc -g -Os -m32    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_Os_32
gcc -g -Ofast -m32 ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_Ofast_32

# clang, 64-bit
clang -g -O0    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_O0_clang
clang -g -O1    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_O1_clang
clang -g -O2    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_O2_clang
clang -g -O3    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_O3_clang
clang -g -Os    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_Os_clang
clang -g -Ofast ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_Ofast_clang

# clang, 32-bit
clang -g -O0 -m32    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_O0_32_clang
clang -g -O1 -m32    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_O1_32_clang
clang -g -O2 -m32    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_O2_32_clang
clang -g -O3 -m32    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_O3_32_clang
clang -g -Os -m32    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_Os_32_clang
clang -g -Ofast -m32 ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_Ofast_32_clang

# --- Base (no -O) builds ---

# gcc, 64-bit
gcc      ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser

# gcc, 32-bit
gcc -m32 ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_32

# clang, 64-bit
clang    ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_clang

# clang, 32-bit
clang -m32 ./elf-parser.c ./elf-parser-main.c ./disasm.c -I. -o elf-parser_32_clang