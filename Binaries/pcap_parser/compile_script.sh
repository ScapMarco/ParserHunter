#!/usr/bin/env bash

# gcc, 64-bit
gcc -g -O0    ./pcap.c ./test.c -I. -o pcap_parser_O0
gcc -g -O1    ./pcap.c ./test.c -I. -o pcap_parser_O1
gcc -g -O2    ./pcap.c ./test.c -I. -o pcap_parser_O2
gcc -g -O3    ./pcap.c ./test.c -I. -o pcap_parser_O3
gcc -g -Os    ./pcap.c ./test.c -I. -o pcap_parser_Os
gcc -g -Ofast ./pcap.c ./test.c -I. -o pcap_parser_Ofast

# gcc, 32-bit
gcc -g -O0 -m32    ./pcap.c ./test.c -I. -o pcap_parser_O0_32
gcc -g -O1 -m32    ./pcap.c ./test.c -I. -o pcap_parser_O1_32
gcc -g -O2 -m32    ./pcap.c ./test.c -I. -o pcap_parser_O2_32
gcc -g -O3 -m32    ./pcap.c ./test.c -I. -o pcap_parser_O3_32
gcc -g -Os -m32    ./pcap.c ./test.c -I. -o pcap_parser_Os_32
gcc -g -Ofast -m32 ./pcap.c ./test.c -I. -o pcap_parser_Ofast_32

# clang, 64-bit
clang -g -O0    ./pcap.c ./test.c -I. -o pcap_parser_O0_clang
clang -g -O1    ./pcap.c ./test.c -I. -o pcap_parser_O1_clang
clang -g -O2    ./pcap.c ./test.c -I. -o pcap_parser_O2_clang
clang -g -O3    ./pcap.c ./test.c -I. -o pcap_parser_O3_clang
clang -g -Os    ./pcap.c ./test.c -I. -o pcap_parser_Os_clang
clang -g -Ofast ./pcap.c ./test.c -I. -o pcap_parser_Ofast_clang

# clang, 32-bit
clang -g -O0 -m32    ./pcap.c ./test.c -I. -o pcap_parser_O0_32_clang
clang -g -O1 -m32    ./pcap.c ./test.c -I. -o pcap_parser_O1_32_clang
clang -g -O2 -m32    ./pcap.c ./test.c -I. -o pcap_parser_O2_32_clang
clang -g -O3 -m32    ./pcap.c ./test.c -I. -o pcap_parser_O3_32_clang
clang -g -Os -m32    ./pcap.c ./test.c -I. -o pcap_parser_Os_32_clang
clang -g -Ofast -m32 ./pcap.c ./test.c -I. -o pcap_parser_Ofast_32_clang

# --- Base (no -O) builds ---

# gcc, 64-bit
gcc      ./pcap.c ./test.c -I. -o pcap_parser

# gcc, 32-bit
gcc -m32 ./pcap.c ./test.c -I. -o pcap_parser_32

# clang, 64-bit
clang    ./pcap.c ./test.c -I. -o pcap_parser_clang

# clang, 32-bit
clang -m32 ./pcap.c ./test.c -I. -o pcap_parser_32_clang
