#!/usr/bin/env bash
#   The lab's Python environment (labs/.venv), separate from Thunder-X's.
#
#   ./labs/lab.sh          create it (first time) or update it, and register the Jupyter kernel "lab"
#   ./labs/lab.sh open     same, then open the lab in Jupyter Lab (browser), already in this environment
#   ./labs/lab.sh miniwob  same, but opens the MiniWoB++ lab (confidence_lab_withMiniWoB++.ipynb)
#   ./labs/lab.sh kpi      same, but opens the KPI lab (kpi_lab.ipynb): start Thunder-X first (./run.sh)
#   source labs/lab.sh     same as the first, and also activate it in this terminal
#
#   In VS Code: Select Kernel → Python Environments → labs/.venv  (or Jupyter Kernel → lab)

LAB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_ENV="$LAB_DIR/.venv"
LAB_PYTHON="$LAB_ENV/bin/python"

PACKAGES=(
  ipykernel      # to run the notebooks in this environment
  jupyterlab     # ./labs/lab.sh open
  pandas         # tables
  pyarrow        # parquet files
  numpy
  matplotlib     # charts
  scikit-learn   # correlations, train/test split, calibration
  miniwob        # MiniWoB++ tasks as gymnasium environments (needs Chrome installed)
  pydantic       # Thunder-X's nl_parser, used to filter the tasks
  "browser-use>=0.13,<0.14"   # benchmark builder: opens pages, acts on elements (same version as Thunder-X)
  httpx          # KPI lab: sends the benchmark rows to Thunder-X's service
)

lab_setup() {
  command -v python3 >/dev/null || { echo "✘ python3 not found"; return 1; }

  if [[ ! -x "$LAB_PYTHON" ]]; then
    echo "⚡ creating the lab environment in $LAB_ENV"
    python3 -m venv "$LAB_ENV" || return 1
  fi

  echo "⚡ installing the lab's packages"
  "$LAB_PYTHON" -m pip install --quiet --upgrade pip "${PACKAGES[@]}" || return 1

  echo "⚡ registering the Jupyter kernel \"lab\""
  "$LAB_PYTHON" -m ipykernel install --user --name lab --display-name "lab" >/dev/null || return 1

  echo "✔ lab ready"
}

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  # sourced: set up, then activate in the current terminal (no `exit`: it would close the terminal)
  lab_setup && source "$LAB_ENV/bin/activate" && echo "✔ activated (deactivate: \`deactivate\`)"
elif [[ "${1:-}" == "open" ]]; then
  lab_setup || exit 1
  cd "$LAB_DIR" && exec "$LAB_ENV/bin/jupyter" lab confidence_lab.ipynb
elif [[ "${1:-}" == "miniwob" ]]; then
  lab_setup || exit 1
  cd "$LAB_DIR" && exec "$LAB_ENV/bin/jupyter" lab "confidence_lab_withMiniWoB++.ipynb"
elif [[ "${1:-}" == "kpi" ]]; then
  lab_setup || exit 1
  cd "$LAB_DIR" && exec "$LAB_ENV/bin/jupyter" lab kpi_lab.ipynb
elif [[ -n "${1:-}" ]]; then
  echo "✘ unknown command \"$1\": use  open,  miniwob  or  kpi  (or nothing, to only set up)"
  exit 1
else
  lab_setup || exit 1
  echo "  open it: ./labs/lab.sh open   ·   MiniWoB++ lab: ./labs/lab.sh miniwob   ·   KPI lab: ./labs/lab.sh kpi"
  echo "  (or in VS Code: Select Kernel → Python Environments → labs/.venv)"
fi
