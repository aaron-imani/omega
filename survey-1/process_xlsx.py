import os
import sys

import matplotlib.pyplot as plt
import pandas as pd
import pingouin as pg
import seaborn as sns

os.makedirs("output", exist_ok=True)

survey_report = pd.read_excel(sys.argv[1], sheet_name="Raw Data", header=None)
# print(len(survey_report.columns.get_level_values(1)))
survey_report = survey_report.iloc[:, 18:-2]

cur_col = "OMG"
for i in range(0, len(survey_report.columns), 5):
    if cur_col == "OMG":
        next_col = "AMG"
    else:
        next_col = "OMG"

    # Map values
    for j in range(5):
        survey_report.iloc[2:, i + j].replace(
            {"1": "Identical", "2": cur_col, "3": next_col}, inplace=True
        )
    cur_col = next_col

col_names = ["OMG"] * 5
cur_col = "AMG"
for i in range(1, 15):
    col_names.extend([cur_col] * 5)
    if cur_col == "AMG":
        cur_col = "OMG"
    else:
        cur_col = "AMG"

survey_report.iloc[0, :] = col_names

# set two first rows as header
# new_columns = pd.MultiIndex.from_arrays([survey_report.iloc[1], survey_report.iloc[1]])
# survey_report.columns = new_columns
# survey_report = survey_report.drop([0, 1]).reset_index(drop=True)

# Set the second row as header
survey_report.columns = survey_report.iloc[1]
survey_report = survey_report.drop([0, 1]).reset_index(drop=True)

survey_report.to_csv("output/processed.csv", index=False)

criteria = [
    "Rationality",
    "Expressiveness",
    "Conciseness",
    "Comprehensiveness",
    "Overall I prefer ...",
]


# Function to count occurrences of each method for a given criterion
def count_methods(column):
    counts = {"AMG": 0, "OMG": 0, "Identical": 0}
    for value in column:
        counts[value] += 1
    total = sum(counts.values())
    return {method: count / total for method, count in counts.items()}


# Apply the function to each criterion
ratios = survey_report[criteria].apply(count_methods).apply(pd.Series)

data = []
for criterion in criteria:
    data.append(ratios.loc[criterion].mean().round(2))

data = pd.DataFrame(data, index=criteria)
data = data.rename(index={"Overall I prefer ...": "Overall Preference"})
data["Winner"] = data.idxmax(axis=1)
data.index.name = "Criterion"
cols = ["AMG", "Identical", "OMG", "Winner"]
data = data[cols]
data.to_csv("output/summary.csv")

# plt.figure(dpi=100)

# Plot the data
ax = data.plot(
    kind="bar", stacked=False, rot=90, title="Survey Results", figsize=(4, 5)
)


# Define hatch patterns for each method
hatch_patterns = {"AMG": "-", "OMG": "X", "Identical": None}

# Apply consistent hatches to the bars
for bars, method in zip(ax.containers, data.columns):
    for bar in bars:
        bar.set_hatch(hatch_patterns[method])
        bar.set_linewidth(1.5)

plt.legend(loc="center left", bbox_to_anchor=(1.05, 0.85))
# plt.tight_layout()

# Show the plot
# plt.show()
plt.savefig("output/stacked_bar.eps", bbox_inches="tight", format="eps")
plt.savefig("output/stacked_bar.png", bbox_inches="tight", format="png")


# Encode the categorical variables numerically for correlation analysis

data = pd.read_csv("output/processed.csv")
df = data[criteria]

encoding = {"AMG": 1, "OMG": 2, "Identical": 0}
encoded_df = df.map(lambda x: encoding.get(x, x))

# Calculate the correlation matrix with p-values
corr_results = pg.pairwise_corr(encoded_df, method="pearson")
corr_results.to_csv("output/correlation.csv", index=False)

# Filter out the significant correlations
significant_corr = corr_results[corr_results["p-unc"] < 0.1]
significant_corr.to_csv("output/significant_correlation.csv", index=False)


# corr_matrix = corr_results.pivot(index="X", columns="Y", values="r")
# p_matrix = corr_results.pivot(index="X", columns="Y", values="p-unc")
# Plot the correlation matrix with annotations for significance
# plt.figure(figsize=(10, 8))
# sns.heatmap(
#     corr_matrix,
#     annot=True,
#     cmap="coolwarm",
#     fmt=".2f",
#     mask=p_matrix >= 0.05,
#     cbar_kws={"label": "Correlation Coefficient"},
# )
# plt.title("Correlation Matrix of Criteria (Significant Values)")
