import json
import os
import re
import time

from sentence_transformers import SentenceTransformer, util

os.environ["TOKENIZERS_PARALLELISM"] = "true"
model = SentenceTransformer(
    "flax-sentence-embeddings/st-codesearch-distilroberta-base", device="cpu"
)
train_file_address = os.path.join(
    os.path.dirname(__file__), "program_contexts/tlcodesum.train"
)


def read_data(file_address, category):
    ids = []
    codes = []
    comments = []
    labels = []
    with open(file_address, "r") as file:
        lines = file.readlines()
    for line in lines:
        sample = json.loads(line)
        label = sample.get("label")
        if label != category:
            continue
        ids.append(sample.get("id"))
        codes.append(sample.get("raw_code"))
        comments.append(sample.get("comment"))
        labels.append(label)

    return ids, codes, comments, labels


def get_data(category):
    training_codes, training_comments, training_labels = [], [], []
    cur_ids, cur_codes, cur_comments, cur_labels = read_data(
        train_file_address, category
    )
    training_codes += cur_codes
    training_comments += cur_comments
    training_labels += cur_labels
    return training_codes, training_comments, training_labels


def tokenize(code_str):
    code_str = str(code_str)
    code_str = re.sub(r"\/\/.*|\/\*[\s\S]*?\*\/", "", code_str)
    code_str = re.sub(r"[\.\,\;\:\(\)\{\}\[\]]", " ", code_str)
    code_str = re.sub(r"\s+", " ", code_str)
    tokens = re.findall(r"[a-z]+|[A-Z][a-z]*|[0-9]+|[^\w\s]+", code_str)
    for i in range(len(tokens)):
        if i > 0 and tokens[i - 1].islower() and tokens[i].isupper():
            tokens[i] = tokens[i].lower()
    for i in range(len(tokens)):
        tokens[i] = tokens[i].lower()
    java_keywords = [
        "abstract",
        "assert",
        "boolean",
        "break",
        "byte",
        "case",
        "catch",
        "char",
        "class",
        "const",
        "continue",
        "default",
        "do",
        "double",
        "else",
        "extends",
        "false",
        "final",
        "finally",
        "float",
        "for",
        "goto",
        "if",
        "implements",
        "import",
        "instanceof",
        "int",
        "interface",
        "long",
        "native",
        "new",
        "null",
        "package",
        "private",
        "protected",
        "public",
        "return",
        "short",
        "static",
        "strictfp",
        "super",
        "switch",
        "synchronized",
        "this",
        "throw",
        "throws",
        "transient",
        "true",
        "try",
        "void",
        "volatile",
        "while",
    ]
    idxs_del = []
    for i in range(len(tokens)):
        if tokens[i] in java_keywords:
            idxs_del.append(i)

    tokens_temp = []
    for idx, token in enumerate(tokens):
        if idx in idxs_del:
            continue
        else:
            tokens_temp.append(token)
    tokens = tokens_temp
    return tokens


def count_common_elements(list1, list2):
    set1 = set(list1)
    set2 = set(list2)
    intersection_set = set1.intersection(set2)
    union_set = set1.union(set2)
    jaccard = len(intersection_set) / len(union_set)
    return jaccard


def pre_process_samples_token(test_codes, training_codes):
    test_codes_embeddings, training_codes_embeddings = [], []
    st = time.time()
    for i in range(len(test_codes)):
        test_code = test_codes[i]
        code1_emb = tokenize(test_code)
        test_codes_embeddings.append(code1_emb)
    ed = time.time()
    print("Test code embedding generate finish!")
    # print(str(ed - st))
    for i in range(len(training_codes)):
        train_code = training_codes[i]
        code1_emb = tokenize(train_code)
        training_codes_embeddings.append(code1_emb)
    print("Training code embedding generate finish!")
    with open("sim_token.txt", "w") as fp:
        for i in range(len(test_codes)):
            test_code_embedding = test_codes_embeddings[i]
            sim_scores = []
            for j in range(len(training_codes)):
                train_code_embedding = training_codes_embeddings[j]
                score = count_common_elements(test_code_embedding, train_code_embedding)
                sim_scores.append(score)
            sorted_indexes = [
                i
                for i, v in sorted(
                    enumerate(sim_scores), key=lambda x: x[1], reverse=True
                )
            ]
            for val in sorted_indexes[:10]:
                fp.write(str(val) + " ")
            fp.write("\n")


def pre_process_samples_semantic(query_code, training_codes, training_codes_embeddings):
    # training_codes_embeddings = []
    query_code_emb = model.encode(query_code, convert_to_tensor=True)
    # print('Query code embedding generate finish!')
    # for i in range(len(training_codes)):
    #     train_code = training_codes[i]
    #     code1_emb = model.encode(train_code, convert_to_tensor=True)
    #     training_codes_embeddings.append(code1_emb)
    # print('Training code embedding generate finish!')
    sim_scores = []
    for j in range(len(training_codes)):
        train_code_embedding = training_codes_embeddings[j]
        hits = util.semantic_search(query_code_emb, train_code_embedding)[0]
        top_hit = hits[0]
        score = top_hit["score"]
        sim_scores.append(score)
    sorted_indexes = [
        i for i, v in sorted(enumerate(sim_scores), key=lambda x: x[1], reverse=True)
    ]
    return sorted_indexes[:10]


# if __name__ == '__main__':
#
#     training_codes, training_comments, training_labels, test_codes, test_comments, test_labels = get_data()
#     pre_process_samples_token(test_codes, training_codes)
# pre_process_samples_semantic(test_codes, training_codes)
