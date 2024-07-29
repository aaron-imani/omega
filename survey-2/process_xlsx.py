import os
import sys

import matplotlib.pyplot as plt
import pandas as pd
import pingouin as pg
import seaborn as sns

os.makedirs("output", exist_ok=True)

survey_report = pd.read_excel(sys.argv[1], sheet_name="Raw Data", header=None)
# print(len(survey_report.columns.get_level_values(1)))
survey_report = survey_report.iloc[2:, :]

survey_report.iloc[:, 0:7] = survey_report.iloc[:, 0:7].replace({1: "OLD", 2: "NEW"})
survey_report.iloc[:, 7:] = survey_report.iloc[:, 7:].replace({1: "NEW", 2: "OLD"})

old_q = ["OLD"]
new_q = ["NEW"]
col_names = old_q * 7 + new_q * 8

survey_report.columns = col_names

survey_report = survey_report.reset_index(drop=True)

survey_report.to_csv("output/processed.csv", index=False)


# Function to calculate OLD/NEW percentage for a single row
def calculate_percentages(row):
    total = len(row)
    old_count = (row == "OLD").sum()
    new_count = (row == "NEW").sum()
    return pd.Series({"OLD": old_count / total * 100, "NEW": new_count / total * 100})


# Calculate the percentage for each participant
participant_percentages = survey_report.apply(calculate_percentages, axis=1)

print("OLD/NEW Percentage for Each Participant:")
print(participant_percentages)

# Calculate the percentage across all participants
total_responses = survey_report.size
old_total = (survey_report == "OLD").sum().sum()
new_total = (survey_report == "NEW").sum().sum()
overall_percentages = {
    "OLD": old_total / total_responses * 100,
    "NEW": new_total / total_responses * 100,
}

print("\nOLD/NEW Percentage Across All Participants:")
print(overall_percentages)
# plt.figure(dpi=100)

# Plot the data
# ax = data.plot(
#     kind="bar", stacked=False, rot=90, title="Survey Results", figsize=(4, 5)
# )


# # Define hatch patterns for each method
# hatch_patterns = {"AMG": "-", "OMG": "X", "Identical": None}

# # Apply consistent hatches to the bars
# for bars, method in zip(ax.containers, data.columns):
#     for bar in bars:
#         bar.set_hatch(hatch_patterns[method])
#         bar.set_linewidth(1.5)

# plt.legend(loc="center left", bbox_to_anchor=(1.05, 0.85))
# # plt.tight_layout()

# # Show the plot
# # plt.show()
# plt.savefig("output/stacked_bar.eps", bbox_inches="tight", format="eps")
# plt.savefig("output/stacked_bar.png", bbox_inches="tight", format="png")


# # Encode the categorical variables numerically for correlation analysis

# data = pd.read_csv("output/processed.csv")
# df = data[criteria]

# encoding = {"AMG": 1, "OMG": 2, "Identical": 0}
# encoded_df = df.map(lambda x: encoding.get(x, x))

# # Calculate the correlation matrix with p-values
# corr_results = pg.pairwise_corr(encoded_df, method="pearson")
# corr_results.to_csv("output/correlation.csv", index=False)

# # Filter out the significant correlations
# significant_corr = corr_results[corr_results["p-unc"] < 0.1]
# significant_corr.to_csv("output/significant_correlation.csv", index=False)


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
