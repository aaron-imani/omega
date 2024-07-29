import pandas as pd
import json

with open('1151-commits-labeled-with-maintenance-activities.csv','r') as f:
    data = f.readlines()

with open('project_name_mapping.json','r') as f:
    complete_project_names = json.load(f)

data = [d.split('#',4)[:4] for d in data]
df = pd.DataFrame(data[1:], columns=data[0])
df['project'] = df['project'].map(complete_project_names)
df['commitURL'] = df.apply(lambda x: f'https://github.com/{x["project"]}/commit/{x["commitId"]}', axis=1)
# Move the commitURL column to the front
cols = df.columns.tolist()
cols = cols[-1:] + cols[:-1]
df = df[cols]
df.to_csv('preprocessed_1151-commits-labeled-with-maintenance-activities.csv', index=False)