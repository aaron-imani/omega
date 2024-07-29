import jsonlines
from collections import defaultdict
import random 
import pandas as pd

random.seed(456)

with jsonlines.open('program_contexts/tlcodesum.test','r') as f:
    data = list(f)
# print(len(data))
# print(data[0])

labels = set()
categories = defaultdict(list)
# df = pd.DataFrame(data)
# sample = df.groupby('label', group_keys=False).apply(lambda x: x.sample(frac=0.09))

# print(sample.groupby('label').size())
# print(sample.shape)

for item in data:
    labels.add(item['label'])
    categories[item['label']].append(item)

min_length = min([len(categories[category]) for category in categories])

random_sample = []

for category in categories:
    print(category, len(categories[category]))
    with jsonlines.open(f'program_contexts/methdsum-test-{category}.jsonl','w') as f:
        f.write_all(categories[category])

    random_sample.extend(random.sample(categories[category], min_length))

df = pd.DataFrame(random_sample)
df.to_csv('program_contexts/methdsum-test-sample.csv', index=False)
print(f'Collecting {min_length} samples from each category. Total samples: {len(random_sample)}')