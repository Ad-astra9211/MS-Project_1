#!/bin/bash
set -e

# Install RAPIDS libraries
pip install \
    --extra-index-url=https://pypi.nvidia.com \
    "cudf-cu12>=25.04" "cuml-cu12>=25.04" \
    "dask-cuda>=25.04"