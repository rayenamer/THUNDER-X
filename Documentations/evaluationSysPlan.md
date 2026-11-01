# System Evaluation Plan

The plan has two systems.

## 1. CI: System Scoring

1. Run the system on the Mind2Web dataset.
2. Collect the results.
3. Compare the results to the real (ground-truth) answers.
4. Compute the KPIs (accuracy, precision, …).
5. Give the system an overall score.

## 2. Live Confidence Score

1. Run the system on Mind2Web and collect the results.
2. **Lab:** analyze the correlation between each candidate column and right/wrong.
3. Pick the columns to group by, using these criteria:
   - **Few columns** (and few values per column), so each group keeps enough examples (≥ 30)
   - **No noise:** no duplicate columns that say the same thing
   - **Strong correlation** with right/wrong
   - **Available live:** computable at runtime (no ground truth)
4. Compute the **% right** for each group (on the train split, then verify on the test split).
5. For every new prompt: find its group → **that group's % is its confidence score**.