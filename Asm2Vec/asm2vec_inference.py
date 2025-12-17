import re
import json
from gensim.models.asm2vec import Asm2Vec, Function, Instruction

# use conda env asm2vec

def make_predictions(model, cleaned_function):
    # compute the embedding for the function
    embedding = model.infer_vector(cleaned_function)
    return embedding.tolist()

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

def clean_and_transform_assembly(assembly_codes: str) -> str:
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
    return cleaned_block


def get_instructions_list(assembly_codes):
    #print(f"Raw assembly codes: {repr(assembly_codes)}")
    
    # Replace escaped newline sequences with actual newline characters
    assembly_codes = assembly_codes.replace('\\n', '\n')

    instructions = assembly_codes.strip().split('\n')
    #print(f"Instructions after split: {repr(instructions)}")

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

    return all_instructions_for_line



def main(assembly_codes):
    model = Asm2Vec.load("./Asm2Vec/asm2vec_model") 
    # Clean and trasform the assembly codes
    cleaned_assembly_codes = clean_and_transform_assembly(assembly_codes)
    # Get the list of Instruction objects
    list_instructions = get_instructions_list(cleaned_assembly_codes)
    # Create a Function object
    function = Function(words=list_instructions, tags=[f'basic_block_len_{len(list_instructions)}'])
    # Make predictions
    embedding = make_predictions(model, function)
    # Print the embedding as JSON string
    print(json.dumps(embedding))


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: model_inference <assembly_codes>")
        sys.exit(1)
    assembly_codes = sys.argv[1]
    main(assembly_codes)