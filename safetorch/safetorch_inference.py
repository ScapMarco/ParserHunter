#!/usr/bin/env python3
import sys
import torch
from utils.function_normalizer import FunctionNormalizer
from utils.instructions_converter import InstructionsConverter
from safetorch.safe_network import SAFE
from safetorch.parameters import Config

# use conda env safe37

def init_safe_model(model_path: str, vocab_path: str, max_instruction: int, device: torch.device):
    cfg = Config()
    net = SAFE(cfg).to(device)
    sd = torch.load(model_path, map_location=device)
    net.load_state_dict(sd)
    net.eval()
    conv = InstructionsConverter(vocab_path)
    norm = FunctionNormalizer(max_instruction=max_instruction)
    return net, conv, norm

def embed_instructions(instrs: list, net: SAFE, conv: InstructionsConverter, norm: FunctionNormalizer, device: torch.device):
    ids = conv.convert_to_ids(instrs)
    padded, lengths = norm.normalize_functions([ids])
    seq = padded[0]
    length0 = int(lengths[0])
    tensor = torch.LongTensor(seq).to(device)
    with torch.no_grad():
        emb = net(tensor, [length0])
    return emb.squeeze(0).cpu()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python embed_asm.py '<instr1>; <instr2>; <instr3>; ...'")
        sys.exit(1)

    # Parse instructions from command line
    asm_input = sys.argv[1]
    instructions = [x.strip() for x in asm_input.split(';') if x.strip()]

    device = "cpu"
    # Initialize SAFE model
    net, conv, norm = init_safe_model(
        model_path="./safetorch/model/SAFEtorch.pt",
        vocab_path="./safetorch/model/word2id.json",
        max_instruction=150,
        device=device
    )

    embedding = embed_instructions(instructions, net, conv, norm, device)
    print(f"Embedding vector (shape= {len(embedding)}):")
    print(embedding.tolist())
