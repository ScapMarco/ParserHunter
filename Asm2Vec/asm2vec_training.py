import re
from gensim.models.asm2vec import Asm2Vec, Function, Instruction


# Use conda env asm2vec (python 3.8.19)


### ASM2VEC TRAINING ###############################################################################################################

def read_list(file_path):
    print(f"Reading list from file: {file_path} -----------------------------------------------")
    # Initialize an empty list to store the assembly code instructions
    assembly_codes = []

    # Open the file in read mode and read all lines into the list
    with open(file_path, "r") as file:
        current_basic_block = ""  # Initialize a string to store the instructions of the current basic block
        for line in file:
            line = line.strip()  # Remove leading and trailing whitespace
            if line:  # If the line is not empty
                try:
                    if len(line.split()) == 1:  # If the line contains a single instruction
                        line += " "  # Add a space after the instruction
                    current_basic_block += line + "\n"  # Add the line to the current basic block with a newline character
                except Exception as e:
                    print(f"Error processing line: {e}")
                    continue  # Continue to the next iteration if there's an error
            else:  # If an empty line is encountered, it signifies the end of the current basic block
                if current_basic_block:  # Only append if the current basic block is not empty
                    assembly_codes.append(current_basic_block.rstrip("\n"))  # Append the current basic block to the list of assembly codes
                current_basic_block = ""  # Reset the string for the next basic block

    # If there's any remaining basic block after reading all lines, append its instructions to the assembly codes list
    if current_basic_block:
        assembly_codes.append(current_basic_block.rstrip("\n"))
    
    print(f"End Reading list! Read {len(assembly_codes)} basic blocks -----------------------------------------------")
    return assembly_codes

def clean_instruction(instruction: str) -> str:
    # Define the regex pattern to remove unwanted symbols, excluding parentheses
    pattern = r'[\[\]{}<>!@#$%^&*_=|/~`",;:?]'
    # Remove the unwanted symbols
    cleaned_instruction = re.sub(pattern, '', instruction)
    return cleaned_instruction

def replace_hex_and_int(instruction: str) -> str:
    """
    Replace hex addresses and integer values with generic placeholders.
    """
    # Replace hex values, including optional preceding symbols
    instruction = re.sub(r'(?<!\w)[+-]?0x[a-fA-F0-9]+(?!\w)', 'ADDR', instruction)
    # Replace integer values, including optional preceding symbols
    instruction = re.sub(r'(?<!\w)[+-]?\b\d+\b(?!\w)', 'INT', instruction)
    return instruction

def clean_and_transform_assembly(list_assembly_codes: list) -> list:
    list_cleaned_assembly_codes = []
    for assembly_codes in list_assembly_codes:
        # Split the block into individual instructions
        instructions = re.findall(r'[^;\n]+', assembly_codes)  # Split by lines or semicolons
        # Clean and transform each instruction
        cleaned_instructions = []
        for instr in instructions:
            cleaned_instr = clean_instruction(instr.strip())
            transformed_instr = replace_hex_and_int(cleaned_instr)
            cleaned_instructions.append(transformed_instr)
        
        # Join the cleaned instructions back into a block, preserving newlines
        cleaned_block = '\n'.join(cleaned_instructions)
        list_cleaned_assembly_codes.append(cleaned_block)
    
    return list_cleaned_assembly_codes

def clean_operand(operand):
    # Remove square brackets, split by colons, spaces, commas, plus, minus, asterisk, bitwise AND, OR, XOR, left shift, right shift, and bitwise NOT signs
    cleaned_parts = re.split(r'[,\[\]:\s&|<>^~*]', operand.replace('[', '').replace(']', '').replace(':', ' '))
    # Split by +, -, *, &, |, ^, <<, >>, and ~ and retain the operands
    final_parts = []
    for part in cleaned_parts:
        if '+' in part or '-' in part or '*' in part or '&' in part or '|' in part or '^' in part or '<<' in part or '>>' in part or '~' in part:
            final_parts.extend(re.split(r'(\+|-|\*|&|\||\^|<<|>>|~)', part))
        else:
            final_parts.append(part)
    # Filter out empty parts, spaces, and symbols
    return [part.strip() for part in final_parts if part.strip() and not re.match(r'[+\-*&|<>^~]', part)]


