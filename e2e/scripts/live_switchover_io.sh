#!/bin/sh
set -eu

DATA_DIR="${DATA_DIR:-/data/switchover_io}"
DATA_FILE="${DATA_FILE:-${DATA_DIR}/data.bin}"
MANIFEST="${MANIFEST:-/tmp/switchover_manifest}"
STOP_FILE="${STOP_FILE:-/tmp/switchover_stop}"
CHUNK_FILE="${CHUNK_FILE:-/tmp/switchover_chunk}"
DONE_FILE="${DONE_FILE:-/tmp/switchover_writer_done}"
ERROR_FILE="${ERROR_FILE:-/tmp/switchover_writer_error}"
PID_FILE="${PID_FILE:-/tmp/switchover_io.pid}"
LOG_FILE="${LOG_FILE:-/tmp/switchover_io.log}"
CHUNK_SIZE="${CHUNK_SIZE:-65536}"

writer() {
  rm -rf "${DATA_DIR}"
  mkdir -p "${DATA_DIR}"
  rm -f "${MANIFEST}" "${STOP_FILE}" "${CHUNK_FILE}" "${DONE_FILE}" "${ERROR_FILE}"
  : > "${DATA_FILE}"
  : > "${MANIFEST}"

  i=0
  while [ ! -f "${STOP_FILE}" ]; do
    if ! dd if=/dev/urandom of="${CHUNK_FILE}" bs="${CHUNK_SIZE}" count=1 status=none; then
      echo "dd failed at ${i}" > "${ERROR_FILE}"
      exit 1
    fi

    sum="$(sha256sum "${CHUNK_FILE}" | awk '{print $1}')"
    if ! dd if="${CHUNK_FILE}" of="${DATA_FILE}" bs="${CHUNK_SIZE}" count=1 seek="${i}" conv=notrunc,fsync status=none; then
      echo "sync write failed at ${i}" > "${ERROR_FILE}"
      exit 1
    fi

    echo "${i} ${sum}" >> "${MANIFEST}"
    i=$((i + 1))
    sleep 0.2
  done

  echo "${i}" > "${DONE_FILE}"
  sync
  echo "STOPPED chunks=${i}"
}

start() {
  (sh "$0" writer > "${LOG_FILE}" 2>&1 & echo $! > "${PID_FILE}")
  cat "${PID_FILE}"
}

count() {
  test ! -f "${ERROR_FILE}"
  kill -0 "$(cat "${PID_FILE}")"
  wc -l < "${MANIFEST}"
}

stop() {
  touch "${STOP_FILE}"
  for _ in $(seq 1 30); do
    test -f "${DONE_FILE}" && break
    sleep 1
  done
  echo "done=$(cat "${DONE_FILE}" 2>/dev/null || echo missing)"
  test ! -f "${ERROR_FILE}"
  tail -n 5 "${LOG_FILE}" 2>/dev/null || true
  wc -l "${MANIFEST}"
  wc -c "${DATA_FILE}"
}

stop_if_running() {
  touch "${STOP_FILE}"
  kill "$(cat "${PID_FILE}" 2>/dev/null)" 2>/dev/null || true
}

verify() {
  idx=0
  bad=0
  while read -r i expected; do
    got="$(dd if="${DATA_FILE}" bs="${CHUNK_SIZE}" count=1 skip="${i}" 2>/dev/null | sha256sum | awk '{print $1}')"
    if [ "${got}" != "${expected}" ]; then
      echo "MISMATCH chunk=${i} expected=${expected} got=${got}"
      bad=1
      break
    fi
    idx=$((idx + 1))
  done < "${MANIFEST}"

  if [ "${bad}" -ne 0 ]; then
    exit 1
  fi

  size="$(wc -c < "${DATA_FILE}")"
  expected_size=$((idx * CHUNK_SIZE))
  if [ "${size}" -ne "${expected_size}" ]; then
    echo "SIZE_MISMATCH size=${size} expected=${expected_size}"
    exit 1
  fi

  echo "CHECKSUM_OK chunks=${idx} size=${size} sha256=$(sha256sum "${DATA_FILE}" | awk '{print $1}')"
}

case "${1:-}" in
  writer) writer ;;
  start) start ;;
  count) count ;;
  stop) stop ;;
  stop-if-running) stop_if_running ;;
  verify) verify ;;
  *)
    echo "Usage: $0 {start|count|stop|stop-if-running|verify}" >&2
    exit 2
    ;;
esac
