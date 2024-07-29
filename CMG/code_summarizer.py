# from sentence_transformers import SentenceTransformer
import os

import torch
from openai import BadRequestError

import common.model_loader as model_loader
from CMG.find_examples_tlc_training_SUM import get_data, pre_process_samples_semantic
from common.log_config import get_logger

logger = get_logger("MethodSummarizer")
model = model_loader.model
instruction_allowed = model_loader.is_instruction_tuned
# from langchain_community.callbacks import get_openai_callback

# system messages
zero_what = "You are an expert Java programmer, please describe the functionality of the method in the comment."
zero_property = "You are an expert Java programmer, please describe the asserts properties of the method including pre-conditions or post-conditions of the method in the comment."
zero_why = "You are an expert Java programmer, please explain the reason why the method is provided or the design rational of the method in the comment."
zero_use = "You are an expert Java programmer, please describe the usage or the expected set-up of using the method in the comment."
zero_done = "You are an expert Java programmer, please describe the implementation details of the method in the comment."

# zero_what = "You are an expert Java programmer. I will give you a method and I want you to write a brief comment for it. In your comment, please describe only the functionality of the method. When generating a comment, please learn from your previous comments."
# zero_property = "You are an expert Java programmer. I will give you a method and I want you to write a brief comment for it. In your comment, please describe only the asserts properties of the method including pre-conditions or post-conditions of the method. When generating a comment, please learn from your previous comments."
# zero_why = "You are an expert Java programmer. I will give you a method and I want you to write a brief comment for it. In your comment, please explain only the reason why the method is provided or the design rational of the method. When generating a comment, please learn from your previous comments."
# zero_use = "You are an expert Java programmer. I will give you a method and I want you to write a brief comment for it. In your comment, please describe only the usage or the expected set-up of using the method. When generating a comment, please learn from your previous comments."
# zero_done = "You are an expert Java programmer. I will give you a method and I want you to write a brief comment for it. In your comment, please describe only the implementation details of the method. When generating a comment, please learn from your previous comments."


# Original
# prompt_lists = {
#     "what": zero_what,
#     "why": zero_why,
#     "use": zero_use,
#     "done": zero_done,
#     "property": zero_property,
# }
# training_codes, training_comments, training_labels = get_data()

prompt_lists = {
    "what": zero_what,
    "why": zero_why,
    "usage": zero_use,
    "done": zero_done,
    "property": zero_property,
}

data = {
    "what": get_data("what"),
    "why": get_data("why"),
    "usage": get_data("usage"),
    "done": get_data("done"),
    "property": get_data("property"),
}

training_codes_embeddings_path = os.path.join(
    os.path.dirname(__file__), "training_data_semantic_embedding.pt"
)
training_codes_embeddings = torch.load(training_codes_embeddings_path)


# def openai_completion(**kwargs):
#     return client.chat.completions.create(**kwargs)


# def ollama_completetion(messages, **kwargs):
#     return model.invoke(messages, **kwargs)


def _prepare_messages(query_method, comment_category):
    training_codes, training_comments, training_labels = data[comment_category]
    if training_codes and training_comments and training_labels:
        demonstration_example_idxs = pre_process_samples_semantic(
            query_method, training_codes, training_codes_embeddings
        )

        system_msg = prompt_lists.get(comment_category, zero_what)

        if instruction_allowed:
            messages = [{"role": "system", "content": system_msg}]
        else:
            messages = [
                {"role": "user", "content": system_msg},
                {"role": "assistant", "content": "Sure, please provide the method."},
            ]

        for i in range(10):
            example_index = int(demonstration_example_idxs[i])
            user_msg = (
                "Here is the code:\n```\n"
                + training_codes[example_index]
                + "\n``` Your comment:"
            )
            assistant_msg = training_comments[example_index]
            messages.append({"role": "user", "content": user_msg})
            messages.append({"role": "assistant", "content": assistant_msg})

        query = "Here is the code:\n```\n" + query_method + "\n``` Your comment:"
        messages.append({"role": "user", "content": query})
        return messages
    else:
        return None


def summarize_method_body(query_method, comment_category):
    messages = _prepare_messages(query_method, comment_category)
    if messages:
        cur_ans = "Method body's summary can not be generated."
        try:
            response = model.invoke(messages, max_tokens=30)
            cur_ans = response.content
        except BadRequestError as e:
            error_msg = e.body["message"]
            logger.error(error_msg)
            if error_msg.startswith("This model's maximum context length is"):
                cur_ans = "Method is too long to summarize"

        return cur_ans
    else:
        return "Method body's summary can not be generated."


if __name__ == "__main__":
    query_code = """
class Solution {
    public int[] twoSum(int[] nums, int target) {
        Map<Integer, Integer> numMap = new HashMap<>();
        int n = nums.length;

        for (int i = 0; i < n; i++) {
            int complement = target - nums[i];
            if (numMap.containsKey(complement)) {
                return new int[]{numMap.get(complement), i};
            }
            numMap.put(nums[i], i);
        }

        return new int[]{{}};
    }
}
"""
    for k in prompt_lists:
        print(f"{k}:", summarize_method_body(query_code, k))