def get_instructions_list(assembly_codes):
    '''
    Extract the string of instructions (representing the basic block assembly) and return a list of sublist of 'Instruction',
    where each list represents a basic block, and each sublist represents instructions.
    Parameters:
        assembly_codes (list): A list of assembly code strings 
            [bb1_assembly_string, bb2_assembly_string, bb3_assembly_string, ...].
    Returns:
        all_instructions (list): A list of sublist of 'Instruction' objects 
            [bb1_list_Instructions, bb2_list_Instructions, bb3_list_Instructions] 
                = [[Instruction1, Instruction2, ... ], [Instruction1, Instruction2], [Instruction1, Instruction2],  ...] .
    '''
    print(f"Getting the list of instructions from assembly codes -------------------------------------------------")
    tot_instructions = 0
    all_instructions = []

    for assembly_line in assembly_codes:
        if assembly_line: # Skip empty lines
            # Replace escaped newline sequences with actual newline characters
            assembly_line = assembly_line.replace('\\n', '\n')
            instructions = assembly_line.strip().split('\n')
            all_instructions_for_line = []
            for instruction in instructions:
                if instruction:  # Skip empty lines
                    try:
                        parts = instruction.split()
                        operator = parts[0] # Get the operator
                        operands = parts[1:]  # Get the operands
                    except IndexError:
                        print(f"Error: Unable to split instruction: {instruction}")
                        continue
                    all_instructions_for_line.append(Instruction(operator=operator, operands=operands))

            all_instructions.append(all_instructions_for_line)
            tot_instructions += len(all_instructions_for_line)

    print(f"        Total instructions read {tot_instructions} in {len(all_instructions)} basic blocks")
    # Total instructions read 2816365 in 693100 basic blocks
    print(f"End getting the list of instructions from assembly codes -------------------------------------------------")
    return all_instructions


def train_asm2vec_model(functions):
    '''
    Train the Asm2Vec model using the list of assembly code, where each one is a string of assembly code representing a basic block,
    and save the trained model.
    Parameters:
        assembly_codes (list): A list of assembly code strings [bb1, bb2, bb3, bb4, ...].
    '''
    print(f"TRAINING ASM2VEC MODEL ------------------------------------------------------------------")

    # Create an instance of the Asm2Vec model
    embedding_dim = 10      # Dimensionality of the word embeddings
    window_size = 10        # Context window size for Word2Vec
    min_count = 1           # Minimum frequency count of words (default: 5)
    seed = 42               # Random seed for reproducibility

    model = Asm2Vec(vector_size=embedding_dim, window=window_size, min_count=min_count, seed=seed) # to check compute_loss=True
    print(f"    Definining model: embedding_dim={embedding_dim}, window_size={window_size}, min_count={min_count}")

    # Build the vocabulary from the assembly code
    model.build_vocab(documents=functions, progress_per=1)
    epochs = 200 # Number of epochs to train the model
    print(f"    Training the model for {epochs} epochs ------------------------------------------------------")
    # Train the model
    model.train(documents=functions, total_examples=model.corpus_count, epochs=epochs)
    print(f"        model.total_train_time: {model.total_train_time} seconds")              # Total training time 5780.273784412537 seconds 
    print(f"        model.docvecs.vector_size: {model.docvecs.vector_size}")                # 20 Dimensionality of the document vectors
    print(f"        len(model.docvecs.vectors_docs)): {len(model.docvecs.vectors_docs)}")   # 693100 Number of documents
    print(f"        len(model.wv.vectors): {len(model.wv.vectors)}")                        # 454 Number of words

    print()
    print(f"Saving model: {model}")
    # Save the trained model
    model.save("./Asm2Vec/asm2vec_model")

#####################################################################################################################



def main():
    # Read the list of assembly codes from a text file
    list_assembly_codes = read_list(file_path="./Asm2Vec/assembly_codes.txt") # list of basic blocks
    print(f"len(list_assembly_codes): {len(list_assembly_codes)}") #  693100
    print(f"list_assembly_codes[0]: {list_assembly_codes[0]}") # [bb1, bb2, bb3, bb4, ...]  =  [..., INT\npop ebx\nret \n', 'call eax\n']
    print()

    list_cleaned_assembly_codes = clean_and_transform_assembly(list_assembly_codes) # list of cleaned basic blocks 
    print(f"len(list_cleaned_assembly_codes): {len(list_cleaned_assembly_codes)}") #  693100
    print(f"list_cleaned_assembly_codes[0]: {list_cleaned_assembly_codes[0]}")
    print()

    # get the list of instructions for all basic blocks 
    # Total instructions read 782682 in 160470 basic blocks
    list_instructions = get_instructions_list(list_cleaned_assembly_codes) # [ [instructions for bb1], [instructions for bb2], ...]
    # Total instructions read 2816365 in 693100 basic blocks
    print(f"len(list_instructions): {len(list_instructions)}") # 693100
    print(f"list_instructions[0]: {list_instructions[0]}")
    print()

    # Create a list of Function objects for all assembly codes
    functions = [Function(words=instructions, tags=[f'basic_block_{i}']) for i, instructions in enumerate(list_instructions)]
    print(f"len(functions): {len(functions)}")
    print(f"functions[0]: {functions[0]}")

    # Train the model and save it
    train_asm2vec_model(functions) #  454 Number of words

    # Load the saved model
    model = Asm2Vec.load("./Asm2Vec/asm2vec_model")
    print(f"model: {model}")
    print()

    print(f"len(model.wv.vectors): {len(model.wv.vectors)}") # 454 Number of words (unique instructions)
    for key in model.wv.vocab.keys():
        print(f"key: {key}")


if __name__ == "__main__":
    main()