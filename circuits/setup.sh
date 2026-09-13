#!/usr/bin/env bash

# Compile Qyvox's age circuit and perform a complete development Groth16 setup.
# Every command is non-interactive and fails closed. The random contributions
# come from OpenSSL and are never written to disk.
set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${SCRIPT_DIR}/build"
FRONTEND_ASSET_DIR="${REPOSITORY_DIR}/frontend/public/zk"
BACKEND_ASSET_DIR="${REPOSITORY_DIR}/backend/zk"
SNARKJS_BIN="${SCRIPT_DIR}/node_modules/.bin/snarkjs"

command -v circom >/dev/null 2>&1 || {
  echo "Circom 2.x is required but was not found on PATH." >&2
  exit 1
}
command -v openssl >/dev/null 2>&1 || {
  echo "OpenSSL is required to generate ceremony entropy." >&2
  exit 1
}
[[ -x "${SNARKJS_BIN}" ]] || {
  echo "Run 'npm ci' in ${SCRIPT_DIR} before this script." >&2
  exit 1
}

mkdir -p "${BUILD_DIR}" "${FRONTEND_ASSET_DIR}" "${BACKEND_ASSET_DIR}"

# Phase 0: compile to R1CS and WebAssembly witness generator.
circom "${SCRIPT_DIR}/age_check.circom" \
  --r1cs \
  --wasm \
  --sym \
  --output "${BUILD_DIR}" \
  -l "${SCRIPT_DIR}/node_modules"

"${SNARKJS_BIN}" r1cs info "${BUILD_DIR}/age_check.r1cs"

# Phase 1: create a bn128 Powers of Tau transcript sized for this circuit and
# add fresh local entropy. Power 12 supports up to 2^12 constraints.
"${SNARKJS_BIN}" powersoftau new \
  bn128 12 \
  "${BUILD_DIR}/pot12_0000.ptau" \
  --verbose

"${SNARKJS_BIN}" powersoftau contribute \
  "${BUILD_DIR}/pot12_0000.ptau" \
  "${BUILD_DIR}/pot12_0001.ptau" \
  --name="Qyvox development phase-1 contribution" \
  --entropy="$(openssl rand -hex 64)" \
  --verbose

"${SNARKJS_BIN}" powersoftau prepare phase2 \
  "${BUILD_DIR}/pot12_0001.ptau" \
  "${BUILD_DIR}/pot12_final.ptau" \
  --verbose

# Phase 2: specialize the ceremony to age_check.r1cs and contribute fresh
# circuit-specific entropy before exporting the verification key.
"${SNARKJS_BIN}" groth16 setup \
  "${BUILD_DIR}/age_check.r1cs" \
  "${BUILD_DIR}/pot12_final.ptau" \
  "${BUILD_DIR}/age_check_0000.zkey"

"${SNARKJS_BIN}" zkey contribute \
  "${BUILD_DIR}/age_check_0000.zkey" \
  "${BUILD_DIR}/age_check_final.zkey" \
  --name="Qyvox development circuit contribution" \
  --entropy="$(openssl rand -hex 64)" \
  --verbose

"${SNARKJS_BIN}" zkey verify \
  "${BUILD_DIR}/age_check.r1cs" \
  "${BUILD_DIR}/pot12_final.ptau" \
  "${BUILD_DIR}/age_check_final.zkey"

"${SNARKJS_BIN}" zkey export verificationkey \
  "${BUILD_DIR}/age_check_final.zkey" \
  "${BUILD_DIR}/verification_key.json"

# Publish exactly the artifacts consumed at runtime.
cp "${BUILD_DIR}/age_check_js/age_check.wasm" \
  "${FRONTEND_ASSET_DIR}/age_check.wasm"
cp "${BUILD_DIR}/age_check_final.zkey" \
  "${FRONTEND_ASSET_DIR}/age_check_final.zkey"
cp "${BUILD_DIR}/verification_key.json" \
  "${BACKEND_ASSET_DIR}/verification_key.json"
chmod 0644 \
  "${FRONTEND_ASSET_DIR}/age_check.wasm" \
  "${FRONTEND_ASSET_DIR}/age_check_final.zkey" \
  "${BACKEND_ASSET_DIR}/verification_key.json"

echo "Qyvox circuit artifacts generated successfully."
