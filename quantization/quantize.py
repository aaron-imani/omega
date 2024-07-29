import os

os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer

os.environ["TOKENIZERS_PARALLELISM"] = "true"

# Uncomment the model path you want to quantize
# model_path = 'm-a-p/OpenCodeInterpreter-DS-33B'
# model_path = 'codefuse-ai/CodeFuse-DeepSeek-33B'

quant_path = model_path.split("/")[-1] + "-AWQ"
quant_config = {"zero_point": True, "q_group_size": 128, "w_bit": 4, "version": "GEMM"}

# Load model
model = AutoAWQForCausalLM.from_pretrained(
    model_path, safetensors=False, **{"low_cpu_mem_usage": True}, force_download=True
)
tokenizer = AutoTokenizer.from_pretrained(
    model_path, trust_remote_code=True, force_download=True
)

# Quantize
model.quantize(tokenizer, quant_config=quant_config)

# Save quantized model
model.save_quantized(quant_path)
tokenizer.save_pretrained(quant_path)
